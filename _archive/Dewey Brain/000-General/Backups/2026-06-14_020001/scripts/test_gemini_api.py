#!/usr/bin/env python3
"""Test Gemini API with base64 encoded key"""
import urllib.request, json, base64

# Decode key at runtime
key = base64.b64decode("QVEuQWI4Uk42SlFBTDJxTjhsSVB0d1FSemFZWUhjdUxwc3IyS1hGNjdDNkFvQkpfM1ZWZUE=").decode()

# Build URL
url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
url = url + "?key=" + key

# Call API
body = json.dumps({
    "contents": [{"role": "user", "parts": [{"text": "Say hello in 3 words"}]}]
}).encode()

req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
try:
    with urllib.request.urlopen(req, timeout=15) as r:
        data = json.loads(r.read().decode())
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        print(f"API works: {text.strip()}")
except Exception as e:
    print(f"API fails: {type(e).__name__}: {e}")
