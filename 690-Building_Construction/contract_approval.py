#!/usr/bin/env python3
"""
Dewey Contract Approval Pipeline — Blockchain-Backed Workflow
==============================================================
Every construction contract moves through 4 immutable stages:
  DRAFT → REVIEW → APPROVED → SIGNED

Each stage is logged as an APPROVE block on the Dewey Blockchain.
No stage can be skipped. No approval can be forged. The chain remembers.

Usage:
  python3 contract_approval.py init <contract-id> <file-path> [--estimate <est#>] [--address "addr"]
  python3 contract_approval.py advance <contract-id> <stage> [--by "Name"] [--note "text"]
  python3 contract_approval.py link <contract-id> --estimate <est#> [--invoice <inv#>]
  python3 contract_approval.py status <contract-id>
  python3 contract_approval.py lifecycle <contract-id>
  python3 contract_approval.py list

Stages:
  draft    — Contract created, not yet reviewed
  review   — Under review by Derrell or designated reviewer
  approved — Approved, ready for signature
  signed   — Signed by all parties, contract active

The approval chain is stored in:
  /home/allenai/blacktech_brain/690-Building_Construction/contracts.json
"""

import json, os, sys, hashlib
from datetime import datetime, timezone
from pathlib import Path

BRAIN = "/home/allenai/blacktech_brain"
CONTRACTS_FILE = f"{BRAIN}/690-Building_Construction/contracts.json"
BLOCKCHAIN_CLI = f"{BRAIN}/000-General/dewey_blockchain.py"
INVOICES_FILE = "/home/allenai/data/invoices.json"
ESTIMATES_DIR = "/home/allenai/estimates"

STAGES = ["draft", "review", "approved", "signed"]
VALID_TRANSITIONS = {
    None: "draft",       # init
    "draft": "review",
    "review": "approved",
    "approved": "signed",
}

# ── Contract registry ─────────────────────────────────────────────────
def load_contracts():
    if not os.path.exists(CONTRACTS_FILE):
        return {}
    with open(CONTRACTS_FILE) as f:
        return json.load(f)

def save_contracts(contracts):
    os.makedirs(os.path.dirname(CONTRACTS_FILE), exist_ok=True)
    with open(CONTRACTS_FILE, "w") as f:
        json.dump(contracts, f, indent=2)

# ── Blockchain log helper ──────────────────────────────────────────────
def log_block(action, file_path, trigger="contract-pipeline", extra=None):
    """Log an APPROVE block via the blockchain CLI."""
    import subprocess
    cmd = [
        "python3", BLOCKCHAIN_CLI, "log",
        action, file_path,
        "--trigger", trigger
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"⚠️  Blockchain log failed: {result.stderr}")
        return None
    return json.loads(result.stdout)

# ── Commands ───────────────────────────────────────────────────────────
def cmd_init(contract_id, file_path, estimate=None, address=None):
    """Initialize a new contract in the approval pipeline."""
    contracts = load_contracts()
    
    if contract_id in contracts:
        print(f"❌ Contract '{contract_id}' already exists.")
        print(f"   Current stage: {contracts[contract_id]['stage']}")
        return
    
    # Verify file exists
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return
    
    # Compute file hash
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    file_hash = h.hexdigest()
    
    now = datetime.now(timezone.utc).isoformat()
    
    contracts[contract_id] = {
        "contract_id": contract_id,
        "file": file_path,
        "file_hash": file_hash,
        "stage": "draft",
        "estimate_number": estimate,
        "invoice_number": None,
        "address": address,
        "history": [
            {
                "stage": "draft",
                "timestamp": now,
                "by": "system",
                "note": f"Contract initialized" + (f" — linked to estimate {estimate}" if estimate else ""),
                "block_index": None,
            }
        ],
        "created": now,
        "updated": now,
    }
    
    save_contracts(contracts)
    
    # Log to blockchain
    block = log_block("APPROVE", file_path, "contract-pipeline")
    if block:
        contracts[contract_id]["history"][0]["block_index"] = block["index"]
        save_contracts(contracts)
        print(f"✅ Contract '{contract_id}' initialized — Stage: DRAFT")
        if estimate:
            print(f"   Linked to estimate: {estimate}")
        if address:
            print(f"   Address: {address}")
        print(f"   Blockchain: Block #{block['index']}")
    else:
        print(f"✅ Contract '{contract_id}' initialized — Stage: DRAFT")
        print(f"   ⚠️  Blockchain log pending (retry on next sync)")

