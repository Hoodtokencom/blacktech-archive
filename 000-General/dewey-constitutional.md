# Dewey Constitutional — The 3-Body System

**Ratified:** June 17, 2026  
**Jurisdiction:** Blacktech Solutions Corp — All Digital Knowledge Assets  
**Amendments:** Via blockchain-logged CREATE/MODIFY on this document only

---

## Preamble

We, the knowledge systems of Blacktech Solutions Corp, establish this Constitutional to govern the creation, storage, synchronization, access, and preservation of all digital knowledge assets. The Dewey Decimal Library is the brain; the three storage mirrors are the body; the blockchain is the immutable memory. Together they form a single living organism for organizational intelligence.

---

## Article I — The Three Mirrors

### Section 1.01 — BRAIN (Google Drive Storefront)

**Role:** Public catalog. Index. Cover art.  
**Location:** Google Drive → `Dewey Brain/` root folder  
**Contains:** 13 Dewey section subfolders with metadata, README files, and catalog entries. File *titles and descriptions only* — not the actual content.  
**Access:** Open to authorized viewers. Anyone can browse the catalog.  
**Function:** The storefront window. You can see what exists, but you cannot touch the merchandise.

> *The Brain knows what is in the library. It does not hold the books.*

### Section 1.02 — BODY (Internal Drive Vault)

**Role:** The actual files. The real content. The working copies.  
**Location:** `/home/allenai/blacktech_brain/` on the Raspberry Pi  
**Contains:** All 27+ real files across 13 Dewey sections. This is where work happens — files are created, edited, and deleted here first.  
**Access:** Key-locked. Requires passcode authentication via the Security Guard (port 8096).  
**Function:** The vault. The engine room. The place where information moves.

> *The Body holds the books. You need a key to enter.*

### Section 1.03 — ARCHIVE (GitHub Repository)

**Role:** Complete mirror. Clutter staging. Historical record.  
**Location:** `Hoodtokencom/blacktech-archive` on GitHub  
**Contains:** Full copy of every file that has ever existed in the Body. Files marked for deletion go here first for review before permanent removal.  
**Access:** Public repository. Visible to all.  
**Function:** The recycling center. Nothing is ever truly deleted — it goes to Archive for review. Files can be restored or permanently removed after review.

> *The Archive remembers everything. Even the things we chose to forget.*

---

## Article II — The Sync Pipeline (Message Bus)

### Section 2.01 — dewey_sync.py

The sync pipeline (`dewey_sync.py`) is the central nervous system connecting all three mirrors. It runs on-demand or via cron schedule.

**Rules of synchronization:**

1. **Body is the source of truth.** All changes originate in the Body (Internal Drive). Brain and Archive are mirrors — they reflect, they do not originate.
2. **SHA256 change detection.** Before any sync operation, the pipeline hashes every file. Only changed files are pushed. No redundant transfers.
3. **Three-way mirror on every sync:**
   - Body → Brain (Google Drive upload via rclone)
   - Body → Archive (GitHub push via git)
   - Every sync event → Blockchain (immutable log)
4. **Direction is one-way.** Brain and Archive never push back to Body. The Body is sovereign.
5. **Sync is additive, not destructive.** Files deleted from Body are moved to Archive's `_trash/` directory — never deleted from Archive. Brain reflects current state only.

### Section 2.02 — Sync Triggers

The pipeline fires on:
- Manual invocation: `python3 dewey_sync.py`
- Cron schedule: nightly at 2:00 AM CT
- Post-major-change: after any batch of 3+ file operations

---

## Article III — The Blockchain Audit Trail

### Section 3.01 — Immutable Ledger

Every action on the knowledge base is logged to the Dewey Blockchain (`dewey_blockchain.json`, port 8104).

**Logged actions:**
- `CREATE` — new file added to Body
- `MODIFY` — existing file changed in Body
- `DELETE` — file removed from Body (moved to Archive trash)
- `SYNC` — sync pipeline executed
- `ACCESS` — key-approved access to vault files
- `RESTORE` — file restored from Archive to Body
- `APPROVE` — contract/workflow approval step (draft → review → approved → signed)

**Block structure:**
```
{
  index: N,
  timestamp: ISO-8601,
  action: CREATE|MODIFY|DELETE|SYNC|ACCESS|RESTORE,
  file: "/path/relative/to/blacktech_brain",
  file_hash: SHA256 or null,
  section: "Dewey class (e.g. 650)",
  dewey_class: "000-999",
  trigger: "manual|hermes-agent|cron|sync-pipeline",
  previous_hash: SHA256 of block N-1,
  hash: SHA256 of this block
}
```

