# 322 — Legislative Branch (GLM-5.1)

**Dewey Class:** 322 — Legislative  
**Authority:** SOP generation, policy drafting, code proposals  
**Model:** GLM-5.1 via Ollama Cloud  
**Cron:** `002 — Legislative Branch (Qwen SOW Generator)` → daily 2:00 AM

---

## Responsibilities

- Generate SOPs and operational procedures
- Draft policies for Executive review
- SOW (Statement of Work) generation for projects
- Code proposals and architectural suggestions
- Cannot override Executive decisions

## Cron Job

- **ID:** 2f11a477350d
- **Schedule:** `0 2 * * *` (daily 2:00 AM)
- **Script:** `/home/allenai/scripts/qwen_sow_generator.py`
- **Model:** glm-5.1 (Ollama Cloud)
- **Deliver:** local (silent)

## Output

- Generated SOPs saved to this folder
- SOW documents saved to `692-Auxiliary_Practices/`