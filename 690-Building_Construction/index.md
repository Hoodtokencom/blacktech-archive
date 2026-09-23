# Federal Contractors Directory — MEP NAICS

**Last Updated:** 2026-06-23  
**Source:** USASpending.gov API (open, no key required)  
**NAICS:** 238210 (Electrical), 238220 (Plumbing/HVAC), 238290 (Other Building Equipment)

## Stats
- **805 contractors** in `blacktech_core.db` (contacts table, source=USASpending.gov)
- **812 enrichment records** with UEI, DUNS, address, business types
- **33 IL contractors** (Siemens $64M, Richard Group $35M, O'Neill $26M lead)
- **350 MBE/DBE/8(a)** certified firms
- **Total federal spend:** ~$12.5B across all MEP awards

## Top 5 IL Contractors
1. Siemens Industry Inc — Buffalo Grove, IL — $64.5M
2. Richard Group LLC — Chicago, IL — $35.3M
3. O'Neill Contractors Inc — Chicago, IL — $26.6M (8(a))
4. Modesto Management LLC — Oak Park, IL — $20.8M (8(a), Black-owned)
5. Troop Contracting Inc — Willowbrook, IL — $17.4M

## Nearby Contractors
- **A Vet Communications, Inc.** — Midlothian, IL ($18K) — right in Blacktech's backyard (60419)

## Data Locations (Body tier)
- **Raw scrapes:** `4-Vendor_Materials/Federal_Contracts/SAM/raw_scrapes/usaspending_mep_all.json`
- **Deduped contractors:** `4-Vendor_Materials/Federal_Contracts/SAM/processed/mep_contractors_deduped.json`
- **UEI enrichment:** `4-Vendor_Materials/Federal_Contracts/SAM/enrichment/uei_enrichment_full.json`
- **DB:** `blacktech_core.db` contacts table (8 UEI columns added)

## Query Examples
```sql
-- All IL contractors
SELECT name, city, uei, total_transaction_amount FROM contacts WHERE state='IL' AND source='USASpending.gov' ORDER BY total_transaction_amount DESC;

-- MBE/8(a) firms
SELECT name, city, state, business_types FROM contacts WHERE (business_types LIKE '%minority_owned%' OR business_types LIKE '%8a_program%') AND source='USASpending.gov';

-- By city
SELECT name, uei, total_transaction_amount FROM contacts WHERE city='CHICAGO' AND source='USASpending.gov';
```
