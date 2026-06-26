#!/usr/bin/env python3
"""
Blacktech Solutions Corp — Phase 1
Build unified blacktech_core.db + migrate all existing data
Run once: python3 /home/allenai/scripts/build_core_db.py
"""

import sqlite3, json, os, uuid, datetime

CORE_DB   = "/home/allenai/data/blacktech_core.db"
OLD_DB    = "/home/allenai/data/blacktech.db"
DATA_DIR  = "/home/allenai/data"

def uid(prefix):
    return f"{prefix}-{uuid.uuid4().hex[:8].upper()}"

def now():
    return datetime.datetime.now().isoformat(timespec='seconds')

# ── 1. CREATE SCHEMA ──────────────────────────────────────────────
def create_schema(conn):
    conn.executescript("""
    PRAGMA journal_mode=WAL;
    PRAGMA foreign_keys=ON;

    -- CONTACTS (customers, leads, vendors, employees)
    CREATE TABLE IF NOT EXISTS contacts (
        id          TEXT PRIMARY KEY,
        name        TEXT NOT NULL,
        company     TEXT,
        phone       TEXT,
        email       TEXT,
        address     TEXT,
        city        TEXT,
        state       TEXT DEFAULT 'IL',
        zip         TEXT,
        type        TEXT DEFAULT 'lead',
        source      TEXT,
        status      TEXT DEFAULT 'new',
        notes       TEXT,
        created_at  TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at  TEXT DEFAULT CURRENT_TIMESTAMP
    );

    -- JOBS / PROJECTS
    CREATE TABLE IF NOT EXISTS jobs (
        id           TEXT PRIMARY KEY,
        contact_id   TEXT REFERENCES contacts(id),
        title        TEXT,
        scope        TEXT,
        address      TEXT,
        city         TEXT,
        state        TEXT DEFAULT 'IL',
        zip          TEXT,
        type         TEXT DEFAULT 'electrical',
        status       TEXT DEFAULT 'lead',
        source       TEXT,
        submitted_by TEXT,
        amount       REAL DEFAULT 0,
        start_date   TEXT,
        end_date     TEXT,
        notes        TEXT,
        created_at   TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at   TEXT DEFAULT CURRENT_TIMESTAMP
    );

    -- ESTIMATES
    CREATE TABLE IF NOT EXISTS estimates (
        id           TEXT PRIMARY KEY,
        job_id       TEXT REFERENCES jobs(id),
        contact_id   TEXT REFERENCES contacts(id),
        title        TEXT,
        status       TEXT DEFAULT 'draft',
        subtotal     REAL DEFAULT 0,
        tax          REAL DEFAULT 0,
        total        REAL DEFAULT 0,
        valid_until  TEXT,
        notes        TEXT,
        created_at   TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS estimate_lines (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        estimate_id  TEXT REFERENCES estimates(id),
        description  TEXT,
        qty          REAL DEFAULT 1,
        rate         REAL DEFAULT 0,
        amount       REAL DEFAULT 0,
        category     TEXT
    );

    -- INVOICES
    CREATE TABLE IF NOT EXISTS invoices (
        id             TEXT PRIMARY KEY,
        job_id         TEXT REFERENCES jobs(id),
        contact_id     TEXT REFERENCES contacts(id),
        estimate_id    TEXT REFERENCES estimates(id),
        invoice_number TEXT UNIQUE,
        status         TEXT DEFAULT 'draft',
        issue_date     TEXT,
        due_date       TEXT,
        subtotal       REAL DEFAULT 0,
        tax            REAL DEFAULT 0,
        total          REAL DEFAULT 0,
        amount_paid    REAL DEFAULT 0,
        notes          TEXT,
        html_file      TEXT,
        created_at     TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at     TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS invoice_lines (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_id  TEXT REFERENCES invoices(id),
        description TEXT,
        qty         REAL DEFAULT 1,
        rate        REAL DEFAULT 0,
        amount      REAL DEFAULT 0,
        category    TEXT
    );

    -- PAYMENTS  ← NEW — did not exist before
    CREATE TABLE IF NOT EXISTS payments (
        id           TEXT PRIMARY KEY,
        invoice_id   TEXT REFERENCES invoices(id),
        job_id       TEXT REFERENCES jobs(id),
        contact_id   TEXT REFERENCES contacts(id),
        amount       REAL NOT NULL,
        method       TEXT,
        reference    TEXT,
        payment_date TEXT,
        notes        TEXT,
        created_at   TEXT DEFAULT CURRENT_TIMESTAMP
    );

    -- JOB COSTS
    CREATE TABLE IF NOT EXISTS job_costs (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id      TEXT REFERENCES jobs(id),
        category    TEXT,
        description TEXT,
        amount      REAL DEFAULT 0,
        vendor      TEXT,
        receipt     TEXT,
        cost_date   TEXT,
        created_at  TEXT DEFAULT CURRENT_TIMESTAMP
    );

    -- EMPLOYEES
    CREATE TABLE IF NOT EXISTS employees (
        id            TEXT PRIMARY KEY,
        name          TEXT NOT NULL,
        role          TEXT,
        type          TEXT DEFAULT 'W2',
        pay_type      TEXT DEFAULT 'hourly',
        rate          REAL DEFAULT 0,
        overtime_rate REAL DEFAULT 0,
        status        TEXT DEFAULT 'active',
        email         TEXT,
        phone         TEXT,
        start_date    TEXT
    );

    -- TIMESHEETS
    CREATE TABLE IF NOT EXISTS timesheets (
        id             TEXT PRIMARY KEY,
        employee_id    TEXT REFERENCES employees(id),
        job_id         TEXT REFERENCES jobs(id),
        week_start     TEXT,
        hours          REAL DEFAULT 0,
        ot_hours       REAL DEFAULT 0,
        reg_pay        REAL DEFAULT 0,
        ot_pay         REAL DEFAULT 0,
        bonus          REAL DEFAULT 0,
        total          REAL DEFAULT 0,
        status         TEXT DEFAULT 'pending',
        paid_date      TEXT,
        payment_method TEXT,
        notes          TEXT,
        created_at     TEXT DEFAULT CURRENT_TIMESTAMP
    );

    -- PAYROLL RUNS
    CREATE TABLE IF NOT EXISTS payroll_runs (
        id             TEXT PRIMARY KEY,
        week_start     TEXT,
        run_date       TEXT,
        total          REAL DEFAULT 0,
        employee_count INTEGER DEFAULT 0,
        status         TEXT DEFAULT 'draft',
        method         TEXT,
        notes          TEXT,
        created_at     TEXT DEFAULT CURRENT_TIMESTAMP
    );

    -- EXPENSES (business + tax)
    CREATE TABLE IF NOT EXISTS expenses (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id       TEXT REFERENCES jobs(id),
        category     TEXT,
        description  TEXT,
        amount       REAL,
        vendor       TEXT,
        receipt      TEXT,
        expense_date TEXT,
        deductible   INTEGER DEFAULT 1,
        created_at   TEXT DEFAULT CURRENT_TIMESTAMP
    );

    -- TAX PAYMENTS
    CREATE TABLE IF NOT EXISTS tax_payments (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        quarter      TEXT,
        year         INTEGER DEFAULT 2025,
        amount_paid  REAL,
        paid_date    TEXT,
        confirmation TEXT,
        notes        TEXT,
        created_at   TEXT DEFAULT CURRENT_TIMESTAMP
    );

    -- VENDORS / MATERIAL CATALOG
    CREATE TABLE IF NOT EXISTS vendors (
        id           TEXT PRIMARY KEY,
        name         TEXT,
        company      TEXT,
        part_number  TEXT,
        category     TEXT,
        unit         TEXT,
        cost         REAL DEFAULT 0,
        price        REAL DEFAULT 0,
        markup       REAL DEFAULT 0,
        vendor_src   TEXT,
        notes        TEXT
    );

    -- COMED LEADS (extends jobs)
    CREATE TABLE IF NOT EXISTS comed_leads (
        id           TEXT PRIMARY KEY,
        contact_id   TEXT REFERENCES contacts(id),
        job_id       TEXT REFERENCES jobs(id),
        services     TEXT,
        status       TEXT DEFAULT 'new',
        photos_dir   TEXT,
        closeout     TEXT,
        created_at   TEXT DEFAULT CURRENT_TIMESTAMP
    );

    -- KANBAN
    CREATE TABLE IF NOT EXISTS kanban_cards (
        id         TEXT PRIMARY KEY,
        job_id     TEXT REFERENCES jobs(id),
        contact_id TEXT REFERENCES contacts(id),
        title      TEXT,
        notes      TEXT,
        status     TEXT DEFAULT 'backlog',
        tag        TEXT,
        color      TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    -- PIPELINE RESULTS (AI)
    CREATE TABLE IF NOT EXISTS pipeline_results (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        task_id      TEXT,
        task_type    TEXT,
        priority     TEXT,
        input_data   TEXT,
        final_output TEXT,
        total_cost   REAL DEFAULT 0,
        status       TEXT,
        created_at   TEXT DEFAULT CURRENT_TIMESTAMP
    );

    -- SETTINGS
    CREATE TABLE IF NOT EXISTS settings (
        key        TEXT PRIMARY KEY,
        value      TEXT,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    -- AUDIT LOG (every state change recorded)
    CREATE TABLE IF NOT EXISTS audit_log (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        entity     TEXT,
        entity_id  TEXT,
        action     TEXT,
        old_value  TEXT,
        new_value  TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """)
    conn.commit()
    print("✅ Schema created")

