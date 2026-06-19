"""
hecos.modules.backup
────────────────────
Global Backup Orchestrator for Hecos.

Exposes:
  orchestrator  — per-module backup/restore functions
  scheduler     — APScheduler wrapper for automatic backups
  store         — persistent configuration (YAML)
  api           — Flask routes at /hecos/api/backup/...
"""
