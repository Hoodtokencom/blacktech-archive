#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════
VAULT LOADER — Decrypt .env.enc in memory for scripts
═══════════════════════════════════════════════════════════
Usage in any script:
    from vault_loader import load_env
    load_env()   # decrypts .env.enc → loads into os.environ

Password sources (tried in order):
    1. VAULT_PASSWORD environment variable
    2. ~/.vault_pass file (permission 600)
    3. Prompt user (interactive only)
"""

import os
import sys
import getpass
import vault

ENV_PATH = "/home/allenai/.env"
ENC_PATH = "/home/allenai/.env.enc"
PASS_PATH = "/home/allenai/.vault_pass"

def get_password():
    # 1. Environment variable
    pw = os.getenv("VAULT_PASSWORD", "")
    if pw:
        return pw

    # 2. Password file (permission 600)
    try:
        if os.stat(PASS_PATH).st_mode & 0o777 == 0o600:
            with open(PASS_PATH, "r") as f:
                return f.read().strip()
    except Exception:
        pass

    # 3. Interactive prompt
    if sys.stdin.isatty():
        return getpass.getpass("Vault password: ")

    raise RuntimeError(
        "Vault password not found. Set VAULT_PASSWORD env var or create " + PASS_PATH + " (chmod 600)"
    )

def load_env():
    """Load environment variables from .env or decrypted .env.enc."""
    # Already decrypted file exists?
    if os.path.exists(ENV_PATH):
        _load_plain_env()
        return

    # Encrypted file exists?
    if os.path.exists(ENC_PATH):
        pw = get_password()
        plaintext = vault.decrypt_file(ENC_PATH, pw)
        # Parse and load into os.environ
        for line in plaintext.decode().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, val = line.split("=", 1)
                os.environ[key.strip()] = val.strip().strip('"').strip("'")
        return

    raise FileNotFoundError(f"Neither {ENV_PATH} nor {ENC_PATH} found")

def _load_plain_env():
    with open(ENV_PATH, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, val = line.split("=", 1)
                os.environ[key.strip()] = val.strip().strip('"').strip("'")

if __name__ == "__main__":
    load_env()
    print("✅ Vault unlocked — environment loaded")
    # Print loaded keys (without values)
    keys = [k for k in os.environ if k in ["GEMINI_API_KEY", "ANTHROPIC_API_KEY", "GROQ_API_KEY"]]
    for k in keys:
        print(f"  {k}: {'✅ SET' if os.environ[k] else '❌ EMPTY'}")
