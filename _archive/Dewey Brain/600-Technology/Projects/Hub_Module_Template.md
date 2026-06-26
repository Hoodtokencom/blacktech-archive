# Neighborhood Blockchain Hub — Build-Along Module Template

**Version:** 1.0  
**Purpose:** Replicable template for any Hub member to host a live build session.  
**Prerequisites:** Host must have successfully built the system at least once before teaching it.

---

## 1. Module Header

| Field | Value |
|---|---|
| **Module Number** | `XXX` |
| **Module Title** | `[Short, clear name]` |
| **System Built** | `[What you have at the end]` |
| **Host** | `[Name]` |
| **Estimated Duration** | `60-90 minutes` |
| **Cost to Replicate** | `$0 / $XX` |
| **Skill Level** | `Beginner / Intermediate / Advanced` |
| **Prerequisites for Attendees** | `[What they need before the call]` |

---

## 2. Pre-Session Checklist (Host)

- [ ] System is currently running and stable in your own environment
- [ ] Test environment exists (fresh Pi, VM, or separate laptop) for live demo
- [ ] All passwords, API keys, and secrets are stored in a vault — none visible on screen
- [ ] Screen recording software ready (OBS, built-in recorder, or Telegram video)
- [ ] Backup plan if live build fails: pre-recorded successful run as fallback
- [ ] Attendee signup list collected (Telegram group or Signal)

---

## 3. Session Structure (60-90 Minutes)

### Part A — What & Why (10 min)
- What problem this system solves
- What centralized/SaaS alternative it replaces
- Why self-hosted is better (privacy, cost, control)

### Part B — The Build (40-60 min)
- Host screen-shares step-by-step
- Attendees follow on their own device
- Every config file, command, and URL is copy-paste ready
- One attendee volunteer shares their screen if they get stuck

### Part C — Verify It Works (10 min)
- Host demonstrates the system running
- Attendees confirm theirs is working
- Common errors and fixes (prepared list)

### Part D — Q&A + Homework (5-10 min)
- Open floor for questions
- Homework: run it solo before next session
- Next module preview

---

## 4. Handout Package (Distributed After Session)

Attendees receive a zip or folder containing:

```
module_XXX/
├── README.md           ← This module guide (written version)
├── scripts/
│   ├── install.sh      ← One-command installer (if possible)
│   ├── config.env.example  ← Template with fake credentials
│   └── verify.py       ← Script that confirms it works
├── screenshots/
│   ├── 01_open_terminal.png
│   ├── 02_expected_output.png
│   └── 03_final_result.png
└── video_recording.mp4 ← Full session recording (if host agrees)
```

---

## 5. Verification Script Template

Every module includes a `verify.py` script. Attendees run it to confirm success.

```python
#!/usr/bin/env python3
"""Module XXX Verification Script"""
import sys

def check_prerequisites():
    print("Checking prerequisites...")
    # e.g., python3 version, disk space, internet
    return True

def check_installation():
    print("Checking system installation...")
    # e.g., service running, port open, file exists
    return True

def check_functionality():
    print("Checking system works...")
    # e.g., API responds, email sends, page loads
    return True

if __name__ == "__main__":
    ok = all([check_prerequisites(), check_installation(), check_functionality()])
    sys.exit(0 if ok else 1)
```

---

## 6. Troubleshooting Quick Reference

| Symptom | Most Likely Cause | Fix |
|---|---|---|
| `[Symptom 1]` | `[Cause]` | `[One-line fix]` |
| `[Symptom 2]` | `[Cause]` | `[One-line fix]` |
| `[Symptom 3]` | `[Cause]` | `[One-line fix]` |

---

## 7. Decentralization Connection

Explain how this module connects to the bigger picture:

- **Before:** What SaaS/centralized tool did you depend on?
- **After:** What do you control now?
- **Next:** What module plugs into this one?

---

*End of template. Every Hub module must follow this structure for consistency.*
