#!/usr/bin/env python3
"""Inspect Dewey-related cron jobs in the active profile + GitHub archive state."""
import json, subprocess

jobs = json.load(open('/home/allenai/.hermes/profiles/derrell-black/cron/jobs.json'))
items = jobs if isinstance(jobs, list) else jobs.get('jobs', [])
print(f"total jobs: {len(items)}")
for j in items:
    name = str(j.get('name') or '')
    if any(k in name.lower() for k in ('dewey', 'mirror', 'body sync', 'weekly')):
        print(f"• {name} | id={j.get('id')} | sched={j.get('schedule')}")
        for k in ('script', 'command', 'prompt'):
            v = j.get(k)
            if v:
                print(f"    {k}: {str(v)[:180]}")

print("===GITHUB-ARCHIVE===")
r = subprocess.run(['git', '-C', '/home/allenai/blacktech_archive', 'log', '--oneline', '-3'],
                   capture_output=True, text=True)
print(r.stdout.strip() or r.stderr.strip())
r = subprocess.run(['git', '-C', '/home/allenai/blacktech_archive', 'status', '--porcelain'],
                   capture_output=True, text=True)
lines = r.stdout.splitlines()
print(f"uncommitted entries: {len(lines)}")
for l in lines[:5]:
    print(f"  {l}")