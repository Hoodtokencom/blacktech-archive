# Blacktech Brain — Dewey Decimal Library

A knowledge base organized like a library catalog.

## Catalog

| Section | Class | Contents |
|---------|-------|----------|
| `000-General` | Generalities | Index, README, lookup tools, passcode vault script |
| `100-Philosophy_Psychology` | Philosophy | Mission, values, principles |
| `200-Religion` | Religion | Faith-based trust docs, church relations |
| `300-Social_Sciences` | Social sciences | Community, SSBN, team structure |
| `400-Language` | Language | Style guide, terminology, shorthand |
| `500-Science_Math` | Science | Electrical theory, calculations, LCP rates |
| `600-Technology` | Technology | HostGator email, Pi infrastructure, servers |
| `620-Engineering_Construction` | Civil/mechanical eng | Engineering specs, NEC code notes |
| `650-Management_Business` | Management | SOPs, contracts, HR, legal |
| `657-Accounting_Finance` | Accounting | Passcodes, QBO, payroll, invoices, budgets |
| `690-Building_Construction` | Construction | Electrical estimates, permits, materials |
| `700-Arts_Design` | Arts | Brand assets, logos, colors, templates |
| `800-Literature` | Literature | Proposals, newsletters, scripts |
| `900-History_Geography` | History | Company timeline, milestones |
| `910-Travel_Locations` | Travel/geography | Job site locations, zip code maps |
| `920-Biography_People` | Biography | Contacts, subcontractors, vendor notes |
| `930-Archaeology_History` | Archaeology | Old project archives, lessons learned |
| `999-Decisions_Logs` | Local history | Decision log, change history |

## Rules

- Every document gets a Dewey-style path: `650-Management_Business/email-sop.md`
- Keep filenames descriptive and lowercase with hyphens.
- Passcodes encrypted via `000-General/passcode_vault.py`.
- Sync to Google Drive nightly via `drive_sync.py`.
