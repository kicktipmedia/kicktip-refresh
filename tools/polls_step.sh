#!/bin/bash
# AP / Coaches poll gate. Never fails the refresh: exit 0, last good file kept on any error.
# GitHub outputs: polls_changed=0|1, and polls_out / polls_baseline only when a file was written.
# Hooks (off unless a manual non-production dispatch sets them): KT_POLLS_URL, KT_POLLS_BASELINE=week10, KT_POLLS_FAIL.
set -u
R=${KT_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}
ZIP=${KT_POLLS_ZIP:-$R/base/kicktip-site.zip}
D=$R/polls/cur
OUT=$D/polls.json
BASE=$D/baseline.json
LOG=$D/step.log
GO=${GITHUB_OUTPUT:-/dev/null}
SUM=${GITHUB_STEP_SUMMARY:-/dev/null}
mkdir -p "$D"
rm -f "$OUT" "$BASE"
timeout 80 python3 "$R/tree/src/poll_refresh.py" --zip "$ZIP" --out "$OUT" --baseline-out "$BASE" --cfp > "$LOG" 2>&1 || echo "WARNING polls: step crashed; keeping the last good polls file" >> "$LOG"
cat "$LOG"
CH=0
grep -q '^POLLS_CHANGED=1$' "$LOG" && CH=1
{
  echo "polls_changed=$CH"
  if [ "$CH" = 1 ] && [ -f "$OUT" ]; then echo "polls_out=$OUT"; fi
  if [ -f "$BASE" ] && grep -q '^POLLS_BASELINE=' "$LOG"; then echo "polls_baseline=$BASE"; fi
} >> "$GO"
{
  echo "### Polls"
  echo "- changed vs the comparison baseline: $CH"
  grep -E '^(polls:|WARNING polls:)' "$LOG" | head -n 20
} >> "$SUM"
exit 0
