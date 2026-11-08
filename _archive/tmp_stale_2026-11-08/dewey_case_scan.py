#!/usr/bin/env python3
"""Case-collision scan: Body files whose name collides case-insensitively with a
Brain file of a different case (exFAT treats them as one — rsync no-ops silently)."""
import os, json

brain = '/home/allenai/blacktech_brain'
body = '/media/allenai/Expansion/Blacktech_Drive/Dewey_Library'

def walk(root):
    out = []
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d != '__pycache__']
        for f in files:
            if f.startswith('.') or f.endswith(('.pyc', '.tmp')):
                continue
            out.append(os.path.relpath(os.path.join(dirpath, f), root))
    return out

bset = {}
for rel in walk(brain):
    bset.setdefault(rel.lower(), set()).add(rel)

coll = []
for rel in walk(body):
    low = rel.lower()
    if low in bset and rel not in bset[low]:
        coll.append((rel, sorted(bset[low])))

print(f"{len(coll)} case-collision(s):")
for r, b in coll:
    print(f"  BODY: {r}  <->  BRAIN: {b}")

# Also: every index-ish file on Body for size/mtime eyeball
print("---ALL-INDEX-MD-ON-BODY---")
for dirpath, dirs, files in os.walk(body):
    dirs[:] = [d for d in dirs if d != '__pycache__']
    for f in files:
        if f.lower() == 'index.md':
            p = os.path.join(dirpath, f)
            st = os.stat(p)
            print(f"  {st.st_size:>9} bytes  mtime={st.st_mtime:.0f}  {p}")