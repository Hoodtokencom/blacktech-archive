#!/usr/bin/env python3
"""Triple-Play Auto-Pipeline -- GEMINI -> OLLAMA -> CLAUDE"""

import os
import sys
import time
import json
import urllib.request
import base64

# -- CONFIG --------------------------------------------------
TELEMETRY_URL = os.getenv("TELEMETRY_URL", "http://localhost:8094/api/telemetry")
TOLL_FILE     = "/home/allenai/data/ai_toll_meter.txt"
OLLAMA_HOST   = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL  = os.getenv("OLLAMA_MODEL", "phi3")
GEMINI_MODEL  = "gemini-2.5-flash"
GEMINI_BASE   = "https://generativelanguage.googleapis.com/v1beta"

MIN_OLLAMA_CHARS = 200

# Base64 encoded key -- decoded at runtime
_ENCODED = "QVEuQWI4Uk42SlFBTDJxTjhsSVB0d1FSemFZWUhjdUxwc3IyS1hGNjdDNkFvQkpfM1ZWZUE="

# -- LOAD .ENV via VAULT --------------------------------------
import vault_loader
vault_loader.load_env()

# -- HELPERS -------------------------------------------------
def push_telemetry(metrics):
    try:
        body = json.dumps(metrics).encode()
        req = urllib.request.Request(
            TELEMETRY_URL, data=body,
            headers={"Content-Type": "application/json"}, method="POST"
        )
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status == 200
    except Exception as e:
        print(f"Warning: Telemetry push failed: {e}")
        return False

def append_toll(task, cost):
    try:
        with open(TOLL_FILE, "a") as f:
            dt = time.strftime("%m/%d/%y")
            f.write(f"|  {dt}  | {task[:35]:35} |${cost:8.6f} |       |\n")
    except Exception as e:
        print(f"Warning: Toll write failed: {e}")

def ollama_generate(prompt):
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.3, "num_ctx": 4096}
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
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        # Fallback: decode from embedded base64
        try:
            key = base64.b64decode(_ENCODED).decode()
        except:
            pass
    if not key:
        return "GEMINI_API_KEY missing", {"status": "skipped", "cost": 0, "model": GEMINI_MODEL}

    start = time.time()
    try:
        url = GEMINI_BASE + "/models/" + GEMINI_MODEL + ":generateContent?key=" + key
        body = json.dumps({
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.3, "maxOutputTokens": 4096}
        }).encode()

        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.loads(r.read().decode())
            latency = round(time.time() - start, 2)
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            usage = data.get("usageMetadata", {})
            ti = usage.get("promptTokenCount", 0)
            to = usage.get("candidatesTokenCount", 0)
            cost = round((ti / 1_000_000 * 0.15) + (to / 1_000_000 * 0.60), 6)
            return text, {
                "tokens_in": ti, "tokens_out": to, "cost": cost,
                "latency_seconds": latency, "model": GEMINI_MODEL,
                "status": "completed"
            }
    except urllib.error.HTTPError as e:
        err = json.loads(e.read().decode())
        return f"Gemini HTTP {e.code}: {err['error']['message']}", {
            "status": "failed", "cost": 0, "latency_seconds": round(time.time()-start,2),
            "model": GEMINI_MODEL, "error": f"HTTP {e.code}"
        }
    except Exception as e:
        return f"Gemini error: {e}", {
            "status": "failed", "cost": 0, "latency_seconds": round(time.time()-start,2),
            "model": GEMINI_MODEL, "error": str(e)
        }

