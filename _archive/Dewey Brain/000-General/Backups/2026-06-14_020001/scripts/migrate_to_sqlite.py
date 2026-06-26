#!/usr/bin/env python3
"""
JSON to SQLite Migration for Blacktech Solutions
Migrates all .json data files to a single SQLite database.
CRASH-PROOF: SQLite is atomic — power loss mid-write won't corrupt data.
"""

import os
import json
import sqlite3
from datetime import datetime

# ── CONFIG ─────────────────────────────────────────
DATA_DIR = "/home/allenai/data"
DB_PATH = os.path.join(DATA_DIR, "blacktech.db")

# ── SCHEMA ───────────────────────────────────────
SCHEMA = """
-- Jobs / Budget table
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    customer TEXT,
    scope TEXT,
    address TEXT,
    phone TEXT,
    amount REAL,
    status TEXT,
    notes TEXT,
    submitted_by TEXT,
    date_added TEXT,
    source TEXT
);

-- CRM Contacts
CREATE TABLE IF NOT EXISTS contacts (
    id TEXT PRIMARY KEY,
    name TEXT,
    company TEXT,
    phone TEXT,
    email TEXT,
    address TEXT,
    status TEXT,
    source TEXT,
    notes TEXT,
    created TEXT,
    last_contact TEXT
);

-- Invoices
CREATE TABLE IF NOT EXISTS invoices (
    num TEXT PRIMARY KEY,
    customer TEXT,
    address TEXT,
    job TEXT,
    date TEXT,
    due TEXT,
    status TEXT,
    notes TEXT,
    html_file TEXT,
    total REAL
);

-- Invoice line items
CREATE TABLE IF NOT EXISTS invoice_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_num TEXT,
    description TEXT,
    qty REAL,
    rate REAL,
    FOREIGN KEY (invoice_num) REFERENCES invoices(num)
);

-- Kanban cards
CREATE TABLE IF NOT EXISTS kanban (
    id TEXT PRIMARY KEY,
    title TEXT,
    status TEXT,
    column_name TEXT,
    created TEXT,
    updated TEXT
);

-- Vendors
CREATE TABLE IF NOT EXISTS vendors (
    id TEXT PRIMARY KEY,
    name TEXT,
    service TEXT,
    phone TEXT,
    email TEXT,
    address TEXT,
    status TEXT
);

-- BFN shared data
CREATE TABLE IF NOT EXISTS bfn_shared (
    id TEXT PRIMARY KEY,
    key TEXT,
    value TEXT,
    updated TEXT
);

-- Generic settings / config
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated TEXT
);

-- BFN nested JSON data (stored as JSON blobs for flexibility)
CREATE TABLE IF NOT EXISTS bfn_data (
    key TEXT PRIMARY KEY,
    json_blob TEXT,
    updated TEXT
);
"""

# ── MIGRATIONS ─────────────────────────────────────
MIGRATIONS = {
    "budget.json": {
        "table": "jobs",
        "map": {
            "id": "id",
            "customer": "customer",
            "scope": "scope",
            "address": "address",
            "phone": "phone",
            "amount": "amount",
            "status": "status",
            "notes": "notes",
            "submitted_by": "submitted_by",
            "date_added": "date_added",
            "source": "source"
        }
    },
    "crm_contacts.json": {
        "table": "contacts",
        "map": {
            "id": "id",
            "name": "name",
            "company": "company",
            "phone": "phone",
            "email": "email",
            "address": "address",
            "status": "status",
            "source": "source",
            "notes": "notes",
            "created": "created",
            "lastContact": "last_contact"
        }
    },
    "invoices.json": {
        "table": "invoices",
        "special": "invoices",  # has nested line items
        "map": {
            "num": "num",
            "customer": "customer",
            "address": "address",
            "job": "job",
            "date": "date",
            "due": "due",
            "status": "status",
            "notes": "notes",
            "htmlFile": "html_file"
        }
    },
    "kanban_cards.json": {
        "table": "kanban",
        "map": {
            "id": "id",
            "title": "title",
            "status": "status",
            "column": "column_name",
            "created": "created",
            "updated": "updated"
        }
    },
    "vendors.json": {
        "table": "vendors",
        "map": {
            "id": "id",
            "name": "name",
            "service": "service",
            "phone": "phone",
            "email": "email",
            "address": "address",
            "status": "status"
        }
    },
    "bfn_shared.json": {
        "table": "bfn_data",
        "special": "nested_json",  # nested dict with arrays
        "map": {}
    }
}

# ── HELPERS ────────────────────────────────────────
def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] 🗄️  {msg}")

def migrate_file(cursor, filename, config):
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        log(f"Skip (not found): {filename}")
        return 0

    with open(path, 'r') as f:
        data = json.load(f)

    # Special handling for nested JSON blobs (dicts, not lists)
    if config.get("special") == "nested_json" and isinstance(data, dict):
        for key, value in data.items():
            cursor.execute(
                "INSERT OR REPLACE INTO bfn_data (key, json_blob, updated) VALUES (?, ?, ?)",
                (key, json.dumps(value), datetime.now().isoformat())
            )
        log(f"Migrated nested JSON: {filename} → bfn_data ({len(data)} keys)")
        return len(data)

    if not isinstance(data, list):
        log(f"Skip (not a list): {filename}")
        return 0

    table = config["table"]
    field_map = config["map"]
    count = 0

    for item in data:
        if not isinstance(item, dict):
            continue

        # Build insert
        cols = []
        vals = []
        for json_key, db_col in field_map.items():
            cols.append(db_col)
            vals.append(item.get(json_key, None))

        # Special handling for invoices with line items
        if config.get("special") == "invoices":
            lines = item.get("lines", [])
            total = sum(line.get("qty", 0) * line.get("rate", 0) for line in lines)
            cols.append("total")
            vals.append(total)

        placeholders = ",".join(["?"] * len(cols))
        sql = f"INSERT OR REPLACE INTO {table} ({','.join(cols)}) VALUES ({placeholders})"
        cursor.execute(sql, vals)

        # Insert line items for invoices
        if config.get("special") == "invoices":
            for line in lines:
                cursor.execute(
                    "INSERT INTO invoice_lines (invoice_num, description, qty, rate) VALUES (?, ?, ?, ?)",
                    (item.get("num"), line.get("desc"), line.get("qty", 0), line.get("rate", 0))
                )

        count += 1

    log(f"Migrated {count} records: {filename} → {table}")
    return count

# ── MAIN ───────────────────────────────────────────
def main():
    log("═══ JSON → SQLite Migration Started ═══")
    log(f"Database: {DB_PATH}")

    # Connect (creates file if not exists)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Create schema
    cursor.executescript(SCHEMA)
    log("Schema created/verified")

    # Migrate each file
    total = 0
    for filename, config in MIGRATIONS.items():
        total += migrate_file(cursor, filename, config)

    conn.commit()
    conn.close()

    # Show stats
    log("═══ Migration Complete ═══")
    log(f"Total records migrated: {total}")

    # Verify by connecting and counting
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    for table in ["jobs", "contacts", "invoices", "kanban", "vendors", "bfn_shared"]:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        log(f"  {table}: {count} rows")
    conn.close()

    log(f"Database size: {os.path.getsize(DB_PATH):,} bytes")
    log("Done.")

if __name__ == "__main__":
    main()