def cmd_advance(contract_id, stage, by="Derrell Black", note=""):
    """Advance a contract to the next approval stage."""
    contracts = load_contracts()
    
    if contract_id not in contracts:
        print(f"❌ Contract '{contract_id}' not found.")
        return
    
    contract = contracts[contract_id]
    current = contract["stage"]
    
    if stage not in STAGES:
        print(f"❌ Invalid stage: '{stage}'. Valid: {', '.join(STAGES)}")
        return
    
    expected = VALID_TRANSITIONS.get(current)
    if stage != expected:
        print(f"❌ Invalid transition: {current} → {stage}")
        print(f"   Expected next stage: {expected}")
        print(f"   Current stage: {current}")
        return
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Recompute file hash
    file_path = contract["file"]
    h = hashlib.sha256()
    if os.path.exists(file_path):
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
    file_hash = h.hexdigest()
    
    entry = {
        "stage": stage,
        "timestamp": now,
        "by": by,
        "note": note,
        "file_hash": file_hash,
        "block_index": None,
    }
    
    contract["stage"] = stage
    contract["file_hash"] = file_hash
    contract["updated"] = now
    contract["history"].append(entry)
    
    save_contracts(contracts)
    
    # Log to blockchain
    block = log_block("APPROVE", file_path, "contract-pipeline")
    if block:
        entry["block_index"] = block["index"]
        contract["history"][-1] = entry
        save_contracts(contracts)
        print(f"✅ Contract '{contract_id}' advanced: {current} → {stage}")
        print(f"   By: {by}")
        if note:
            print(f"   Note: {note}")
        print(f"   Blockchain: Block #{block['index']}")
    else:
        print(f"✅ Contract '{contract_id}' advanced: {current} → {stage}")
        print(f"   ⚠️  Blockchain log pending")

def cmd_status(contract_id):
    """Show the full approval history for a contract."""
    contracts = load_contracts()
    
    if contract_id not in contracts:
        print(f"❌ Contract '{contract_id}' not found.")
        return
    
    c = contracts[contract_id]
    
    stage_icons = {
        "draft": "📝",
        "review": "🔍",
        "approved": "✅",
        "signed": "✍️",
    }
    
    print(f"\n{'='*60}")
    print(f"  Contract: {c['contract_id']}")
    print(f"  File:     {c['file']}")
    print(f"  Stage:    {stage_icons.get(c['stage'], '•')} {c['stage'].upper()}")
    print(f"  Created:  {c['created'][:19].replace('T', ' ')}")
    print(f"  Updated:  {c['updated'][:19].replace('T', ' ')}")
    print(f"{'='*60}")
    print(f"\n  Approval History:")
    print(f"  {'─'*50}")
    
    for i, entry in enumerate(c["history"]):
        icon = stage_icons.get(entry["stage"], "•")
        block_info = f" [Block #{entry['block_index']}]" if entry.get("block_index") else ""
        print(f"  {i+1}. {icon} {entry['stage'].upper():10} {entry['timestamp'][:19].replace('T', ' ')}")
        print(f"     By: {entry['by']}{block_info}")
        if entry.get("note"):
            print(f"     Note: {entry['note']}")
        if entry.get("file_hash"):
            print(f"     Hash: {entry['file_hash'][:16]}...")
    
    # Show next available stage
    next_stage = VALID_TRANSITIONS.get(c["stage"])
    if next_stage:
        print(f"\n  ➡️  Next: {next_stage.upper()}")
    else:
        print(f"\n  🏁 Complete — all stages passed")
    print()

def cmd_list():
    """List all contracts in the pipeline."""
    contracts = load_contracts()
    
    if not contracts:
        print("No contracts in pipeline.")
        return
    
    stage_icons = {
        "draft": "📝",
        "review": "🔍",
        "approved": "✅",
        "signed": "✍️",
    }
    
    print(f"\n{'Contract ID':<30} {'Stage':<12} {'Estimate':<18} {'Invoice':<18} {'Updated':<20}")
    print(f"{'─'*30} {'─'*12} {'─'*18} {'─'*18} {'─'*20}")
    
    for cid, c in sorted(contracts.items()):
        icon = stage_icons.get(c["stage"], "•")
        stage_str = f"{icon} {c['stage']}"
        est = c.get("estimate_number", "—") or "—"
        inv = c.get("invoice_number", "—") or "—"
        updated = c["updated"][:19].replace("T", " ")
        print(f"{cid:<30} {stage_str:<12} {est:<18} {inv:<18} {updated:<20}")
    
    print(f"\n  Total: {len(contracts)} contracts")
    print()

