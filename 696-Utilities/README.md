# 🤖 Triple-Play AI Pipeline — Code Backup

**Location:** `6-Operations/AI_Pipeline/` on Blacktech Drive  
**Date:** June 6, 2026  
**Status:** Active / In Production

---

## 📁 FILES IN THIS FOLDER

| File | What it does | When to use |
|------|-----------|-------------|
| `gemini_coordinator_*.py` | **Standalone Gemini wrapper** — calls Google Gemini 2.0 Flash-Lite for fast routing/formatting | When you need just the middle layer (parsing, cleaning, JSON formatting) |
| `triple_play_pipeline_*.py` | **Full auto-pipeline** — chains Claude → Gemini → Ollama in one command | When you want all 3 models to run automatically with one task |
| `pipeline_env_*.sh` | **Environment config** — sets API keys, hosts, model names | Source this before running any pipeline script |
| `toll_meter_*.txt` | **Cost tracker** — running tally of every Claude/Gemini session | Check this to see your AI spend |

---

## 🧠 THE TRIPLE-PLAY ARCHITECTURE

```
YOU (task)
    ↓
🔵 CLAUDE OPUS     = Strategy + planning      (~$0.01–$0.50)
    ↓
🟢 GEMINI FLASH    = Parse + clean + route     (~$0.00001–$0.0001)
    ↓
⚪ OLLAMA/PHI3     = Write final output        ($0.00 — FREE)
    ↓
DONE ✅
```

**Gemini's job:** Strict formatting only. No creative writing. Converts Claude's strategy into clean JSON or structured text that Ollama can execute.

**Gemini system prompt (hardcoded):**
```
ROLE: You are a strict data formatting utility.
DUTY: Convert the input strategy text into the exact JSON schema requested.
BOUNDARIES:
- Do NOT add conversational text, pleasantries, or explanations.
- Do NOT attempt to write the final proposal text.
- Do NOT expand on the strategy provided.
- Output ONLY the raw JSON object starting with { and ending with }.
```

---

## ⚡ QUICK START

### 1. Install Google SDK
```bash
pip install google-genai
```

### 2. Set API keys (one-time)
```bash
export ANTHROPIC_API_KEY="***"
export GEMINI_API_KEY="***"
```

### 3. Source environment
```bash
source /media/allenai/Expansion/Blacktech_Drive/6-Operations/AI_Pipeline/pipeline_env_*.sh
```

### 4. Run pipeline
```bash
python3 /media/allenai/Expansion/Blacktech_Drive/6-Operations/AI_Pipeline/triple_play_pipeline_*.py "Your task here"
```

---

## 📊 PRICING (June 2026)

| Model | Input | Output | Per 1K tokens |
|-------|-------|--------|---------------|
| Claude Opus | $15.00/M | $75.00/M | ~$0.045 |
| Gemini 2.0 Flash-Lite | $0.075/M | $0.30/M | ~$0.00018 |
| Ollama/Phi3 (local) | $0.00 | $0.00 | FREE |

**Example:** 1,000 token task
- Claude only: ~$0.045
- Gemini only: ~$0.00018
- Triple-Play (all 3): ~$0.04518 (Claude + Gemini, Ollama free)

---

## 🌐 MONITOR DASHBOARD

Live metrics pushed automatically to:  
`https://blue.blacktechsolutionscorp.com/monitor`

Shows: tokens in/out, cost per run, session history, real-time activity log.

---

## 🔧 MAINTENANCE NOTES

- **Gemini API key:** Get at `makersuite.google.com/app/apikey`
- **Ollama host:** `http://localhost:11434` (your Pi)
- **Telemetry endpoint:** `http://localhost:8094/api/telemetry` (BFN server)
- **Toll meter:** `/home/allenai/data/ai_toll_meter.txt`

**Backup this folder before any major changes.**

---

**Built by:** Claude + Blacktech Solutions Corp  
**System:** Raspberry Pi 5 + External SSD  
**Status:** Production Ready