### Section 3.02 — Chain Integrity

- Genesis block (index 0) is seeded with a known hash.
- Every block links to its predecessor via `previous_hash`.
- `verify()` walks the entire chain and confirms every link.
- A broken chain = system compromise. Triggers immediate audit.

---

## Article IV — Access Control (The Key System)

### Section 4.01 — Four Access Tiers

| Tier | Name | Access | Mechanism |
|------|------|--------|-----------|
| 1 | **Public** | Browse Brain catalog (Google Drive) | Shared link |
| 2 | **Key** | View Body files (read-only) | Passcode via Security Guard |
| 3 | **Approval** | Edit Body files (read-write) | Derrell-authorized passcode |
| 4 | **Vault** | Access encrypted passcodes | Fernet key + master password |

### Section 4.02 — Security Guard (Port 8096)

The Security Guard (`dewey_pipeline.py`, port 8096) is the gatekeeper. All access to Tier 2 and above flows through it.

**Functions:**
- Validate passcodes against the encrypted vault (`657-Accounting`)
- Grant/deny access to Body files
- Log all access attempts to Blockchain
- Serve the Dewey Dashboard (combined with Guard UI)

### Section 4.03 — The Key Flow

```
User requests file → Brain shows catalog entry
  ↓
User requests access → Security Guard (port 8096)
  ↓
Passcode validated → Fernet decrypt against vault
  ↓
Access granted → Body file unlocked
  ↓
Access logged → Blockchain (ACCESS block)
```

> *The Brain shows you the cover. The Guard gives you the key. The Body hands you the book. The Blockchain remembers you read it.*

---

## Article V — File Lifecycle

### Section 5.01 — Birth (CREATE)

1. File is created in Body (`/home/allenai/blacktech_brain/XXX-Section/filename.ext`)
2. Blockchain logs `CREATE` block
3. On next sync: uploaded to Brain (Google Drive) + pushed to Archive (GitHub)

### Section 5.02 — Life (MODIFY)

1. File is edited in Body
2. Blockchain logs `MODIFY` block with new SHA256 hash
3. On next sync: updated in Brain + Archive

### Section 5.03 — Death (DELETE)

1. File is moved from Body to Archive `_trash/` directory
2. Blockchain logs `DELETE` block
3. File remains in Archive for review (30-day minimum)
4. After review: either `RESTORE` back to Body, or permanent removal from Archive only (never from Blockchain log)

> *Nothing is ever truly deleted. The Blockchain remembers forever.*

---

## Article VI — Dewey Decimal Classification

### Section 6.01 — The 13 Sections

All files MUST be placed in one of the 13 Dewey sections:

| Class | Section | Domain |
|-------|---------|--------|
| 000 | General | Index, README, Constitution, passcode vault |
| 100 | Philosophy & Psychology | Mission, values, principles |
| 200 | Religion | Faith-based docs, church relations |
| 300 | Social Sciences | Community, SSBN, team structure |
| 400 | Language | Style guide, terminology, shorthand |
| 500 | Science & Math | Electrical theory, calculations, schematics |
| 600 | Technology | HostGator, Pi infrastructure, servers |
| 620 | Engineering & Construction | Engineering specs, NEC code |
| 650 | Management & Business | SOPs, contracts, HR, legal |
| 657 | Accounting & Finance | Passcodes, QBO, payroll, invoices |
| 690 | Building & Construction | Estimates, permits, materials |
| 700 | Arts & Design | Brand assets, logos, templates |
| 800 | Literature | Proposals, newsletters, scripts |
| 900 | History & Geography | Timeline, milestones, locations |
| 910 | Travel & Locations | Job sites, zip code maps |
| 920 | Biography & People | Contacts, subcontractors, vendors |
| 930 | Archaeology & History | Old project archives, lessons learned |
| 999 | Decisions & Logs | Decision log, change history |

### Section 6.02 — Naming Convention

- Lowercase with hyphens: `energy-advisor-sop.md`
- No spaces, no underscores in filenames
- PDF + HTML pairs share the same base name: `dewey-blockchain-schematic.html` / `.pdf`

---

## Article VII — Governance

### Section 7.01 — Sovereignty

The Body (Internal Drive) is sovereign. Brain and Archive are mirrors. No external system may modify the Body without passing through the Security Guard.