# ── 2. MIGRATE DATA ───────────────────────────────────────────────
def migrate_jobs(conn):
    path = os.path.join(DATA_DIR, "jobs.json")
    if not os.path.exists(path):
        print("⚠️  jobs.json not found, skipping")
        return 0
    with open(path) as f:
        data = json.load(f)
    jobs = data if isinstance(data, list) else data.get("jobs", [])
    count = 0
    for j in jobs:
        jid = j.get("id") or uid("BSC-JOB")
        if not jid.startswith("BSC-"):
            jid = f"BSC-JOB-{jid}"
        # Upsert contact first
        cid = uid("BSC-CUST")
        conn.execute("""INSERT OR IGNORE INTO contacts
            (id,name,phone,email,address,city,type,source,status,notes,created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (cid, j.get("customer","Unknown"), j.get("phone",""),
             j.get("email",""), j.get("address",""), j.get("city","Chicago"),
             "customer", j.get("source","import"), "active", "", now()))
        conn.execute("""INSERT OR IGNORE INTO jobs
            (id,contact_id,title,scope,address,city,type,status,source,
             submitted_by,amount,notes,created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (jid, cid,
             j.get("customer","") + " — " + j.get("scope","")[:40],
             j.get("scope",""), j.get("address",""),
             j.get("city","Chicago"), "electrical",
             j.get("status","lead"), j.get("source","import"),
             j.get("submitted_by",""), j.get("amount",0),
             j.get("notes",""), j.get("date_added", now())))
        count += 1
    conn.commit()
    print(f"✅ Migrated {count} jobs")
    return count

def migrate_invoices(conn):
    path = os.path.join(DATA_DIR, "invoices.json")
    if not os.path.exists(path):
        print("⚠️  invoices.json not found, skipping")
        return 0
    with open(path) as f:
        data = json.load(f)
    invoices = data if isinstance(data, list) else data.get("invoices", [])
    count = 0
    for inv in invoices:
        iid = uid("BSC-INV")
        cid = uid("BSC-CUST")
        conn.execute("""INSERT OR IGNORE INTO contacts
            (id,name,address,type,source,status,created_at)
            VALUES (?,?,?,?,?,?,?)""",
            (cid, inv.get("customer","Unknown"),
             inv.get("address",""), "customer", "invoice-import", "active", now()))
        total = sum(
            float(l.get("qty",1)) * float(l.get("rate",0))
            for l in inv.get("lines", [])
        ) or float(inv.get("total", 0))
        status = inv.get("status","sent")
        amount_paid = total if status == "paid" else 0.0
        conn.execute("""INSERT OR IGNORE INTO invoices
            (id,contact_id,invoice_number,status,issue_date,due_date,
             total,amount_paid,notes,html_file,created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (iid, cid, str(inv.get("num","")), status,
             inv.get("date",""), inv.get("due",""),
             total, amount_paid,
             inv.get("notes",""), inv.get("htmlFile",""), now()))
        for line in inv.get("lines", []):
            amt = float(line.get("qty",1)) * float(line.get("rate",0))
            conn.execute("""INSERT INTO invoice_lines
                (invoice_id,description,qty,rate,amount)
                VALUES (?,?,?,?,?)""",
                (iid, line.get("desc",""), float(line.get("qty",1)),
                 float(line.get("rate",0)), amt))
        count += 1
    conn.commit()
    print(f"✅ Migrated {count} invoices")
    return count

def migrate_contacts(conn):
    path = os.path.join(DATA_DIR, "crm_contacts.json")
    if not os.path.exists(path):
        print("⚠️  crm_contacts.json not found, skipping")
        return 0
    with open(path) as f:
        data = json.load(f)
    contacts = data if isinstance(data, list) else data.get("contacts", [])
    count = 0
    for c in contacts:
        cid = uid("BSC-CUST")
        conn.execute("""INSERT OR IGNORE INTO contacts
            (id,name,company,phone,email,address,type,source,status,notes,created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (cid, c.get("name",""), c.get("company",""),
             c.get("phone",""), c.get("email",""), c.get("address",""),
             c.get("type","lead"), c.get("source","crm"),
             c.get("status","new"), c.get("notes",""),
             c.get("created", now())))
        count += 1
    conn.commit()
    print(f"✅ Migrated {count} CRM contacts")
    return count

def migrate_comed_leads(conn):
    path = os.path.join(DATA_DIR, "comed_leads.json")
    if not os.path.exists(path):
        print("⚠️  comed_leads.json not found, skipping")
        return 0
    with open(path) as f:
        data = json.load(f)
    leads = data if isinstance(data, list) else data.get("leads", [])
    count = 0
    for l in leads:
        cid = uid("BSC-CUST")
        jid = uid("BSC-JOB")
        lid = uid("BSC-COMED")
        conn.execute("""INSERT OR IGNORE INTO contacts
            (id,name,phone,email,address,city,type,source,status,created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (cid, l.get("name",""), l.get("phone",""),
             l.get("email",""), l.get("address",""),
             l.get("city","Chicago"), "customer",
             "comed", l.get("status","new"), l.get("created", now())))
        conn.execute("""INSERT OR IGNORE INTO jobs
            (id,contact_id,title,address,city,type,status,source,created_at)
            VALUES (?,?,?,?,?,?,?,?,?)""",
            (jid, cid,
             f"ComEd EESP — {l.get('name','')}",
             l.get("address",""), l.get("city","Chicago"),
             "comed", l.get("status","lead"), "comed", l.get("created", now())))
        conn.execute("""INSERT OR IGNORE INTO comed_leads
            (id,contact_id,job_id,services,status,created_at)
            VALUES (?,?,?,?,?,?)""",
            (lid, cid, jid,
             json.dumps(l.get("services",[])),
             l.get("status","new"), l.get("created", now())))
        count += 1
    conn.commit()
    print(f"✅ Migrated {count} ComEd leads → contacts + jobs + comed_leads")
    return count

def migrate_employees(conn):
    path = os.path.join(DATA_DIR, "payroll.json")
    if not os.path.exists(path):
        print("⚠️  payroll.json not found, skipping")
        return 0
    with open(path) as f:
        data = json.load(f)
    emps = data.get("employees", [])
    sheets = data.get("timesheets", [])
    runs = data.get("payment_runs", [])
    ec = tc = rc = 0
    for e in emps:
        eid = e.get("id") or uid("BSC-EMP")
        conn.execute("""INSERT OR IGNORE INTO employees
            (id,name,role,type,pay_type,rate,overtime_rate,status,email,phone)
            VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (eid, e.get("name",""), e.get("role",""),
             e.get("type","W2"), e.get("payType","hourly"),
             float(e.get("rate",0)), float(e.get("overtimeRate",0)),
             e.get("status","active"), e.get("email",""), e.get("phone","")))
        ec += 1
    conn.executescript("PRAGMA foreign_keys=OFF;")
    for s in sheets:
        conn.execute("""INSERT OR IGNORE INTO timesheets
            (id,employee_id,week_start,hours,ot_hours,reg_pay,ot_pay,
             bonus,total,status,paid_date,payment_method,notes,created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (s.get("id", uid("BSC-TS")),
             s.get("employeeId",""), s.get("weekStart",""),
             float(s.get("hours",0)), float(s.get("otHours",0)),
             float(s.get("regPay",0)), float(s.get("otPay",0)),
             float(s.get("bonus",0)), float(s.get("total",0)),
             "paid" if s.get("paid") else "pending",
             s.get("paid_date",""), s.get("payment_method",""),
             s.get("notes",""), s.get("date", now())))
        tc += 1
    for r in runs:
        conn.execute("""INSERT OR IGNORE INTO payroll_runs
            (id,week_start,run_date,total,employee_count,status,method)
            VALUES (?,?,?,?,?,?,?)""",
            (r.get("id", uid("BSC-PR")),
             r.get("week",""), r.get("date",""),
             float(r.get("total",0)), int(r.get("employeeCount",0)),
             r.get("status","paid"), r.get("method","")))
        rc += 1
    conn.commit()
    print(f"✅ Migrated {ec} employees, {tc} timesheets, {rc} payroll runs")
    return ec

def migrate_job_costs(conn):
    path = os.path.join(DATA_DIR, "job_costs.json")
    if not os.path.exists(path):
        print("⚠️  job_costs.json not found, skipping")
        return 0
    with open(path) as f:
        data = json.load(f)
    costs = data if isinstance(data, list) else data.get("costs", [])
    count = 0
    for c in costs:
        for cat in ["material","labor","contractor","other"]:
            amt_key = f"{cat}_cost"
            amt = float(c.get(amt_key, 0))
            if amt > 0:
                conn.execute("""INSERT INTO job_costs
                    (category,description,amount,cost_date)
                    VALUES (?,?,?,?)""",
                    (cat, f"{cat.title()} cost for {c.get('job_id','')}",
                     amt, now()))
                count += 1
    conn.commit()
    print(f"✅ Migrated {count} job cost entries")
    return count

def migrate_vendors(conn):
    path = os.path.join(DATA_DIR, "vendors.json")
    if not os.path.exists(path):
        print("⚠️  vendors.json not found, skipping")
        return 0
    with open(path) as f:
        data = json.load(f)
    items = data if isinstance(data, list) else data.get("vendors", [])
    count = 0
    for v in items:
        vid = v.get("id") or uid("BSC-VND")
        conn.execute("""INSERT OR IGNORE INTO vendors
            (id,name,part_number,category,unit,cost,price,markup,vendor_src,notes)
            VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (vid, v.get("name",""), v.get("partNumber",""),
             v.get("category",""), v.get("unit",""),
             float(v.get("cost",0)), float(v.get("price",0)),
             float(v.get("markup",0)), v.get("vendor",""),
             v.get("notes","")))
        count += 1
    conn.commit()
    print(f"✅ Migrated {count} vendor/material items")
    return count

def migrate_tax(conn):
    import sqlite3 as sq
    path = os.path.join(DATA_DIR, "tax_tracker.db")
    if not os.path.exists(path):
        print("⚠️  tax_tracker.db not found, skipping")
        return 0
    old = sq.connect(path)
    # expenses
    ec = 0
    for row in old.execute("SELECT date,category,description,amount FROM expenses"):
        conn.execute("""INSERT INTO expenses
            (expense_date,category,description,amount,deductible)
            VALUES (?,?,?,?,1)""", row)
        ec += 1
    # tax payments
    tc = 0
    for row in old.execute("SELECT quarter,amount_paid,paid_date,confirmation,notes FROM quarterly_payments"):
        conn.execute("""INSERT INTO tax_payments
            (quarter,year,amount_paid,paid_date,confirmation,notes)
            VALUES (?,2025,?,?,?,?)""",
            (row[0], row[1], row[2], row[3], row[4]))
        tc += 1
    old.close()
    conn.commit()
    print(f"✅ Migrated {ec} expenses + {tc} tax payments from tax_tracker.db")
    return ec + tc

def migrate_pipeline(conn):
    import sqlite3 as sq
    path = os.path.join(DATA_DIR, "blacktech.db")
    if not os.path.exists(path):
        print("⚠️  blacktech.db not found, skipping")
        return 0
    old = sq.connect(path)
    count = 0
    try:
        for row in old.execute(
            "SELECT task_id,task_type,priority,input_data,final_output,total_cost,claude_status,created_at FROM pipeline_results ORDER BY id DESC LIMIT 200"
        ):
            conn.execute("""INSERT OR IGNORE INTO pipeline_results
                (task_id,task_type,priority,input_data,final_output,total_cost,status,created_at)
                VALUES (?,?,?,?,?,?,?,?)""", row)
            count += 1
    except Exception as e:
        print(f"  pipeline_results: {e}")
    old.close()
    conn.commit()
    print(f"✅ Migrated {count} pipeline results")
    return count

def migrate_kanban(conn):
    path = os.path.join(DATA_DIR, "kanban_cards.json")
    if not os.path.exists(path):
        print("⚠️  kanban_cards.json not found, skipping")
        return 0
    with open(path) as f:
        data = json.load(f)
    cards = data if isinstance(data, list) else data.get("cards", [])
    count = 0
    for c in cards:
        cid = c.get("id") or uid("BSC-KAN")
        conn.execute("""INSERT OR IGNORE INTO kanban_cards
            (id,title,notes,status,tag,color,created_at)
            VALUES (?,?,?,?,?,?,?)""",
            (cid, c.get("title",""), c.get("notes",""),
             c.get("column","backlog"), c.get("tag",""),
             c.get("color",""), c.get("created", now())))
        count += 1
    conn.commit()
    print(f"✅ Migrated {count} kanban cards")
    return count

def seed_settings(conn):
    settings = [
        ("company_name", "Blacktech Solutions Corp"),
        ("ein", "82-3394717"),
        ("owner", "Derrell A Black"),
        ("address", "10052 S Forest Ave, Chicago IL 60628"),
        ("phone", "(312) 965-2782"),
        ("email", "payroll@blacktechsolutionscorp.com"),
        ("tax_year", "2025"),
        ("tax_rate", "0.25"),
        ("db_version", "1.0"),
        ("created_at", now()),
    ]
    for k, v in settings:
        conn.execute("INSERT OR REPLACE INTO settings (key,value,updated_at) VALUES (?,?,?)",
                     (k, v, now()))
    conn.commit()
    print("✅ Settings seeded")

# ── 3. RUN REPORT ─────────────────────────────────────────────────
def print_report(conn):
    tables = ["contacts","jobs","invoices","invoice_lines","payments",
              "employees","timesheets","payroll_runs","expenses",
              "tax_payments","vendors","comed_leads","kanban_cards",
              "pipeline_results","audit_log"]
    print("\n" + "="*50)
    print("📊 BLACKTECH CORE DB — MIGRATION REPORT")
    print("="*50)
    total = 0
    for t in tables:
        try:
            n = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            total += n
            if n > 0:
                print(f"  {t:<25} {n:>5} rows")
        except:
            pass
    print(f"  {'TOTAL':<25} {total:>5} rows")
    print("="*50)

# ── MAIN ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("🏭 Blacktech Phase 1 — Building unified database...")
    print(f"   Target: {CORE_DB}\n")

    conn = sqlite3.connect(CORE_DB)

    create_schema(conn)
    migrate_contacts(conn)
    migrate_jobs(conn)
    migrate_invoices(conn)
    migrate_comed_leads(conn)
    migrate_employees(conn)
    migrate_job_costs(conn)
    migrate_vendors(conn)
    migrate_tax(conn)
    migrate_pipeline(conn)
    migrate_kanban(conn)
    seed_settings(conn)
    print_report(conn)

    conn.close()
    print(f"\n✅ DONE — {CORE_DB} is ready")
    print("   All original files untouched (safe rollback available)")
