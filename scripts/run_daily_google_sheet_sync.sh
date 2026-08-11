#!/bin/zsh
set -euo pipefail

cd "/Users/admin/Documents/Obsidian Vault/TCL-Signs/order-agent"
/usr/bin/python3 scripts/daily_google_sheet_sync.py >> data/cache/daily-google-sheet-sync.log 2>&1
