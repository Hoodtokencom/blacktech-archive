# Decentralized Test Node — Results

**Date:** Jun 29, 2026
**Location:** Pi #1 (Docker containers), /home/allenai/decentralized-test/
**Goal:** Test fully decentralized alternatives to current centralized services

## Services Tested

### 1. IPFS (InterPlanetary File System) ✅
- **Image:** ipfs/kubo:latest (Docker)
- **Peer ID:** 12D3KooWKuRoFRdN6MuQNkBZ6QeHF2dZ4yLAEJ2KwXUUrXTZUVms
- **Swarm Peers:** 195 connected nodes
- **Ports:** 4001 (P2P), 5001 (API), 8122 (Gateway)
- **Test:** Added file → CID QmfXJ7dkNbUbgMm2PAZS9XnU1Ze8iJUjZNJdDtnjmdjtW6 → retrieved via gateway ✅
- **Verdict:** Works. Content-addressed storage, no central server. 195 peers = files retrievable from network.

### 2. Radicale (CalDAV Calendar) ✅
- **Image:** kozea/radicale:latest (Docker)
- **Ports:** 5232
- **User:** derrell (htpasswd/bcrypt)
- **Calendar:** blacktech-calendar
- **Test:** Created calendar → added event → retrieved via CalDAV PROPFIND ✅
- **Verdict:** Works. Replaces Google Calendar. Compatible with Apple Calendar, Thunderbird, DAVx5 (Android).
- **Config:** owner_only rights type, filesystem storage at /var/lib/radicale/collections

### 3. Nginx Web Server ✅
- **Image:** nginx:alpine (Docker)
- **Ports:** 8120
- **Test:** Serves static HTML dashboard ✅
- **Verdict:** Works. Can serve web content without external hosting.

## Decentralization Scorecard

| Service | Status | Centralized Alternative |
|---------|--------|----------------------|
| Storage (IPFS) | ✅ DECENTRALIZED | Google Drive |
| Calendar (Radicale) | ✅ DECENTRALIZED | Google Calendar |
| Web (Nginx) | ✅ DECENTRALIZED | Cloudflare Pages |
| DNS (Cloudflare) | ❌ CENTRALIZED | → ENS/HNS |
| Email (HostGator) | ❌ CENTRALIZED | → Mailcow |
| Payments (Bank/Plaid) | ❌ CENTRALIZED | → Lightning/USDC |

## Resource Usage
- IPFS: ~200MB RAM
- Radicale: ~30MB RAM
- Nginx: ~10MB RAM
- Total: ~240MB (well within Pi capacity)

## Pitfalls Encountered
1. Port conflicts — Pi has many services on 8080-8099, used 8120-8122 instead
2. Radicale image — `tomssquest/radicale` doesn't exist, `kozea/radicale` works
3. Radicale rights — needed `owner_only` type in config, and proper MKCOL with XML body
4. IPFS API — requires POST not GET for `/api/v0/*` endpoints
5. IPFS buffer — UDP buffer size warning (208 kiB vs 7168 kiB wanted) — non-fatal

## Next Steps (Phase 2)
1. Email — Mailcow on Pi (biggest sovereignty win)
2. DNS — ENS or Handshake naming
3. Payments — Lightning node + USDC integration
4. Identity — SIWE (Sign-In with Ethereum) for wallet auth

---
*Test environment lives at /home/allenai/decentralized-test/ — run `docker compose up -d` to start, `docker compose down` to stop.*