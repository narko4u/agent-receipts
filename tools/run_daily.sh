#!/usr/bin/env bash
# Produce today's receipt, commit it, push it. Nothing here posts anywhere.
set -euo pipefail
cd /home/vault/work/agent-receipts
mkdir -p logs
python3 tools/daily.py >> logs/daily.log 2>&1
python3 tools/verify.py --gh >> logs/daily.log 2>&1
git add -A
if git diff --cached --quiet; then
  echo "no new receipt" >> logs/daily.log
  exit 0
fi
git commit -qm "receipt: $(date +%F)" >> logs/daily.log 2>&1
git push -q origin main >> logs/daily.log 2>&1
echo "pushed $(date -Is)" >> logs/daily.log
