#!/usr/bin/env python3
"""
Blacktech Passcode Vault

Simple encrypted key-value store for service credentials.
Uses Fernet symmetric encryption. The key is derived from a master
passphrase + salt, so the vault file can sit on Drive safely.

Usage:
  passcode_vault.py set hostgator:payroll --value 'Newproject26$'
  passcode_vault.py get hostgator:payroll
  passcode_vault.py list
"""

import argparse
import base64
import getpass
import json
import os
import sys
from pathlib import Path

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

VAULT_PATH = Path('/home/allenai/blacktech_brain/657-Accounting_Finance/passcode_vault.enc')
SALT_PATH = VAULT_PATH.with_suffix('.salt')


def _derive_key(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=480000,
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode()))


def _load_salt() -> bytes:
    if SALT_PATH.exists():
        return SALT_PATH.read_bytes()
    salt = os.urandom(16)
    SALT_PATH.write_bytes(salt)
    os.chmod(SALT_PATH, 0o600)
    return salt


def _get_fernet(password: str) -> Fernet:
    return Fernet(_derive_key(password, _load_salt()))


def load(password: str) -> dict:
    f = _get_fernet(password)
    if not VAULT_PATH.exists():
        return {}
    try:
        plaintext = f.decrypt(VAULT_PATH.read_bytes()).decode()
        return json.loads(plaintext)
    except Exception as e:
        print(f"Decryption failed: {e}", file=sys.stderr)
        sys.exit(1)


def save(password: str, data: dict) -> None:
    f = _get_fernet(password)
    VAULT_PATH.write_bytes(f.encrypt(json.dumps(data, indent=2).encode()))
    os.chmod(VAULT_PATH, 0o600)


def cmd_set(args):
    pw = getpass.getpass('Master passphrase: ')
    value = args.value or getpass.getpass('Value: ')
    data = load(pw)
    data[args.key] = value
    save(pw, data)
    print(f"Stored: {args.key}")


def cmd_get(args):
    pw = getpass.getpass('Master passphrase: ')
    data = load(pw)
    if args.key not in data:
        print(f"Key not found: {args.key}")
        sys.exit(1)
    print(data[args.key])


def cmd_list(args):
    pw = getpass.getpass('Master passphrase: ')
    data = load(pw)
    for k in sorted(data):
        print(k)


def main():
    p = argparse.ArgumentParser(description='Blacktech encrypted passcode vault')
    sub = p.add_subparsers(dest='command', required=True)

    sp = sub.add_parser('set', help='store a value')
    sp.add_argument('key')
    sp.add_argument('--value')
    sp.set_defaults(func=cmd_set)

    gp = sub.add_parser('get', help='retrieve a value')
    gp.add_argument('key')
    gp.set_defaults(func=cmd_get)

    lp = sub.add_parser('list', help='list keys')
    lp.set_defaults(func=cmd_list)

    args = p.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
