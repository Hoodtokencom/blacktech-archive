#!/usr/bin/env python3
"""
find_brain.py — search the Blacktech Library Brain.

Usage:
  find_brain.py email               # full-text search
  find_brain.py --section 600       # list docs in Technology
  find_brain.py --section 657 --all # list all files under 657-*
  find_brain.py --map               # print full catalog tree
"""

import argparse
import os
import re
import sys
from pathlib import Path

ROOT = Path('/home/allenai/blacktech_brain')


def normalize_section(s: str) -> str:
    s = s.strip().lstrip('0')
    if not s:
        return '000'
    return s


def section_match(name: str, query: str) -> bool:
    """Return True if folder name matches query like '6', '65', '657'."""
    prefix = name.split('-')[0]
    return prefix.startswith(query)


def list_sections(query: str = None) -> list:
    sections = sorted([d for d in ROOT.iterdir() if d.is_dir()])
    if query:
        sections = [d for d in sections if section_match(d.name, query)]
    return sections


def files_in_section(section_path: Path) -> list:
    out = []
    for root, _, files in os.walk(section_path):
        for f in files:
            if f.startswith('.'):
                continue
            out.append(Path(root) / f)
    return sorted(out)


def grep_files(pattern: str, paths: list) -> list:
    hits = []
    rx = re.compile(pattern, re.IGNORECASE)
    for p in paths:
        try:
            text = p.read_text(errors='ignore')
        except Exception:
            continue
        lines = text.splitlines()
        for i, line in enumerate(lines, 1):
            if rx.search(line):
                hits.append((p, i, line.strip()))
    return hits


def cmd_search(args):
    pattern = args.query
    sections = list_sections(normalize_section(args.section)) if args.section else list_sections()
    all_files = []
    for s in sections:
        all_files.extend(files_in_section(s))
    hits = grep_files(pattern, all_files)
    if not hits:
        print(f"No matches for: {pattern}")
        return
    current = None
    for p, line_no, line in hits:
        if p != current:
            print(f"\n{p.relative_to(ROOT)}")
            current = p
        print(f"  {line_no:4}: {line[:120]}")


def cmd_section(args):
    sections = list_sections(normalize_section(args.section))
    if not sections:
        print(f"No section matching: {args.section}")
        return
    for s in sections:
        files = files_in_section(s)
        print(f"\n{s.relative_to(ROOT)}/  ({len(files)} files)")
        for f in files:
            rel = f.relative_to(ROOT)
            print(f"  {rel}")


def cmd_map(args):
    for s in list_sections():
        print(s.relative_to(ROOT))
        for f in files_in_section(s):
            print(f"  {f.relative_to(s)}")


def main():
    if len(sys.argv) > 1 and sys.argv[1] not in ('search', 'section', 'map', '-h', '--help'):
        # Bare query default to search
        class Args:
            query = ' '.join(sys.argv[1:])
            section = None
        cmd_search(Args())
        return

    p = argparse.ArgumentParser(description='Search the Blacktech Library Brain')
    sub = p.add_subparsers(dest='command')

    sp = sub.add_parser('search', help='full-text search')
    sp.add_argument('query')
    sp.add_argument('--section', help='limit to section prefix (e.g. 600)')

    sec = sub.add_parser('section', help='list files in section(s)')
    sec.add_argument('section')

    mp = sub.add_parser('map', help='print full catalog tree')

    args = p.parse_args()

    if args.command == 'search':
        cmd_search(args)
    elif args.command == 'section':
        cmd_section(args)
    elif args.command == 'map':
        cmd_map(args)


if __name__ == '__main__':
    main()