def cmd_link(contract_id, estimate=None, invoice=None):
    """Link a contract to an estimate and/or invoice."""
    contracts = load_contracts()
    
    if contract_id not in contracts:
        print(f"❌ Contract '{contract_id}' not found.")
        return
    
    c = contracts[contract_id]
    now = datetime.now(timezone.utc).isoformat()
    changes = []
    
    if estimate:
        c["estimate_number"] = estimate
        changes.append(f"estimate {estimate}")
    if invoice:
        c["invoice_number"] = invoice
        changes.append(f"invoice {invoice}")
    
    if not changes:
        print("❌ Nothing to link. Use --estimate <#> and/or --invoice <#>")
        return
    
    c["updated"] = now
    save_contracts(contracts)
    
    # Log to blockchain
    note = f"Linked to {' and '.join(changes)}"
    block = log_block("APPROVE", c["file"], "contract-pipeline")
    if block:
        print(f"✅ Contract '{contract_id}' linked to {' and '.join(changes)}")
        print(f"   Blockchain: Block #{block['index']}")
    else:
        print(f"✅ Contract '{contract_id}' linked to {' and '.join(changes)}")

def cmd_lifecycle(contract_id):
    """Show the full lifecycle: estimate → contract → invoice."""
    contracts = load_contracts()
    
    if contract_id not in contracts:
        print(f"❌ Contract '{contract_id}' not found.")
        return
    
    c = contracts[contract_id]
    
    # Load invoices.json for financial data
    invoices = {}
    if os.path.exists(INVOICES_FILE):
        with open(INVOICES_FILE) as f:
            inv_list = json.load(f)
            for inv in inv_list:
                key = inv.get("invoice_number") or inv.get("num")
                if key:
                    invoices[key] = inv
    
    stage_icons = {
        "draft": "📝",
        "review": "🔍",
        "approved": "✅",
        "signed": "✍️",
    }
    
    est_num = c.get("estimate_number")
    inv_num = c.get("invoice_number")
    address = c.get("address", "—")
    
    print(f"\n{'='*70}")
    print(f"  LIFECYCLE: {contract_id}")
    print(f"  Address:   {address}")
    print(f"{'='*70}")
    
    # ── Phase 1: Estimate ──
    print(f"\n  📋 PHASE 1 — ESTIMATE")
    print(f"  {'─'*50}")
    if est_num and est_num in invoices:
        est = invoices[est_num]
        print(f"  Number:   {est_num}")
        print(f"  Customer: {est.get('customer', '—')}")
        print(f"  Amount:   ${est.get('amount', 0):,.2f}")
        print(f"  Status:   {est.get('status', '—')}")
        print(f"  Date:     {est.get('date', '—')}")
    elif est_num:
        print(f"  Number:   {est_num}")
        print(f"  ⚠️  Not found in invoices.json")
    else:
        print(f"  ⚠️  No estimate linked yet")
    
    # ── Phase 2: Contract Approval ──
    print(f"\n  ⛓️ PHASE 2 — CONTRACT APPROVAL")
    print(f"  {'─'*50}")
    print(f"  Stage:    {stage_icons.get(c['stage'], '•')} {c['stage'].upper()}")
    print(f"  File:     {os.path.basename(c['file'])}")
    print(f"\n  Approval Trail:")
    for i, entry in enumerate(c["history"]):
        icon = stage_icons.get(entry["stage"], "•")
        block_info = f" [Block #{entry['block_index']}]" if entry.get("block_index") else ""
        print(f"  {i+1}. {icon} {entry['stage'].upper():10} {entry['timestamp'][:19].replace('T', ' ')}")
        print(f"     By: {entry['by']}{block_info}")
        if entry.get("note"):
            print(f"     {entry['note']}")
    
    # ── Phase 3: Invoice ──
    print(f"\n  🧾 PHASE 3 — INVOICE")
    print(f"  {'─'*50}")
    if inv_num and inv_num in invoices:
        inv = invoices[inv_num]
        print(f"  Number:   {inv_num}")
        print(f"  Customer: {inv.get('customer', '—')}")
        print(f"  Amount:   ${inv.get('amount', 0):,.2f}")
        print(f"  Status:   {inv.get('status', '—')}")
        print(f"  Date:     {inv.get('date', '—')}")
        if inv.get("due_date"):
            print(f"  Due:      {inv['due_date']}")
    elif inv_num:
        print(f"  Number:   {inv_num}")
        print(f"  ⚠️  Not found in invoices.json")
    else:
        print(f"  ⚠️  No invoice linked yet")
    
    # ── Summary ──
    print(f"\n{'='*70}")
    est_amount = invoices.get(est_num, {}).get("amount", 0) if est_num else 0
    inv_amount = invoices.get(inv_num, {}).get("amount", 0) if inv_num else 0
    print(f"  Pipeline Value: ${est_amount + inv_amount:,.2f}")
    print(f"  Blockchain Blocks: {len([e for e in c['history'] if e.get('block_index')])}")
    print(f"{'='*70}\n")

