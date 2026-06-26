#!/usr/bin/env python3
"""Test Gemini key loading from .env"""
import os, urllib.request, json

# Load key
with open('/home/allenai/.env') as f:
    for line in f:
        if 'GEMINI' in line and '=' in line:
            key = line.strip().split('=', 1)[1]
            print(f"Key loaded: length={len(key)}")
            break

# Set env var
os.environ['GEMINI_API_KEY'] = key

# Test API using env var (same as pipeline does)
url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=*** body = json.dumps({
    "contents": [{"role": "user", "parts": [{"text": "Say hello in 3 words"}]}]
}).encode()

req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
try:
    with urllib.request.urlopen(req, timeout=15) as r:
        data = json.loads(r.read().decode())
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        print(f"✅ API works: '{text.strip()}'")
except Exception as e:
    print(f"❌ API fails: {type(e).__name__}: {e}")
