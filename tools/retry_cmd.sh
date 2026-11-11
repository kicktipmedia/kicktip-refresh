#!/bin/bash
# Retry a command. Sleep before a retry is backoff * the attempt that just failed
# (backoff seconds after the first failure, 2*backoff after the second, ...).
# usage: retry_cmd.sh --tries N --backoff SEC --log FILE -- command args...
set -uo pipefail
TRIES=3
BACKOFF=20
LOG=""
while [ $# -gt 0 ]; do
  case "$1" in
    --tries) TRIES=$2; shift 2;;
    --backoff) BACKOFF=$2; shift 2;;
    --log) LOG=$2; shift 2;;
    --) shift; break;;
    *) echo "unknown arg $1" >&2; exit 2;;
  esac
done
[ $# -ge 1 ] || { echo "no command" >&2; exit 2; }
case "$TRIES" in
  ''|*[!0-9]*) echo "tries must be an integer" >&2; exit 2;;
esac
case "$BACKOFF" in
  ''|*[!0-9]*) echo "backoff must be an integer" >&2; exit 2;;
esac
[ "$TRIES" -ge 1 ] || { echo "tries must be >= 1" >&2; exit 2; }
[ -n "$LOG" ] || { echo "--log is required" >&2; exit 2; }
mkdir -p "$(dirname "$LOG")"
: > "$LOG"
attempt=1
rc=1
while [ "$attempt" -le "$TRIES" ]; do
  tmp=$(mktemp)
  set +e
  "$@" >"$tmp" 2>&1
  rc=$?
  set -e
  {
    echo "attempt $attempt/$TRIES rc=$rc"
    cat "$tmp"
  } >> "$LOG"
  rm -f "$tmp"
  if [ "$rc" -eq 0 ]; then
    echo "attempt $attempt/$TRIES ok" >> "$LOG"
    exit 0
  fi
  if [ "$attempt" -lt "$TRIES" ]; then
    sleep_s=$(( BACKOFF * attempt ))
    echo "sleeping ${sleep_s}s before retry" >> "$LOG"
    if [ "$sleep_s" -gt 0 ]; then sleep "$sleep_s"; fi
  fi
  attempt=$(( attempt + 1 ))
done
echo "failed after $TRIES tries rc=$rc" >> "$LOG"
exit "$rc"
