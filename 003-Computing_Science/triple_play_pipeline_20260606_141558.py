#!/usr/bin/env python3
"""
Triple-Play Auto-Pipeline
Runs Claude → Gemini → Ollama in sequence for any task.

Usage:
    export ANTHROPIC_API_KEY="sk-ant-..."
    export GEMINI_API_KEY="***"     . /home/allenai/scripts/.env
    python3 /home/allenai/scripts/triple_play_pipeline.py "Write a solar proposal"

Stages:
    1. Claude Opus     → Strategy & planning       ($$$)
    2. Gemini 2.0 FL   → Parse, clean, route       ($)
    3. Ollama/Phi3     → Final execution           (FREE)
"""

import os
import sys
import time
import json
import urllib.request
import subprocess

# ── CONFIG ─────────────────────────────────────────────────
TELEMETRY_URL  = os.getenv("TELEMETRY_URL", "http://localhost:8094/api/telemetry")
TOLL_FILE      = "/home/allenai/data/ai_toll_meter.txt"
OLLAMA_HOST    = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL   = os.getenv("OLLAMA_MODEL", "phi3")

# ── HELPERS ────────────────────────────────────────────────
def push_telemetry(metrics):
    try:
        body = json.dumps(metrics).encode()
        req = urllib.request.Request(
            TELEMETRY_URL, data=body,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status == 200
    except Exception as e:
        print(f"⚠️ Telemetry push failed: {e}")
        return False

def append_toll(task, cost):
    try:
        with open(TOLL_FILE, "a") as f:
            dt = time.strftime("%m/%d/%y")
            f.write(f"║  {dt}  | {task[:35]:35} |${cost:8.6f} |       ║\n")
    except Exception as e:
        print(f"⚠️ Toll write failed: {e}")

def ollama_generate(prompt):
    """Call local Ollama API. Returns (text, ok)."""
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.3}
    }
    try:
        body = json.dumps(payload).encode()
        req = urllib.request.Request(
            f"{OLLAMA_HOST}/api/generate",
            data=body,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=120) as r:
            data = json.loads(r.read().decode())
            return data.get("response", ""), True
    except Exception as e:
        return f"Ollama error: {e}", False

def gemini_run(prompt):
    """Call Gemini Flash-Lite. Returns (text, metrics)."""
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        return "google-genai not installed", {"status": "skipped", "cost": 0, "model": "gemini"}

    key = os.getenv("GEMINI_API_KEY")
    if not key:
        return "GEMINI_API_KEY missing", {"status": "skipped", "cost": 0, "model": "gemini"}

    client = genai.Client(api_key=key)
    start = time.time()
    try:
        resp = client.models.generate_content(
            model='gemini-2.0-flash-lite',
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="text/plain")
        )
        latency = round(time.time() - start, 2)
        ti = resp.usage_metadata.prompt_token_count
        to = resp.usage_metadata.candidates_token_count
        cost = round((ti / 1_000_000 * 0.075) + (to / 1_000_000 * 0.30), 6)
        return resp.text, {
            "tokens_in": ti, "tokens_out": to, "cost": cost,
            "latency_seconds": latency, "model": "gemini-2.0-flash-lite",
            "status": "completed"
        }
    except Exception as e:
        return f"Gemini error: {e}", {
            "status": "failed", "cost": 0, "latency_seconds": round(time.time()-start,2),
            "model": "gemini-2.0-flash-lite", "error": str(e)
        }

def claude_run(prompt):
    """Call Claude (if key available). Returns (text, metrics)."""
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        return "ANTHROPIC_API_KEY missing — Claude stage skipped", {
            "status": "skipped", "cost": 0, "model": "claude-sonnet-4-6"
        }
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=key)
        start = time.time()
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            temperature=0.2,
            messages=[{"role": "user", "content": prompt}]
        )
        latency = round(time.time() - start, 2)
        ti = resp.usage.input_tokens
        to = resp.usage.output_tokens
        cost = round((ti / 1_000_000 * 3) + (to / 1_000_000 * 15), 6)  # Claude Sonnet pricing
        return resp.content[0].text, {
            "tokens_in": ti, "tokens_out": to, "cost": cost,
            "latency_seconds": latency, "model": "claude-sonnet-4-6",
            "status": "completed"
        }
    except Exception as e:
        return f"Claude error: {e}", {
            "status": "failed", "cost": 0, "latency_seconds": round(time.time()-start,2),
            "model": "claude-sonnet-4-6", "error": str(e)
        }

