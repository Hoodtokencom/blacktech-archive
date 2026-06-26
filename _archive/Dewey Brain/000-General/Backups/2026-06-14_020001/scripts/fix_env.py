#!/usr/bin/env python3
"""Fix .env file with correct Groq API key."""

import os

# Full key from user
FULL_KEY = "gsk_Cx...nv"

# Write clean .env
with open('/home/allenai/.env', 'w') as f:
    f.write("# Blacktech AI Pipeline Environment Variables\n")
    f.write("# Do NOT share this file. Keep restricted.\n\n")
    f.write(f"GROQ_API_KEY={FULL_KEY}\n")

# Lock permissions
os.chmod('/home/allenai/.env', 0o600)

# Verify
with open('/home/allenai/.env') as f:
    for line in f:
        if line.startswith('GROQ_API_KEY='):
            val = line.strip().split('=', 1)[1]
            print(f"✅ Key saved: length={len(val)}, prefix={val[:15]}, suffix={val[-10:]}")
            
            # Quick API test
            import urllib.request, json
            body = json.dumps({
                "model": "llama-3.1-8b-instant",
                "messages": [
                    {"role": "system", "content": "You are fast."},
                    {"role": "user", "content": "Say hello in 3 words"}
                ],
                "temperature": 0.3,
                "max_tokens": 20
            }).encode()
            req = urllib.request.Request(
                "https://api.groq.com/openai/v1/chat/completions",
                data=body,
                headers={"Authorization": f"Bearer {val}", "Content-Type": "application/json"}
            )
            try:
                with urllib.request.urlopen(req, timeout=15) as r:
                    data = json.loads(r.read().decode())
                    text = data["choices"][0]["message"]["content"]
                    print(f"✅ Groq API works: '{text}'")
            except Exception as e:
                print(f"❌ API test: {e}")
            break