### Section 7.02 — Amendments

This Constitutional may be amended by:
1. `MODIFY` to this file (`000-General/dewey-constitutional.md`)
2. Blockchain-logged with amendment description
3. Sync to Brain + Archive within 24 hours

### Section 7.03 — Interpretation

Derrell A. Black is the final authority on all matters of interpretation. The systems serve the mission; the mission does not serve the systems.

---

## Article VIII — Emergency Provisions

### Section 8.01 — Body Failure

If the Internal Drive fails:
1. Restore Body from Archive (GitHub has full mirror)
2. Re-sync Brain from restored Body
3. Blockchain remains intact (separate storage)

### Section 8.02 — Brain Failure

If Google Drive is unavailable:
1. Body continues as normal (sovereign)
2. Archive continues as normal (independent)
3. Sync queues until Brain is restored

### Section 8.03 — Archive Failure

If GitHub is unavailable:
1. Body continues as normal
2. Brain continues as normal
3. Sync queues until Archive is restored

> *No single mirror failure can stop the system. The Body is sovereign; the mirrors are redundant.*

---

## Article IX — Contract Approval Workflow

### Section 9.01 — The Four Immutable Stages

Every construction contract moves through four blockchain-logged stages. No stage may be skipped. No approval may be forged. The chain remembers every step.

| Stage | Icon | Meaning | Who |
|-------|------|---------|-----|
| 1. **DRAFT** | 📝 | Contract created, not yet reviewed | System / Estimator |
| 2. **REVIEW** | 🔍 | Under review by Derrell or designated reviewer | Derrell Black |
| 3. **APPROVED** | ✅ | Approved, ready for client signature | Derrell Black |
| 4. **SIGNED** | ✍️ | Signed by all parties, contract active | Client + Derrell |

### Section 9.02 — The Approval Pipeline

The pipeline (`contract_approval.py`) enforces the workflow:

```
Contract created (DRAFT)
  ↓
Blockchain: APPROVE block logged
  ↓
Review (REVIEW) — Derrell examines
  ↓
Blockchain: APPROVE block logged
  ↓
Approved (APPROVED) — ready for signature
  ↓
Blockchain: APPROVE block logged
  ↓
Signed (SIGNED) — all parties sign
  ↓
Blockchain: APPROVE block logged
  ↓
🏁 Complete — immutable audit trail
```

### Section 9.03 — Blockchain Integration

- Every stage transition is logged as an `APPROVE` block on the Dewey Blockchain
- Each block records: who approved, when, file hash (tamper-proof), and optional notes
- The full approval history is stored in `690-Building_Construction/contracts.json`
- SHA256 hashes at each stage prove the file hasn't changed between approvals

### Section 9.04 — Rules

1. **Sequential only.** draft → review → approved → signed. No skipping.
2. **Immutable history.** Once a stage is logged, it cannot be removed or altered.
3. **File integrity.** SHA256 hash is recomputed at each stage transition. Any file change between stages is detectable.
4. **Human authority.** Only Derrell (or explicitly delegated reviewer) may advance past REVIEW.
5. **Blockchain witness.** Every approval is an APPROVE block. The chain is the ultimate witness.

### Section 9.05 — Commands

```bash
# Start a new contract
python3 contract_approval.py init BSC-C-2026-001 /path/to/contract.pdf

# Advance through stages
python3 contract_approval.py advance BSC-C-2026-001 review --by "Derrell Black" --note "Checked scope"
python3 contract_approval.py advance BSC-C-2026-001 approved --by "Derrell Black"
python3 contract_approval.py advance BSC-C-2026-001 signed --by "Derrell Black" --note "Client signed 6/17/26"

# View full history
python3 contract_approval.py status BSC-C-2026-001

# List all contracts
python3 contract_approval.py list
```

> *A contract without blockchain approval is a handshake without witnesses. The chain remembers who said yes, and when.*

---

## Signatures

**Ratified by:** Derrell A. Black, Blacktech Solutions Corp  
**Witnessed by:** Dewey Blockchain — Genesis Block #0  
**Filed under:** `000-General/dewey-constitutional.md`  
**Effective:** June 17, 2026 — In Perpetuity

---

*This Constitutional governs all digital knowledge assets of Blacktech Solutions Corp. It is the instruction set for the 3-Body System. It lives in 000-General — the brain of the brain.*
# Code Department active — Wed Jun 17 08:44:15 AM CDT 2026
