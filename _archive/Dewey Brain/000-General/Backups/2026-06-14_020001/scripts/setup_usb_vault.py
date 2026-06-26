#!/usr/bin/env python3
"""
Boot-time vault setup.
Copies .vault_pass from USB → /run/user/1000 (RAM-only, no disk)
Creates symlink from /home/allenai/.vault_pass → RAM path.

Triggered by: cron @reboot or manually.
Requires: Blacktech USB drive connected.
"""
import os, shutil, sys

USB_VAULT = "/media/allenai/Expansion/Blacktech_Drive/vault/.vault_pass"
RAM_VAULT = "/run/user/1000/.vault_pass"
SYMLINK = "/home/allenai/.vault_pass"

def setup():
    if not os.path.exists(USB_VAULT):
        print("❌ USB vault missing. Plug in Blacktech USB drive.")
        sys.exit(1)
    
    # Ensure RAM dir exists (systemd creates /run/user/1000 on login)
    os.makedirs(os.path.dirname(RAM_VAULT), exist_ok=True)
    
    # Copy to RAM (no disk write, never hits SD card)
    shutil.copy2(USB_VAULT, RAM_VAULT)
    os.chmod(RAM_VAULT, 0o600)
    
    # Create/overwrite symlink (removes old file or symlink)
    if os.path.exists(SYMLINK) or os.path.islink(SYMLINK):
        os.remove(SYMLINK)
    os.symlink(RAM_VAULT, SYMLINK)
    os.chmod(SYMLINK, 0o600)
    
    print(f"✅ Vault active in RAM: {RAM_VAULT}")
    print(f"🔗 Symlink: {SYMLINK} → RAM")
    
    # Verify decryption works
    try:
        sys.path.insert(0, "/home/allenai/scripts")
        from vault_loader import get_password
        from vault import decrypt_file
        pw = get_password()
        plaintext = decrypt_file("/home/allenai/.env.enc", pw)
        count = plaintext.decode().count("=")
        print(f"🔒 Decryption verified: {count} key(s) readable")
    except Exception as e:
        print(f"⚠️ Decryption check failed: {e}")
    
    return RAM_VAULT

if __name__ == "__main__":
    setup()
