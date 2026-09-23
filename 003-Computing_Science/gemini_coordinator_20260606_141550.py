#!/usr/bin/env python3
"""
Gemini 2.0 Flash-Lite Coordinator — Triple-Play Pipeline
Sits between Claude Opus (strategy) and Ollama/Hermes (local execution)

Install: pip install google-genai
Export:  export GEMINI_API_KEY="your-key"
Run:     python3 scripts/gemini_coordinator.py
"""

import os
import time
import json
import urllib.request
from google import genai
from google.genai import types

TELEMETRY_URL = "http://localhost:8094/api/telemetry"

def push_to_dashboard(metrics: dict) -> bool:
    """Sends metrics to BFN /monitor dashboard."""
    try:
        body = json.dumps(metrics).encode()
        req = urllib.request.Request(
            TELEMETRY_URL, data=body,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status == 200
    except Exception as e:
        print(f"⚠️ Dashboard push failed: {e}")
        return False

def run_gemini_coordinator(payload_context: str, task_instructions: str):
    """
    Runs Gemini 2.0 Flash-Lite for fast routing/parsing.
    Returns: (response_text, metrics_dict)
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not set. Run: export GEMINI_API_KEY='your-key'")

    client = genai.Client(api_key=api_key)

    SYSTEM_INSTRUCTION = """ROLE: You are a strict data formatting utility.
DUTY: Convert the input strategy text into the exact JSON schema requested.
BOUNDARIES:
- Do NOT add any conversational text, pleasantries, or explanations.
- Do NOT attempt to write the final proposal text.
- Do NOT expand on the strategy provided.
- Output ONLY the raw JSON object starting with { and ending with }."""

    prompt = f"""Context: {payload_context}
Task: {task_instructions}
Respond with clean, structured JSON."""

    print("⚡ Firing Gemini 2.0 Flash-Lite...")
    start = time.time()

    try:
        response = client.models.generate_content(
            model='gemini-2.0-flash-lite',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                system_instruction=SYSTEM_INSTRUCTION
            )
        )
        latency = round(time.time() - start, 2)

        tokens_in = response.usage_metadata.prompt_token_count
        tokens_out = response.usage_metadata.candidates_token_count

        # ✅ ACTUAL Gemini 2.0 Flash-Lite pricing (June 2026)
        cost = (tokens_in / 1_000_000 * 0.075) + (tokens_out / 1_000_000 * 0.30)

        metrics = {
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "cost": round(cost, 6),
            "latency_seconds": latency,
            "model": "gemini-2.0-flash-lite",
            "status": "completed"
        }
        print(f"📊 Done. ${cost:.6f} | In:{tokens_in} Out:{tokens_out} | {latency}s")
        return response.text, metrics

    except Exception as e:
        print(f"❌ Gemini failed: {e}")
        return None, {
            "tokens_in": 0, "tokens_out": 0, "cost": 0,
            "latency_seconds": round(time.time() - start, 2),
            "model": "gemini-2.0-flash-lite", "status": "failed", "error": str(e)
        }


# ── CLI DEMO ─────────────────────────────────────────────
if __name__ == "__main__":
    text, metrics = run_gemini_coordinator(
        "Raw lead data: name=Derrell, phone=312-493-6775, zip=60628, service=electrical panel upgrade",
        "Parse into structured JSON with keys: name, phone, zip, service_type, priority. Flag if zip is outside 60628."
    )
    print("\n--- OUTPUT ---")
    print(text)
    print("\n--- METRICS ---")
    print(json.dumps(metrics, indent=2))

    if push_to_dashboard(metrics):
        print("\n✅ Pushed to dashboard")
    else:
        print("\n❌ Dashboard push failed")
