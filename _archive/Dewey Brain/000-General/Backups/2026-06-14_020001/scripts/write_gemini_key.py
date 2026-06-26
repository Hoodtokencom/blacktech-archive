#!/usr/bin/env python3
"""Write Gemini API key to .env file securely."""
import os

key_value = """AQ.Ab8RN6JQAL2qN8lIPtwQRzaYYHcuLpsr2KXF67C6AoBJ_3VVeA"""

env_path = "/home/allenai/.env"
with open(env_path, "w") as f:
    f.write("# Blacktech AI Pipeline Environment Variables\n")
    f.write("# Do NOT share this file. Keep restricted.\n")
    f.write("# Created: 2026-06-06\n\n")
    f.write("GEMINI_API_KEY=*** + key_value + "\n")

os.chmod(env_path, 0o600)

with open(env_path) as f:
    for line in f:
        if line.startswith("GEMINI_API_KEY=***            saved = line.strip().split("=", 1)[1]
            print(f"✅ Key saved: length={len(saved)}, prefix={saved[:20]}, suffix={saved[-10:]}")
            break
