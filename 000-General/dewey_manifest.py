#!/usr/bin/env python3
"""dewey_manifest.py — the ONLY place Dewey sections are defined.

Every pipeline script imports from here. Never hardcode a section list again.

    from dewey_manifest import (drive_folders, sections, content_map,
                                code_to_folder, folder_names, ai_code_list,
                                ai_codes, filename_rules)

Invariants (also recorded in dewey_manifest.json):
  * the folder tree is the shelf        -> where a file physically lives
  * dewey_catalog.json is the card catalog -> REBUILT from the tree every sync
  * dewey_blockchain.json is the ledger -> append-only, NEVER rebuilt
"""
import json
import os

MANIFEST_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "dewey_manifest.json")


def _data():
    with open(MANIFEST_PATH, encoding="utf-8") as f:
        return json.load(f)


def load():
    """All section rows, in canonical order (specific sections first, broad last)."""
    return _data()["sections"]


def drive_folders():
    """{folder_name: drive_folder_id} — replaces DRIVE_FOLDERS in sync + pull."""
    return {r["folder"]: r["drive_id"] for r in load() if r.get("drive_id")}


def sections():
    """{3-digit code: display name} — replaces SECTIONS in sync."""
    return {c: r["name"] for r in load() for c in r.get("codes", [])}


def content_map():
    """[(folder_name, regex_string)] — replaces CONTENT_MAP in the router.

    Returns RAW STRINGS, not compiled patterns: the router calls
    re.search(pattern, text, re.IGNORECASE). Compiling here would break it.
    """
    return [(r["folder"], r["regex"]) for r in load() if r.get("regex")]


def filename_rules():
    """[(keyword, folder_name)] in EXACT precedence order — replaces the router's
    DEWEY_MAP. Order is preserved from the manifest: first keyword match wins."""
    return [(k, v) for k, v in _data()["filename_rules"]]


def code_to_folder():
    """{code: folder_name} — replaces dewey_to_folder()'s inline dict."""
    return {c: r["folder"] for r in load() for c in r.get("codes", [])}


def folder_names():
    """Canonical section folder names, in order."""
    return [r["folder"] for r in load()]


def ai_code_list():
    """The 'Available codes' block for AI_CLASSIFY_PROMPT, generated."""
    return "\n".join(f"  {r['code']} - {r['description']}" for r in load())


def ai_codes():
    """Every code the AI is allowed to return (so the parser can accept them all)."""
    return tuple(r["code"] for r in load())


if __name__ == "__main__":
    rows = load()
    print(f"sections         : {len(rows)}")
    print(f"drive_folders    : {len(drive_folders())}")
    print(f"codes            : {len(code_to_folder())}")
    print(f"with regex       : {len(content_map())}")
    print(f"filename_rules   : {len(filename_rules())}")
    print(f"ai_codes         : {len(ai_codes())}")
    print(f"missing drive_id : {[r['folder'] for r in rows if not r.get('drive_id')]}")
    print(f"missing regex    : {[r['folder'] for r in rows if not r.get('regex')]}")
