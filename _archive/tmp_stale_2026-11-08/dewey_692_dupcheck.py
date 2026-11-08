#!/usr/bin/env python3
"""692 root-vs-sow duplicate audit: same title at both paths — identical bytes?
Also identify non-SOW root files and which titles Drive actually lacks."""
import hashlib, os

R = "/home/allenai/blacktech_brain/692-Auxiliary_Practices"
root_files = {f: os.path.join(R, f) for f in os.listdir(R) if os.path.isfile(os.path.join(R, f))}
sow_files = {f: os.path.join(R, "sow", f) for f in os.listdir(os.path.join(R, "sow"))}

both = sorted(set(root_files) & set(sow_files))
only_root = sorted(set(root_files) - set(sow_files))
only_sow = sorted(set(sow_files) - set(root_files))
print(f"titles in BOTH root & sow/: {len(both)}")
print(f"root-only: {len(only_root)} -> {only_root[:12]}")
print(f"sow-only: {len(only_sow)} (first 5: {only_sow[:5]})")

def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for c in iter(lambda: f.read(8192), b''):
            h.update(c)
    return h.hexdigest()

diff = []
for i, name in enumerate(both):
    if sha(root_files[name]) != sha(sow_files[name]):
        diff.append(name)
    if i % 500 == 0 and i:
        print(f"  ...compared {i}")
print(f"content MISMATCHES among {len(both)} shared titles: {len(diff)}")
for d in diff[:10]:
    print(f"  MISMATCH: {d}  root={os.path.getsize(root_files[d])}B  sow={os.path.getsize(sow_files[d])}B")

# mtime comparison on a sample to see which set is newer
import time
sample = both[:5]
for s in sample:
    print(f"  {s}: root mtime={time.strftime('%Y-%m-%d', time.localtime(os.path.getmtime(root_files[s])))} "
          f"sow mtime={time.strftime('%Y-%m-%d', time.localtime(os.path.getmtime(sow_files[s])))}")