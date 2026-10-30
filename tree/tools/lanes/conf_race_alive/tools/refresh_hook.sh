#!/usr/bin/env bash
# Refresh hook for data/tb/ccg-alive.json (conf_race_alive lane). Called from the refresh routine (build.py, via the lane patch) right after data/ccg-sim.json and data/ccg-rules.json are
# written into the build output, and BEFORE pages are stamped and zipped. build_tb.py's lane step (build_lane.py) re-checks the same file, so a stale card can never reach a toolbox build.
#   usage: refresh_hook.sh <tree root: the folder that holds assets/ and data/>  [--quick-tests]
# Exit 0 = card written, rebuilt byte-for-byte equal, asof equal to ccg-sim, no unknown status.  3 = FREEZE file present.  4/5/6/7 = alive_gate.js refusals.  Any non-zero = do not deploy.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"; ROOT="${1:?tree root}"; ROOT="$(cd "$ROOT" && pwd)"
if [ -f "$ROOT/../FREEZE" ]; then echo "FREEZE file present ($ROOT/../FREEZE): refusing"; exit 3; fi
node "$HERE/build_alive.js" --root "$ROOT"                          # about 4 s; writes <root>/data/tb/ccg-alive.json and the proof file NEXT TO the tree (not shipped)
node "$HERE/build_alive.js" --root "$ROOT" --check                  # a second, in-memory rebuild must equal both files byte for byte
node "$HERE/alive_gate.js" --root "$ROOT"                           # asof equality (exit 4), unknown-status refusal (exit 5), banned words (exit 7)
if [ "${2:-}" = "--quick-tests" ]; then node "$HERE/../tests/alive_test.js" --quick --root "$ROOT"; fi
exit 0
