# Blacktech Decentralization Migration Plan (Items 2-10)

**Goal:** Migrate centralized dependencies to decentralized alternatives
**Principle:** Non-destructive — run new system alongside old before cutting over

---

## Phase 2: Web Hosting (Cloudflare Tunnels → IPFS/Arweave)
**Current:** Cloudflared tunnels route subdomains to Pi services
**Target:** IPFS pinning + Arweave for permanent hosting
**Steps:**
1. Install IPFS node on Pi (`ipfs init`, configure repo)
2. Pin Academy + Command Center static assets to IPFS
3. Set up Arweave wallet, fund with AR tokens
4. Upload permanent content (estimates, invoices, certs) to Arweave
5. Use IPNS or ENS+IPFS for human-readable gateway
6. Keep Cloudflare as fallback during transition
**Cost:** IPFS free (self-hosted), Arweave ~$0.004/KB permanent storage
**Risk:** Slower load times, gateway reliability

## Phase 3: Email (HostGator → Self-Hosted Mailcow on Pi)
**Current:** mail.blacktechsolutionscorp.com via HostGator cPanel
**Target:** Mailcow dockerized on Pi (or secondary Pi)
**Steps:**
1. Install Docker + Mailcow on Pi
2. Configure DNS MX records (Cloudflare → direct A record)
3. Set up DKIM/SPF/DMARC for deliverability
4. Migrate existing emails via IMAP sync (imapsync)
5. Update himalaya config to point to local Mailcow
6. Test send/receive for 30 days alongside HostGator
7. Cut over MX records, decommission HostGator email
**Cost:** Free (self-hosted), domain renewal only
**Risk:** IP reputation — Pi IP may be blacklisted by Gmail/Outlook. Need rDNS + warmup.
**Pitfall:** Port 25 blocked by most ISPs — may need relay (Mailgun free tier)

## Phase 4: CRM/Database (SQLite → OrbitDB or Ceramic)
**Current:** SQLite files on Pi (blacktech_core.db, comed_leads.json)
**Target:** OrbitDB (P2P CRDT database on IPFS) or Ceramic Network
**Steps:**
1. Install OrbitDB on Pi (`npm install orbit-db`)
2. Create document stores mirroring current SQLite schema
3. Build sync layer: SQLite → OrbitDB (one-way initial, then bidirectional)
4. Run both for 30 days, verify data integrity
5. Switch reads to OrbitDB, keep SQLite as backup
6. Eventually decommission SQLite
**Cost:** Free (OrbitDB), Ceramic has free tier
**Risk:** No SQL queries (OrbitDB is key-value/document), complex migrations
**Alternative:** Keep SQLite but replicate to multiple Pis (distributed = good enough)

## Phase 5: Payments (Bank/ACH/Plaid → Crypto-only)
**Current:** Plaid ACH, wire transfers, Zelle via bank
**Target:** USDC, RLUSD, Lightning Network, on-chain payments
**Steps:**
1. Set up Lightning node on Pi (LND or Core Lightning)
2. Generate payment QR codes for invoices (PayBooks integration)
3. Add BTC/USDC payment options to PayBooks (already partially done — RLUSD + USDC)
4. Accept Lightning invoices for estimates
5. Convert crypto → fiat via exchange (Coinbase/Kraken) as needed
6. Keep bank account for fiat-only clients (transition period)
**Cost:** Free (self-hosted Lightning), exchange fees ~0.5-1%
**Risk:** Price volatility (use stablecoins), client adoption

## Phase 6: File Storage (Internal Drive + GDrive → IPFS + Filecoin)
**Current:** /media/allenai/Expansion (Body tier), Google Drive (Brain tier)
**Target:** IPFS pinning + Filecoin for cold storage
**Steps:**
1. Install IPFS on Pi, configure pinned storage to external drive
2. Pin all Dewey Brain files to local IPFS node
3. Set up Filecoin storage deal via Lotus or Filecoin Station
4. Archive old files to Filecoin (cheaper than self-hosting long-term)
5. Use IPFS companion browser extension for access
6. GDrive becomes read-only backup, then decommission
**Cost:** IPFS free (self-hosted), Filecoin ~$0.03/GB/month
**Risk:** Pinning requires always-on node, Filecoin retrieval latency

## Phase 7: Identity (Emails/Logins → DID / Wallet Auth)
**Current:** Email/password logins for Academy, PayBooks, Command Center
**Target:** Wallet-based authentication (MetaMask sign-in, DID)
**Steps:**
1. Implement Sign-In with Ethereum (SIWE) for Academy
2. Add MetaMask login to Command Center
3. Create DID for Derrell (using ceramic-sdk or ethr-did)
4. Map DID to Blacktech identity (wallet address → profile)
5. Keep email/password as fallback during transition
6. Eventually require wallet auth for admin access
**Cost:** Free (open-source libraries)
**Risk:** UX barrier for non-crypto users (contractors, clients)

## Phase 8: Calendar (Google Calendar → Self-Hosted CalDAV)
**Current:** Google Calendar API via google_api.py
**Target:** Radicale or Baïkal (CalDAV server on Pi)
**Steps:**
1. Install Radicale on Pi (`pip install radicale`)
2. Configure calendar + tasks backend
3. Export Google Calendar (.ics), import to Radicale
4. Update email_calendar_pipeline.py to write to CalDAV instead of Google API
5. Connect phone/desktop calendar app to CalDAV URL
6. Test invites (CalDAV supports iMIP for email invitations)
**Cost:** Free (self-hosted)
**Risk:** No native Google integration, mobile push may lag

## Phase 9: Video Hosting (PeerTube → already decentralized ✅)
**Status:** Already done
**Current:** LiveVue (PeerTube on Pi, federated)
**Action:** No migration needed. Ensure federation is active (follow other instances, allow followers).

## Phase 10: Academy (self-hosted → already decentralized ✅)
**Status:** Already done
**Current:** academy.blacktechsolutionscorp.com (Pi-hosted, port 8115)
**Action:** No migration needed. Optionally pin course videos to IPFS for redundancy.

---

## Migration Priority (by impact + feasibility)

| Priority | Phase | Why |
|----------|-------|-----|
| 1st | Phase 8 (Calendar) | Easy, self-hosted, removes Google dependency |
| 2nd | Phase 3 (Email) | Hard but biggest sovereignty win |
| 3rd | Phase 6 (File Storage) | IPFS pinning is straightforward |
| 4th | Phase 5 (Payments) | Already partially done (USDC/RLUSD) |
| 5th | Phase 7 (Identity) | Security improvement, wallet auth |
| 6th | Phase 2 (Hosting) | IPFS reliability concern, needs testing |
| 7th | Phase 4 (Database) | Most complex, SQLite works fine distributed |

## Timeline Estimate
- **Phases 8-9-10:** 1-2 weeks (easy/already done)
- **Phases 3, 6:** 1-2 months each
- **Phases 2, 5, 7:** 2-3 months each
- **Phase 4:** 3-6 months (most complex)

**Total full migration:** ~12-18 months running hybrid throughout

---
*Created Jun 29, 2026. Derrell's insight: "This system we have is both" — hybrid model is the bridge to full decentralization.*