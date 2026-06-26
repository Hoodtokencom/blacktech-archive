# Decision Log

## 2026-06-16 — Disabled legacy watchdog + CICD cron

- **Context:** Legacy cron manually restarted Python scripts every 5 minutes, conflicting with new systemd units.
- **Decision:** Disabled `blacktech_watchdog.py` and `cicd_deploy.py` cron entries.
- **Replaced by:** systemd `Restart=always` + 15-minute `health_reporter.py`.

## 2026-06-16 — Created Blacktech Brain

- **Context:** Passwords and operational instructions scattered across backups and external drive.
- **Decision:** Centralize in `/home/allenai/blacktech_brain/`, sync to Google Drive.
- **Next step:** Build encrypted passcode lookup tool.