def claude_run(prompt):
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        return "ANTHROPIC_API_KEY missing", {
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
        cost = round((ti / 1_000_000 * 3) + (to / 1_000_000 * 15), 6)
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

def classify_complexity(task):
    complex_keywords = [
        "code", "debug", "algorithm", "architecture", "refactor",
        "security", "optimize", "strategy", "compliance", "permit",
        "electrical code", "NEC", "Chicago", "ComEd", "negotiate"
    ]
    task_lower = task.lower()
    score = sum(1 for kw in complex_keywords if kw in task_lower)
    if score >= 2:
        return "high"
    elif score == 1:
        return "medium"
    return "low"

# -- MAIN ----------------------------------------------------
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 triple_play_pipeline.py \"Your task here\"")
        sys.exit(1)

    user_task = sys.argv[1]
    total_cost = 0
    outputs = {}
    complexity = classify_complexity(user_task)

    print("=" * 60)
    print("TRIPLE-PLAY PIPELINE -- GEMINI -> OLLAMA -> CLAUDE")
    print("=" * 60)
    print(f"Task: {user_task}")
    print(f"Complexity guess: {complexity.upper()}")
    print("-" * 60)

    # STAGE 1: GEMINI
    print(f"\nSTAGE 1 -- Gemini {GEMINI_MODEL} (Draft & Parse)")
    gemini_prompt = f"""Complete this task professionally and concisely:

{user_task}

Rules:
- Provide a complete, usable answer
- No filler, no "Here is the..." introductions
- If you cannot complete it fully, say PARTIAL and summarize what is missing"""

    gemini_out, gemini_metrics = gemini_run(gemini_prompt)
    outputs["gemini"] = gemini_out
    total_cost += gemini_metrics.get("cost", 0)
    push_telemetry(gemini_metrics)
    print(f"Status: {gemini_metrics['status'].upper()} | Cost: ${gemini_metrics.get('cost',0):.6f}")
    print(f"Output preview: {gemini_out[:200]}...")

    gemini_ok = gemini_metrics['status'] == 'completed' and len(gemini_out) > 50

    if gemini_ok and complexity == "low" and "PARTIAL" not in gemini_out and len(gemini_out) > MIN_OLLAMA_CHARS:
        print(f"\nQUALITY GATE: Gemini output sufficient. Stopping.")
        final_out = gemini_out
        claude_metrics = {"status": "skipped", "cost": 0, "model": "claude-sonnet-4-6"}
        ollama_metrics = {"status": "skipped", "cost": 0, "model": f"ollama-{OLLAMA_MODEL}"}
        outputs["ollama"] = "SKIPPED"
        outputs["claude"] = "SKIPPED"
    else:
        # STAGE 2: OLLAMA
        print(f"\nSTAGE 2 -- Ollama/{OLLAMA_MODEL} (Local Polish)")
        ollama_prompt = f"""You are an expert electrical contractor and energy advisor in Chicago.

Original task: {user_task}

Draft from Gemini: {gemini_out[:3000]}

Your job: Produce the FINAL, polished response. Fix errors, add details, format cleanly."""

        ollama_out, ollama_ok = ollama_generate(ollama_prompt)
        ollama_metrics = {
            "model": f"ollama-{OLLAMA_MODEL}", "status": "completed" if ollama_ok else "failed",
            "cost": 0, "tokens_in": 0, "tokens_out": 0
        }
        outputs["ollama"] = ollama_out
        push_telemetry(ollama_metrics)
        print(f"Status: {'COMPLETED' if ollama_ok else 'FAILED'} | Cost: $0.00")
        print(f"Output preview: {ollama_out[:200]}...")

        if not ollama_ok or len(ollama_out) < MIN_OLLAMA_CHARS or "error" in ollama_out.lower():
            print(f"\nQUALITY GATE: Ollama failed. Escalating to Claude.")
            escalate = True
        elif complexity == "high":
            print(f"\nCOMPLEXITY GATE: High-complexity task. Escalating to Claude.")
            escalate = True
        else:
            print(f"\nQUALITY GATE: Ollama output sufficient. Stopping.")
            escalate = False
            final_out = ollama_out
            claude_metrics = {"status": "skipped", "cost": 0, "model": "claude-sonnet-4-6"}
            outputs["claude"] = "SKIPPED"

        if escalate:
            # STAGE 3: CLAUDE
            print(f"\nSTAGE 3 -- Claude Sonnet 4 (Strategic Escalation)")
            claude_prompt = f"""You are an expert electrical contractor and energy advisor in Chicago.
The user wants: {user_task}

Previous attempts:
- Gemini draft: {gemini_out[:1500]}
- Ollama attempt: {ollama_out[:1500]}

Produce the FINAL, professional, accurate response. This is the authoritative answer."""

            claude_out, claude_metrics = claude_run(claude_prompt)
            outputs["claude"] = claude_out
            total_cost += claude_metrics.get("cost", 0)
            push_telemetry(claude_metrics)
            print(f"Status: {claude_metrics['status'].upper()} | Cost: ${claude_metrics.get('cost',0):.6f}")
            print(f"Output preview: {claude_out[:200]}...")
            
            # FIX: If Claude fails/skipped, fall back to best available output
            if claude_metrics['status'] in ('failed', 'skipped'):
                print(f"\nFALLBACK: Claude unavailable. Using best previous output.")
                if ollama_ok and len(ollama_out) >= MIN_OLLAMA_CHARS:
                    final_out = ollama_out
                else:
                    final_out = gemini_out
            else:
                final_out = claude_out

    # FINAL
    print("\n" + "=" * 60)
    print("PIPELINE COMPLETE")
    print("=" * 60)
    print(f"Gemini: {gemini_metrics['status'].upper()} -- ${gemini_metrics.get('cost',0):.6f}")
    print(f"Ollama: {ollama_metrics['status'].upper()} -- $0.00")
    print(f"Claude: {claude_metrics['status'].upper()} -- ${claude_metrics.get('cost',0):.6f}")
    print(f"\nTOTAL COST: ${total_cost:.6f}")
    print("=" * 60)

    out_file = f"/tmp/pipeline_output_{int(time.time())}.txt"
    with open(out_file, "w") as f:
        f.write(f"TASK: {user_task}\n")
        f.write(f"COMPLEXITY: {complexity}\n\n")
        f.write(f"GEMINI:\n{outputs.get('gemini','')}\n\n")
        f.write(f"OLLAMA:\n{outputs.get('ollama','')}\n\n")
        f.write(f"CLAUDE (FINAL):\n{outputs.get('claude','')}\n\n")
        f.write(f"---\nFINAL OUTPUT:\n{final_out}\n")
    print(f"Full output saved: {out_file}")

    append_toll(user_task, total_cost)
    print(f"Toll meter updated: +${total_cost:.6f}")
