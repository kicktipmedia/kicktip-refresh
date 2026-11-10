#!/bin/bash
# Post-deploy byte-compare of the custom domains.
# A Cloudflare edge can keep serving the previous deploy for a couple of minutes; that is not a bad deploy.
# Tries are spread over about 2-3 minutes (each one is a cache-busted, no-cache GET via bytecmp.py).
# If the domains still mismatch but the deployment's own pages.dev URL matches the built tree, print
# "edge-lag" and exit 0 so the caller records the new live base. Write FREEZE and exit 22 only when
# that pages.dev URL mismatches.
# usage: live_verify.sh <deploy_dir> <log> <pages_url> <freeze_file> <new_id> <run> <old_live_id>
# env: KT_BYTECMP (optional executable, default tools/bytecmp.py), KT_LIVE_MARKS (comma seconds from start;
#      default 20,70,120,170), KT_LIVE_HOSTS (default apex and www)
set -uo pipefail
[ $# -eq 7 ] || { echo "usage: live_verify.sh <deploy_dir> <log> <pages_url> <freeze_file> <new_id> <run> <old_live_id>" >&2; exit 2; }
DEPLOY=$1; LOG=$2; PAGES=$3; FREEZE=$4; NEW_ID=$5; RUN=$6; OLD=$7
HERE=$(cd "$(dirname "$0")" && pwd)
MARKS=${KT_LIVE_MARKS:-20,70,120,170}
HOSTS=${KT_LIVE_HOSTS:-https://kicktipmedia.com https://www.kicktipmedia.com}
cmp_host() {
  if [ -n "${KT_BYTECMP:-}" ]; then "$KT_BYTECMP" "$DEPLOY" "$1" >> "$LOG"
  else python3 "$HERE/bytecmp.py" "$DEPLOY" "$1" >> "$LOG"; fi
}
IFS=',' read -r -a marks <<< "$MARKS"
[ ${#marks[@]} -ge 1 ] || { echo "KT_LIVE_MARKS empty" >&2; exit 2; }
start=$(date +%s); n=0
for mark in "${marks[@]}"; do
  n=$((n+1))
  now=$(date +%s); wait=$((mark - (now - start)))
  [ "$wait" -gt 0 ] && sleep "$wait"
  ok=1
  for H in $HOSTS; do
    cmp_host "$H" || { ok=0; break; }
  done
  if [ $ok = 1 ]; then echo ok; exit 0; fi
  echo "[live_verify] mismatch try $n/${#marks[@]}" >&2
done
echo "[live_verify] apex/www still mismatch; checking $PAGES" >&2
if cmp_host "$PAGES"; then echo edge-lag; exit 0; fi
echo "byte-compare failed after deploy $NEW_ID run $RUN; rollback to $OLD" > "$FREEZE"
exit 22
