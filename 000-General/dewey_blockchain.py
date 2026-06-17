#!/usr/bin/env python3
"""
Dewey Blockchain Logger — Immutable Real-Time Audit Trail
=========================================================
Every file event (create, modify, delete, sync, access) is a block.
Blocks chain together via SHA256 hashes — tamper-evident, append-only.

Block structure:
  {
    "index": N,
    "timestamp": "ISO8601",
    "action": "CREATE|MODIFY|DELETE|SYNC|ACCESS|APPROVE|GENESIS",
    "file": "relative/path",
    "file_hash": "sha256 of file content (null for DELETE/SYNC)",
    "section": "000-General",
    "dewey_class": "000",
    "trigger": "manual|sync|pipeline|cron",
    "previous_hash": "sha256 of previous block",
    "hash": "sha256 of this block's content"
  }

Usage:
  python3 dewey_blockchain.py log <action> <file> [--trigger manual]
  python3 dewey_blockchain.py verify          — validate entire chain
  python3 dewey_blockchain.py status          — chain stats
  python3 dewey_blockchain.py tail [N]        — last N blocks
  python3 dewey_blockchain.py search <query>  — search blocks
"""

import json, os, sys, hashlib
from datetime import datetime, timezone

BRAIN = "/home/allenai/blacktech_brain"
CHAIN_FILE = f"{BRAIN}/000-General/dewey_blockchain.json"

# ── Block hashing ────────────────────────────────────────────────────
def block_hash(block):
    """SHA256 of block's core fields (excluding the hash itself)."""
    payload = {
        "index": block["index"],
        "timestamp": block["timestamp"],
        "action": block["action"],
        "file": block["file"],
        "file_hash": block.get("file_hash", ""),
        "section": block.get("section", ""),
        "dewey_class": block.get("dewey_class", ""),
        "trigger": block.get("trigger", "manual"),
        "previous_hash": block["previous_hash"],
    }
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode()).hexdigest()

# ── Chain operations ──────────────────────────────────────────────────
def load_chain():
    """Load the blockchain from disk."""
    if not os.path.exists(CHAIN_FILE):
        return []
    with open(CHAIN_FILE) as f:
        return json.load(f)

def save_chain(chain):
    """Save the blockchain to disk."""
    os.makedirs(os.path.dirname(CHAIN_FILE), exist_ok=True)
    with open(CHAIN_FILE, "w") as f:
        json.dump(chain, f, indent=2)

def genesis_block():
    """Create the first block — the origin of the chain."""
    return {
        "index": 0,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": "GENESIS",
        "file": "dewey_blockchain.json",
        "file_hash": None,
        "section": "000-General",
        "dewey_class": "000",
        "trigger": "genesis",
        "previous_hash": "0" * 64,
        "hash": None,  # computed below
    }

def add_block(action, file_path, trigger="manual", file_hash_val=None):
    """Append a new block to the chain."""
    chain = load_chain()
    
    if not chain:
        # Initialize with genesis
        if action == "GENESIS":
            # Direct genesis — use the provided file as the origin
            rel = os.path.relpath(file_path, BRAIN) if file_path.startswith(BRAIN) else file_path
            section_dir = rel.split("/")[0] if "/" in rel else "000-General"
            dewey_num = section_dir.split("-")[0] if "-" in section_dir else "000"
            gen = {
                "index": 0,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "action": "GENESIS",
                "file": rel,
                "file_hash": file_hash_val,
                "section": section_dir,
                "dewey_class": dewey_num,
                "trigger": trigger,
                "previous_hash": "0" * 64,
                "hash": None,
            }
            gen["hash"] = block_hash(gen)
            chain = [gen]
            save_chain(chain)
            return gen
        else:
            # Auto-genesis + requested block
            gen = genesis_block()
            gen["hash"] = block_hash(gen)
            chain = [gen]
    
    prev = chain[-1]
    
    # Determine section and dewey class
    rel = os.path.relpath(file_path, BRAIN) if file_path.startswith(BRAIN) else file_path
    section_dir = rel.split("/")[0] if "/" in rel else "000-General"
    dewey_num = section_dir.split("-")[0] if "-" in section_dir else "000"
    
    # Compute file hash if not provided
    if file_hash_val is None and action not in ("DELETE", "SYNC", "GENESIS"):
        if os.path.exists(file_path):
            h = hashlib.sha256()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    h.update(chunk)
            file_hash_val = h.hexdigest()
    
    block = {
        "index": prev["index"] + 1,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "file": rel,
        "file_hash": file_hash_val,
        "section": section_dir,
        "dewey_class": dewey_num,
        "trigger": trigger,
        "previous_hash": prev["hash"],
        "hash": None,
    }
    block["hash"] = block_hash(block)
    
    chain.append(block)
    save_chain(chain)
    return block

