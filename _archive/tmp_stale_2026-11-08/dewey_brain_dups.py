#!/usr/bin/env python3
"""Find case-duplicate keys INSIDE the brain (ext4 allows index.md + INDEX.md).
These poison the exFAT Body mirror: only one can exist there, rsync no-ops silently."""
import os, hashlib

brain = '/home/allenai/blacktech_brain'

bset = {}
for dirpath, dirs, files in os.walk(brain):
    dirs[:] = [d for d in dirs if d != '__pycache__']
    for f in files:
        if f.startswith('.') or f.endswith(('.pyc', '.tmp')):
            continue
        rel = os.path.relpath(os.path.join(dirpath, f), brain)
        bset.setdefault(rel.lower(), set()).add(rel)

dups = {k: sorted(v) for k, v in bset.items() if len(v) > 1}
print(f"Brain case-duplicate keys: {len(dups)}")
for k, v in dups.items():
    print(f"  {k}:")
    for rel in v:
        p = os.path.join(brain, rel)
        h = hashlib.sha256(open(p, 'rb').read()).hexdigest()[:12]
        with open(p, 'r', errors='replace') as fh:
            head = fh.read(60).replace('\n', '\\n')
        print(f"    {rel}  sha:{h}  head: {head!r}")