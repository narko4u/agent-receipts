#!/usr/bin/env bash
# Produce today's receipt, commit it, push it, then emit the draft post.
# Nothing here posts anywhere. stdout is what the cron delivery shows the owner.
set -uo pipefail
cd /home/vault/work/agent-receipts
mkdir -p logs
day=$(date +%F)

python3 tools/daily.py >> logs/daily.log 2>&1
daily_rc=$?
python3 tools/verify.py --gh >> logs/daily.log 2>&1 || true

if [ -n "$(git status --porcelain)" ]; then
  git add -A
  git commit -qm "receipt: $day" >> logs/daily.log 2>&1
  git push -q origin main >> logs/daily.log 2>&1
fi

if [ ! -f "queue/$day.txt" ]; then
  echo "agent-receipts: no receipt for $day (daily.py exit $daily_rc), see logs/daily.log"
  exit 1
fi

cat "queue/$day.txt"
