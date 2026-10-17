RETIRED CODE -- Gemini/Claude lane cleanup
Retired: 20261016_213014   By: Hermes agent, on Derrell's instruction

INSTRUCTION
  "We only have Ollama for the deploy tile" + "And claude"
  -> the deploy-tile pipeline (scripts/triple_play_pipeline.py) is now OLLAMA-ONLY.
     These two files were the last code paths that consumed a Gemini API key.

FILES
  gemini_coordinator.py  3967B  md5 c0467e72064f5e3ebe35dad574e23a75  (from /home/allenai/scripts/gemini_coordinator.py)
  gate_keeper.py  10125B  md5 23e725594001ed23372f79ebd91e5d96  (from /home/allenai/scripts/gate_keeper.py)

EVIDENCE AT RETIREMENT (nothing was using them)
  - crontab: no entry          - systemd --user units: none
  - hermes cron store: only a 2026-09-22 OUTPUT artifact, no job
  - importers in live *.py/*.sh/*.service under /home/allenai: none
  - running processes: none
  - bt-llm-guard.service uses llm_fail_fast_guard.py, NOT these

KEY HANDLING
  scripts/.env line `export GEMINI_API_KEY` -> COMMENTED OUT (it was a 3-char stub,
  not a live key). The plaintext /home/allenai/.env -- the one scripts/vault_loader.py
  actually prefers -- never contained GEMINI.

RESTORE
  cp {ARC}/gemini_coordinator.py /home/allenai/scripts/
  cp {ARC}/gate_keeper.py        /home/allenai/scripts/
  (and un-comment the GEMINI line in scripts/.env if you ever re-add a lane)
