# Device Blocklist Index

## How to assign blocklists to specific devices:

### Step 1: Identify the device
Check Pi-hole admin panel: http://10.0.0.100/admin
Go to Group Management → Clients

### Step 2: Create a group for the device
Group Management → Groups → Add Group
Name: e.g., "Kids", "IoT", "Work-Only"

### Step 3: Assign the client to the group
Group Management → Clients → Add Client (by IP or MAC)
Select the group

### Step 4: Assign blocklists to the group
Group Management → Adlists
Enable the appropriate blocklist for that group only

## Available Blocklists:
- global-blocked.list → Everyone (drugs, malware, gambling)
- iot-blocked.list → Smart home devices (Ring, Samsung, etc.)
- kids-safe.list → Children's devices (social media, adult content)
- work-only.list → Business devices (blocks entertainment)

## Current Network Devices (update this as needed):
# No active leases yet - will populate when devices connect

## Work-Only Profile
**File:** `work-only.list`
**Purpose:** Business devices — blocks entertainment, streaming, gaming, social media, shopping, sports betting, and dating sites.

### What is ALLOWED:
- Email (Gmail, Outlook, Yahoo)
- Business tools (QuickBooks, Basecamp, CRMs)
- Contractor/supplier sites
- Banking/finance
- Government/permits
- EV/solar industry sites
- News (general, not tabloid)
- Maps/weather
- Code repositories
- Video conferencing (Zoom, Teams, Meet)

### What is BLOCKED:
- All social media
- All streaming (Netflix, YouTube, Twitch)
- All gaming platforms
- Music streaming
- Online shopping
- Sports betting/gambling
- Dating sites
- Tabloid/clickbait news

## How to set Work-Only on a device:
1. Find device IP in Pi-hole admin → http://10.0.0.100/admin
2. Group Management → Groups → Add "Work-Devices"
3. Group Management → Clients → Add device MAC/IP → Assign to "Work-Devices"
4. Group Management → Adlists → Add `work-only.list` → Enable for "Work-Devices" only
