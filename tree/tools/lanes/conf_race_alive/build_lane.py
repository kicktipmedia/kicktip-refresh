#!/usr/bin/env python3
"""conf_race_alive lane build step. build_tb.py runs it AFTER the overlay copy and BEFORE manifest generation and restamping:   build_lane.py --tree <built tree>
It edits no existing site file. What it does, in order:
  1. FREEZE: if <tree>/../FREEZE exists, refuse (exit 3), same rule as the refresh hook.
  2. build.py patch: dry-runs patch_sim_build.py against kicktip-sim6 src/build.py (env KT_SIM_BUILD_PY, default /workspace/kicktip-sim6/src/build.py; skipped with a note if the file is absent),
     so a changed build.py fails THIS build loudly (exact-match, count 1). It APPLIES the patch only when KT_SIM_BUILD_PY is set explicitly.
  3. data/tb/ccg-alive.json: if the tree already holds it (the refresh hook wrote it into the build output), it must equal a fresh rebuild byte for byte or the build fails (stale);
     if it is absent, it is generated from the tree's own data/ccg-sim.json, data/ccg-rules.json, assets/ccgsim.js. Either way the card always matches the tree's ccg-sim.
  4. alive_gate.js: asof equals ccg-sim asof (exit 4), no unknown team status (exit 5), no banned words (exit 7).
Wording stays neutral ("in the race / out of the race on our reading of the rules") for every conference unless <tree>/data/ccg-rules-verified.json carries {conf:{verified:true, rules_hash:<hash of that conference's rules>}}."""
import argparse, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__)); TOOLS = os.path.join(HERE, 'tools')
sys.path.insert(0, HERE)
ap = argparse.ArgumentParser(); ap.add_argument('--tree', required=True); a = ap.parse_args()
tree = os.path.abspath(a.tree)
if os.path.exists(os.path.join(tree, '..', 'FREEZE')):
    print('build_lane[conf_race_alive]: FREEZE file present, refusing'); sys.exit(3)
import patch_sim_build as P
env_file = os.environ.get('KT_SIM_BUILD_PY'); src = env_file or '/workspace/kicktip-sim6/src/build.py'
if os.path.exists(src):
    try: print('build_lane[conf_race_alive]: build.py patch', P.patch(src, apply=bool(env_file)), src)
    except AssertionError as e: print('build_lane[conf_race_alive]: build.py ANCHOR MISMATCH, the patch no longer matches exactly once:', e); sys.exit(1)
else: print('build_lane[conf_race_alive]: build.py not found, patch check skipped (%s)' % src)
def node(*args):
    r = subprocess.run(['node'] + list(args), capture_output=True, text=True); sys.stdout.write(r.stdout); sys.stderr.write(r.stderr); return r.returncode
card = os.path.join(tree, 'data', 'tb', 'ccg-alive.json')
if os.path.exists(card):
    rc = node(os.path.join(TOOLS, 'build_alive.js'), '--root', tree, '--check', '--card-only')
    if rc: print('build_lane[conf_race_alive]: data/tb/ccg-alive.json in the tree is stale or differs from a rebuild'); sys.exit(rc)
else:
    rc = node(os.path.join(TOOLS, 'build_alive.js'), '--root', tree, '--quiet')
    if rc: sys.exit(rc)
sys.exit(node(os.path.join(TOOLS, 'alive_gate.js'), '--root', tree))
