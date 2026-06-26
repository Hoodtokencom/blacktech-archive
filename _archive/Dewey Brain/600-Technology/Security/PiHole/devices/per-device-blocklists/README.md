# Per-Device Blocklists

## Format: DEVICE_NAME.list

Each file contains one domain per line to block specifically for that device.

Example: Samsung-TV.list
```
ads.samsungads.com
telemetry.samsung.com
smarttv.com
```

## How to apply:
1. Create a .list file with the device name (use MAC address or IP as identifier)
2. Add domains to block
3. Run: pihole -g (to update gravity)
4. Use Pi-hole Groups to assign blocklists to specific devices

## Device IDs on your network:
# No leases yet - devices will appear after they connect