def verify_chain():
    """Validate the entire chain — returns (valid, issues)."""
    chain = load_chain()
    if not chain:
        return False, ["Empty chain — no genesis block"]
    
    issues = []
    
    # Check genesis
    if chain[0]["action"] != "GENESIS":
        issues.append("Block 0 is not GENESIS")
    if chain[0]["previous_hash"] != "0" * 64:
        issues.append("Genesis previous_hash is not 64 zeros")
    
    for i in range(1, len(chain)):
        curr = chain[i]
        prev = chain[i - 1]
        
        # Index continuity
        if curr["index"] != prev["index"] + 1:
            issues.append(f"Block {curr['index']}: index gap (prev was {prev['index']})")
        
        # Previous hash match
        if curr["previous_hash"] != prev["hash"]:
            issues.append(f"Block {curr['index']}: previous_hash mismatch")
        
        # Self-hash integrity
        computed = block_hash(curr)
        if curr["hash"] != computed:
            issues.append(f"Block {curr['index']}: hash mismatch (stored={curr['hash'][:16]}..., computed={computed[:16]}...)")
    
    return len(issues) == 0, issues

def chain_status():
    """Return chain statistics."""
    chain = load_chain()
    if not chain:
        return {"blocks": 0, "genesis": False, "last_block": None, "actions": {}}
    
    actions = {}
    for b in chain:
        a = b["action"]
        actions[a] = actions.get(a, 0) + 1
    
    return {
        "blocks": len(chain),
        "genesis": chain[0]["action"] == "GENESIS",
        "first_block": chain[0]["timestamp"],
        "last_block": chain[-1]["timestamp"],
        "last_hash": chain[-1]["hash"][:16],
        "actions": actions,
        "sections": len(set(b.get("section", "") for b in chain)),
    }

def tail_blocks(n=10):
    """Return the last N blocks."""
    chain = load_chain()
    return chain[-n:] if chain else []

def search_blocks(query):
    """Search blocks by file path, action, or section."""
    chain = load_chain()
    q = query.lower()
    results = []
    for b in chain:
        if (q in b["file"].lower() or 
            q in b["action"].lower() or 
            q in b.get("section", "").lower() or
            q in b.get("trigger", "").lower()):
            results.append(b)
    return results

# ── CLI ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: dewey_blockchain.py <command> [args...]")
        print("  log <action> <file> [--trigger <name>]")
        print("  verify")
        print("  status")
        print("  tail [N]")
        print("  search <query>")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "log":
        if len(sys.argv) < 4:
            print("Usage: dewey_blockchain.py log <action> <file> [--trigger <name>]")
            sys.exit(1)
        action = sys.argv[2]
        file_path = sys.argv[3]
        trigger = "manual"
        if "--trigger" in sys.argv:
            idx = sys.argv.index("--trigger")
            trigger = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else "manual"
        
        block = add_block(action, file_path, trigger)
        print(json.dumps(block, indent=2))
    
    elif cmd == "verify":
        valid, issues = verify_chain()
        if valid:
            print("✅ Chain valid — all blocks intact")
        else:
            print(f"🔴 Chain INVALID — {len(issues)} issues:")
            for issue in issues:
                print(f"  • {issue}")
    
    elif cmd == "status":
        stats = chain_status()
        print(json.dumps(stats, indent=2))
    
    elif cmd == "tail":
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        blocks = tail_blocks(n)
        for b in blocks:
            print(f"[{b['index']}] {b['timestamp'][:19]} {b['action']:8} {b['file']}")
    
    elif cmd == "search":
        if len(sys.argv) < 3:
            print("Usage: dewey_blockchain.py search <query>")
            sys.exit(1)
        results = search_blocks(sys.argv[2])
        print(f"{len(results)} matches:")
        for b in results:
            print(f"  [{b['index']}] {b['action']} {b['file']} — {b['timestamp'][:19]}")
    
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
