#!/usr/bin/env python3
"""Print the full prompt of the Dewey 3-Way Mirror Sync cron job (a158fa374c75)."""
import json

jobs = json.load(open('/home/allenai/.hermes/profiles/derrell-black/cron/jobs.json'))
items = jobs if isinstance(jobs, list) else jobs.get('jobs', [])
for j in items:
    if j.get('id') == 'a158fa374c75':
        print(json.dumps({k: j.get(k) for k in ('name', 'schedule', 'prompt', 'paused', 'model')}, indent=2))