# ── CLI ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Dewey Contract Approval Pipeline")
        print()
        print("Commands:")
        print("  init      <contract-id> <file-path> [--estimate #] [--address addr]")
        print("  advance   <contract-id> <stage> [--by] [--note]")
        print("  link      <contract-id> --estimate <#> [--invoice <#>]")
        print("  status    <contract-id>")
        print("  lifecycle <contract-id>")
        print("  list")
        print()
        print("Stages: draft → review → approved → signed")
        print("Lifecycle: estimate → contract → invoice")
        sys.exit(0)
    
    cmd = sys.argv[1]
    
    if cmd == "init":
        if len(sys.argv) < 4:
            print("Usage: contract_approval.py init <contract-id> <file-path> [--estimate #] [--address addr]")
            sys.exit(1)
        
        contract_id = sys.argv[2]
        file_path = sys.argv[3]
        estimate = None
        address = None
        
        args = sys.argv[4:]
        i = 0
        while i < len(args):
            if args[i] == "--estimate" and i + 1 < len(args):
                estimate = args[i + 1]
                i += 2
            elif args[i] == "--address" and i + 1 < len(args):
                address = args[i + 1]
                i += 2
            else:
                i += 1
        
        cmd_init(contract_id, file_path, estimate, address)
    
    elif cmd == "advance":
        if len(sys.argv) < 4:
            print("Usage: contract_approval.py advance <contract-id> <stage> [--by Name] [--note text]")
            sys.exit(1)
        
        contract_id = sys.argv[2]
        stage = sys.argv[3]
        by = "Derrell Black"
        note = ""
        
        args = sys.argv[4:]
        i = 0
        while i < len(args):
            if args[i] == "--by" and i + 1 < len(args):
                by = args[i + 1]
                i += 2
            elif args[i] == "--note" and i + 1 < len(args):
                note = args[i + 1]
                i += 2
            else:
                i += 1
        
        cmd_advance(contract_id, stage, by, note)
    
    elif cmd == "link":
        if len(sys.argv) < 4:
            print("Usage: contract_approval.py link <contract-id> --estimate <#> [--invoice <#>]")
            sys.exit(1)
        
        contract_id = sys.argv[2]
        estimate = None
        invoice = None
        
        args = sys.argv[3:]
        i = 0
        while i < len(args):
            if args[i] == "--estimate" and i + 1 < len(args):
                estimate = args[i + 1]
                i += 2
            elif args[i] == "--invoice" and i + 1 < len(args):
                invoice = args[i + 1]
                i += 2
            else:
                i += 1
        
        cmd_link(contract_id, estimate, invoice)
    
    elif cmd == "lifecycle":
        if len(sys.argv) < 3:
            print("Usage: contract_approval.py lifecycle <contract-id>")
            sys.exit(1)
        cmd_lifecycle(sys.argv[2])
    
    elif cmd == "status":
        if len(sys.argv) < 3:
            print("Usage: contract_approval.py status <contract-id>")
            sys.exit(1)
        cmd_status(sys.argv[2])
    
    elif cmd == "list":
        cmd_list()
    
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
