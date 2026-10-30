#!/usr/bin/env python3
"""The ONE edit conf_race_alive makes to an existing source file: a single line inserted into kicktip-sim6 src/build.py, right after the line that writes data/ccg-rules.json
(ccg-sim.json and ccg-rules.json are both on disk in SITE by then; assets/ccgsim.js was copied at the top of the write block).
Exact-match and count-asserted through core/tools/patchlib.replace_exact: the anchor line must occur exactly once or the patch fails loudly. Idempotent via the marker.
The inserted line is OPT-IN: it does nothing unless the environment variable KT_ALIVE_HOOK holds the path of lanes/conf_race_alive/tools/refresh_hook.sh, so an unpatched or unset run is byte-identical in behaviour.
  patch_sim_build.py --file <build.py> --dry-run    check that the anchor matches exactly once (nothing is written)   [exit 0 ok, 1 anchor problem]
  patch_sim_build.py --file <build.py> --apply      write the line (refuses if already applied)
Never run by a test against the real file; build_lane.py only dry-runs it, and applies it only when KT_SIM_BUILD_PY names the file explicitly."""
import argparse, os, shutil, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', 'core', 'tools'))
from patchlib import replace_exact   # noqa: E402

MARK = '# tb-lane:conf_race_alive'
ANCHOR = '    w("data/ccg-rules.json", json.dumps(dict(codes=sorted(_cr), rules=_cr), separators=(",", ":"), ensure_ascii=False))\n'
HOOK = '    if os.environ.get("KT_ALIVE_HOOK"): __import__("subprocess").run(["bash", os.environ["KT_ALIVE_HOOK"], SITE], check=True)   ' + MARK + '\n'

def patch(path, apply):
    """returns 'applied' | 'would-apply' | 'already-applied'. Raises AssertionError (count) or SystemExit on a changed base."""
    path = os.path.abspath(path); d, f = os.path.dirname(path), os.path.basename(path)
    if MARK in open(path, encoding='utf-8').read(): return 'already-applied'
    if apply:
        replace_exact(d, f, ANCHOR, ANCHOR + HOOK, count=1, marker=MARK); return 'applied'
    t = tempfile.mkdtemp(prefix='tbpatch_')
    try:
        shutil.copy2(path, os.path.join(t, f)); replace_exact(t, f, ANCHOR, ANCHOR + HOOK, count=1, marker=MARK); return 'would-apply'
    finally: shutil.rmtree(t, ignore_errors=True)

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--file', required=True)
    g = ap.add_mutually_exclusive_group(required=True); g.add_argument('--apply', action='store_true'); g.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()
    try: print('patch_sim_build:', patch(a.file, a.apply), a.file)
    except AssertionError as e: print('patch_sim_build: ANCHOR MISMATCH:', e); sys.exit(1)
