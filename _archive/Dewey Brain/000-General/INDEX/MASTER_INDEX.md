# Blacktech Solutions Corp — Master File System Index
**Last Updated:** 06/02/2026

---

## 📁 DRIVE STRUCTURE

```
Blacktech_Drive/
├── 00-INDEX/           ← This file — master map of everything
├── 1-Admin/            ← Business admin, jobs, invoices, contracts
│   ├── Jobs/           ← One folder per customer/job
│   │   ├── Phil_Powell/         ← Eco School (Invoice #1360)
│   │   ├── 6647_S_Saint_Lawrence_Ave/
│   │   ├── 7414_S_Drexel/
│   │   ├── 7919_S_Dorchester/
│   │   └── London_Town_Home/
│   ├── Invoices/
│   │   ├── 2026/        ← All QBO invoice PDFs by year
│   │   ├── Templates/   ← HTML/MD invoice templates
│   │   └── Email_Raw/   ← Raw email attachments from robot
│   ├── Contracts/
│   ├── Warranties/
│   ├── Permits_Licenses/
│   ├── Insurance/
│   └── Leads/           ← Email robot raw lead files
│
├── 2-Projects/          ← Active job site folders
│   ├── Active/
│   │   ├── Euclid/
│   │   ├── Ford_Heights_Fire_Station/
│   │   ├── South_Holland/
│   │   └── Village_Hall/
│   ├── Archived/
│   ├── Bids_Proposals/
│   └── Estimates/
│
├── 3-Accounting/        ← Taxes, payroll, QBO reports
│   ├── Tax_Documents/
│   ├── Payroll/
│   ├── Expense_Receipts/
│   └── QuickBooks_Reports/
│
├── 4-Vendor_Materials/  ← Supplier quotes, material lists
├── 5-Marketing/         ← Flyers, social media, Think Energy
│   ├── Flyers_Branding/
│   ├── Think_Energy_Calculator/
│   ├── Social_Media/
│   ├── QR_Codes/
│   └── Lead_Intake/
│
├── 6-Operations/        ← SOPs, equipment, schedules
├── 7-Personal_The_Vault/← Crypto wallets, personal docs
└── 8-Misc/              ← Drop zone for unsorted files
```

---

## 🗂️ ACTIVE JOBS (as of 06/02/2026)

| Job # | Customer | Address | Status | Invoice | Amount |
|-------|----------|---------|--------|---------|--------|
| 1360 | Phil Powell / Veteran Prestige | Eco School | 🟡 Invoiced | #1360 | $10,033.62 |
| 6647 | Charles Ockerlund | 6647 S Saint Lawrence | ✅ Invoiced | #1357 | $2,817.89 |
| 7414 | Malissa Mitchell | 7414 S Drexel | 🟡 Invoiced | — | $10,900.00 |
| 7919 | Rose Williams | 7919 S Dorchester | 🟡 Invoiced | — | $10,900.00 |
| LONDON | London Town Home | Chicago, IL 60619 | 🟡 Invoiced | #1348 | $221,456.80 |

---

## 📋 CRM / LEADS

| Name | Phone | Email | Status |
|------|-------|-------|--------|
| Phil Powell | (312) 801-0549 | Pvbuilders2@aol.com | Active Client |
| Maria Montgomery | 708-829-2280 | mariawalton74@yahoo.com | Think Energy Lead |

**Lead files:** `/home/allenai/.hermes/profiles/derrell-black/leads/`

---

## 🖥️ PI SYSTEM (money.blacktechsolutionscorp.com:8091)

| File | Location |
|------|----------|
| Money/Budget Dashboard | `/home/allenai/money_budget.html` |
| Jobs data | `/home/allenai/data/jobs.json` |
| Invoices data | `/home/allenai/data/invoices.json` |
| Invoice #1360 HTML | `/home/allenai/Invoice_1360_Phil_Powell_Eco_School.html` |
| Invoice #1360 PDF | `/home/allenai/Invoice_1360_Phil_Powell_Eco_School.pdf` |
| Command Center | `/home/allenai/index.html` |
