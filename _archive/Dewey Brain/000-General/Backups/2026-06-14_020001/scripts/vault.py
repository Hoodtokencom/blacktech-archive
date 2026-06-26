#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════
BLACKTECH VAULT — Encrypt/decrypt .env files with password
═══════════════════════════════════════════════════════════
AES-256-GCM encryption. Password = key via PBKDF2 (100K iterations).

Usage:
    python3 /home/allenai/scripts/vault.py encrypt /path/to/file.env
    python3 /home/allenai/scripts/vault.py decrypt /path/to/file.env.enc
"""

import os
import sys
import getpass
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
import base64

SALT_SIZE = 16
NONCE_SIZE = 12
ITERATIONS = 100_000

def derive_key(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=ITERATIONS,
    )
    return kdf.derive(password.encode())

def encrypt_file(filepath: str, password: str):
    with open(filepath, "rb") as f:
        plaintext = f.read()

    salt = os.urandom(SALT_SIZE)
    key = derive_key(password, salt)
    nonce = os.urandom(NONCE_SIZE)
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)

    outpath = filepath + ".enc"
    with open(outpath, "wb") as f:
        f.write(salt + nonce + ciphertext)

    # Secure-delete original
    os.remove(filepath)
    print(f"🔒 Encrypted: {outpath}")
    print(f"🗑️  Deleted:  {filepath}")
    return outpath

def decrypt_file(encpath: str, password: str) -> bytes:
    with open(encpath, "rb") as f:
        data = f.read()

    salt = data[:SALT_SIZE]
    nonce = data[SALT_SIZE:SALT_SIZE+NONCE_SIZE]
    ciphertext = data[SALT_SIZE+NONCE_SIZE:]

    key = derive_key(password, salt)
    aesgcm = AESGCM(key)
    plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    return plaintext

def main():
    if len(sys.argv) < 3:
        print("Usage: vault.py encrypt|decrypt /path/to/file")
        sys.exit(1)

    action, filepath = sys.argv[1], sys.argv[2]

    if action == "encrypt":
        pw = getpass.getpass("Enter password: ")
        pw2 = getpass.getpass("Confirm password: ")
        if pw != pw2:
            print("❌ Passwords don't match")
            sys.exit(1)
        encrypt_file(filepath, pw)

    elif action == "decrypt":
        pw = getpass.getpass("Enter password: ")
        plaintext = decrypt_file(filepath, pw)
        outpath = filepath.replace(".enc", "")
        with open(outpath, "wb") as f:
            f.write(plaintext)
        print(f"🔓 Decrypted: {outpath}")

    else:
        print("Usage: vault.py encrypt|decrypt /path/to/file")
        sys.exit(1)

if __name__ == "__main__":
    main()
