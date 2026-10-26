#!/usr/bin/env bash
# Produce today's receipt, commit it, push it, publish it behind a gate.
# stdout is what the cron delivery shows the owner: the draft, and what happened.
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

if [ -f "queue/$day.posted" ]; then
  status="already posted id=$(cat "queue/$day.posted")"
else
  python3 tools/post.py "queue/$day.txt" >> logs/post.log 2>&1
  rc=$?
  case $rc in
    0) id=$(grep -o 'id=[0-9]*' logs/post.log | tail -1 | cut -d= -f2)
       echo "$id" > "queue/$day.posted"
       status="posted id=$id" ;;
    2) status="gate refused, see logs/post.log" ;;
    3) status="not posted: X credits depleted" ;;
    *) status="not posted: error rc=$rc, see logs/post.log" ;;
  esac
fi

printf '%s\n\n%s\n' "$(cat "queue/$day.txt")" "status: $status"