# ── MAIN PIPELINE ──────────────────────────────────────────
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 triple_play_pipeline.py \"Your task here\"")
        sys.exit(1)

    user_task = sys.argv[1]
    stage = 1
    total_cost = 0
    outputs = {}

    print("=" * 55)
    print("🚀  TRIPLE-PLAY AUTO-PIPELINE")
    print("=" * 55)
    print(f"Task: {user_task}")
    print("-" * 55)

    # ── STAGE 1: CLAUDE OPUS ───────────────────────────────
    print(f"\n🔵 STAGE 1 — Claude Opus (Strategy)")
    print("Desc: Create high-level plan and requirements")
    claude_prompt = f"""You are an expert electrical contractor and energy advisor in Chicago.
The user wants: {user_task}

Produce a concise strategy document or requirements list that can be passed
to a local AI worker. Do NOT write the final output — only the blueprint."""

    claude_out, claude_metrics = claude_run(claude_prompt)
    outputs["claude"] = claude_out
    total_cost += claude_metrics.get("cost", 0)
    push_telemetry(claude_metrics)
    print(f"Status: {claude_metrics['status'].upper()} | Cost: ${claude_metrics.get('cost',0):.6f}")
    print(f"Output preview: {claude_out[:180]}...")

    # ── STAGE 2: GEMINI FLASH-LITE ─────────────────────────
    print(f"\n🟢 STAGE 2 — Gemini 2.0 Flash-Lite (Routing)")
    print("Desc: Parse, clean, and prepare for local execution")
    gemini_prompt = f"""You are a fast data-processing router.
Strategy from Claude: {claude_out[:2000]}
Original task: {user_task}

Your job: restructure this into a clean, simple prompt for a local AI worker.
Output only the refined prompt — no commentary."""

    gemini_out, gemini_metrics = gemini_run(gemini_prompt)
    outputs["gemini"] = gemini_out
    total_cost += gemini_metrics.get("cost", 0)
    push_telemetry(gemini_metrics)
    print(f"Status: {gemini_metrics['status'].upper()} | Cost: ${gemini_metrics.get('cost',0):.6f}")
    print(f"Output preview: {gemini_out[:180]}...")

    # ── STAGE 3: OLLAMA / PHI3 ─────────────────────────────
    print(f"\n⚪ STAGE 3 — Ollama/{OLLAMA_MODEL} (Execution)")
    print("Desc: Generate final deliverable locally (FREE)")
    ollama_prompt = f"""You are a helpful assistant. Write the final answer to this task.

Task: {user_task}
Guidance from strategy: {gemini_out[:1500]}

Write a professional, complete response."""

    ollama_out, ollama_ok = ollama_generate(ollama_prompt)
    ollama_metrics = {
        "model": f"ollama-{OLLAMA_MODEL}", "status": "completed" if ollama_ok else "failed",
        "cost": 0, "tokens_in": 0, "tokens_out": 0
    }
    push_telemetry(ollama_metrics)
    print(f"Status: {'COMPLETED' if ollama_ok else 'FAILED'} | Cost: $0.00")
    print(f"Output preview: {ollama_out[:180]}...")

    # ── FINAL ──────────────────────────────────────────────
    print("\n" + "=" * 55)
    print("📊  PIPELINE COMPLETE")
    print("=" * 55)
    print(f"Claude:  {claude_metrics['status'].upper()} — ${claude_metrics.get('cost',0):.6f}")
    print(f"Gemini:  {gemini_metrics['status'].upper()} — ${gemini_metrics.get('cost',0):.6f}")
    print(f"Ollama:  {'COMPLETED' if ollama_ok else 'FAILED'} — $0.00")
    print(f"\n💰 TOTAL COST: ${total_cost:.6f}")
    print("=" * 55)

    # Save final output
    out_file = f"/tmp/pipeline_output_{int(time.time())}.txt"
    with open(out_file, "w") as f:
        f.write(f"TASK: {user_task}\n")
        f.write(f"CLAUDE:\n{claude_out}\n\n")
        f.write(f"GEMINI:\n{gemini_out}\n\n")
        f.write(f"OLLAMA (FINAL):\n{ollama_out}\n")
    print(f"📁 Full output saved: {out_file}")

    # Push toll
    append_toll(user_task, total_cost)
    print(f"📈 Toll meter updated.")
