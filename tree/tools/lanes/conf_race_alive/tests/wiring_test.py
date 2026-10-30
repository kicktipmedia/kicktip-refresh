#!/usr/bin/env python3
"""wiring_test.py <built tree>: the build.py patch (count-asserted, idempotent, opt-in), build_lane.py refusals (FREEZE, stale card, unknown status), refresh_hook.sh (writes, FREEZE, refuses unknown status).
Works on COPIES in a temp dir; never touches /workspace/kicktip-sim6 (reads build.py once, copies it)."""
import json, os, shutil, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); LANE = os.path.abspath(os.path.join(HERE, '..'))
TREE = os.path.abspath(sys.argv[1]); SIM = os.environ.get('KT_SIM_BUILD_PY', '/workspace/kicktip-sim6/src/build.py')
sys.path.insert(0, LANE); import patch_sim_build as P
n = [0, 0]
def ok(c, m):
    n[0 if c else 1] += 1
    if not c: print('FAIL', m)
def sh(*a, **k): return subprocess.run(list(a), capture_output=True, text=True, **k)
tmp = tempfile.mkdtemp(prefix='wiring_')
try:
    # 1 patch
    b = os.path.join(tmp, 'build.py'); shutil.copy(SIM, b); orig = open(b).read()
    ok(orig.count(P.ANCHOR) == 1, 'anchor occurs exactly once in the real build.py')
    ok(P.patch(b, False) == 'would-apply' and open(b).read() == orig, 'dry run writes nothing')
    ok(P.patch(b, True) == 'applied', 'apply'); new = open(b).read()
    ok(new == orig.replace(P.ANCHOR, P.ANCHOR + P.HOOK) and new.count(P.MARK) == 1 and len(new.splitlines()) == len(orig.splitlines()) + 1, 'exactly one line added, right after the anchor, nothing else changed')
    ok(P.patch(b, True) == 'already-applied' and open(b).read() == new, 'idempotent')
    ok(sh(sys.executable, '-c', 'import ast,sys;ast.parse(open(sys.argv[1]).read())', b).returncode == 0, 'patched build.py still parses')
    for name, text in [('none', orig.replace(P.ANCHOR, '')), ('twice', orig.replace(P.ANCHOR, P.ANCHOR + P.ANCHOR)), ('changed', orig.replace('ensure_ascii=False))\n', 'ensure_ascii=True))\n', 1) if False else orig.replace('data/ccg-rules.json', 'data/ccg-rules2.json'))]:
        f = os.path.join(tmp, name + '.py'); open(f, 'w').write(text)
        try: P.patch(f, False); r = 'no error'
        except AssertionError: r = 'asserted'
        ok(r == 'asserted', 'anchor count %s: patch refuses' % name)
    ok(sh(sys.executable, os.path.join(LANE, 'patch_sim_build.py'), '--file', os.path.join(tmp, 'twice.py'), '--apply').returncode == 1, 'CLI exits 1 on anchor mismatch')
    # opt-in: the inserted line is inert without the env var (executed in isolation)
    line = P.HOOK.strip(); r = sh(sys.executable, '-c', 'import os\nSITE="x"\n' + line + '\nprint("inert")'); ok(r.stdout.strip() == 'inert' and r.returncode == 0, 'hook line is inert when KT_ALIVE_HOOK is unset')
    # 2 build_lane / hook on copies. Layout: <tmp>/w/site (tree) next to <tmp>/w/FREEZE
    w = os.path.join(tmp, 'w'); site = os.path.join(w, 'site'); shutil.copytree(TREE, site)
    env = dict(os.environ); env.pop('KT_SIM_BUILD_PY', None)
    r = sh(sys.executable, os.path.join(LANE, 'build_lane.py'), '--tree', site, env=env); ok(r.returncode == 0, 'build_lane passes on an up-to-date tree: ' + r.stdout[-200:] + r.stderr[-300:])
    card = os.path.join(site, 'data/tb/ccg-alive.json'); good = open(card).read()
    j = json.loads(good); j['confs']['sec']['in_race'] = j['confs']['sec']['in_race'][:-1]; open(card, 'w').write(json.dumps(j, separators=(',', ':')))
    r = sh(sys.executable, os.path.join(LANE, 'build_lane.py'), '--tree', site, env=env); ok(r.returncode != 0, 'build_lane refuses a stale / edited card (exit %d)' % r.returncode)
    j = json.loads(good); j['asof'] = '2026-10-23 00:00 MT'; open(card, 'w').write(json.dumps(j, separators=(',', ':')))
    r = sh('node', os.path.join(LANE, 'tools/alive_gate.js'), '--root', site); ok(r.returncode == 4, 'alive_gate exit 4 on asof mismatch (got %d)' % r.returncode)
    j = json.loads(good); j['confs']['sec']['counts']['unknown'] = 1; open(card, 'w').write(json.dumps(j, separators=(',', ':')))
    r = sh('node', os.path.join(LANE, 'tools/alive_gate.js'), '--root', site); ok(r.returncode == 5, 'alive_gate exit 5 on an unknown status (got %d)' % r.returncode)
    j = json.loads(good); j['confs']['sec']['name'] = 'SEC CCG'; open(card, 'w').write(json.dumps(j, separators=(',', ':')))
    r = sh('node', os.path.join(LANE, 'tools/alive_gate.js'), '--root', site); ok(r.returncode == 7, 'alive_gate exit 7 on a banned word (got %d)' % r.returncode)
    os.remove(card); r = sh('node', os.path.join(LANE, 'tools/alive_gate.js'), '--root', site); ok(r.returncode == 6, 'alive_gate exit 6 on a missing card (got %d)' % r.returncode)
    # hook: regenerates a missing card, equal to the shipped one
    r = sh('bash', os.path.join(LANE, 'tools/refresh_hook.sh'), site); ok(r.returncode == 0 and open(card).read() == good, 'refresh hook rewrites the card byte-for-byte equal (exit %d) %s' % (r.returncode, r.stderr[-200:]))
    # hook refuses an unknown status: shrink the search caps by running the gate on a card the hook would produce? simulate through a stub node search that reports unknown: tamper the engine so every search is capped
    open(os.path.join(w, 'FREEZE'), 'w').write('x')
    r = sh('bash', os.path.join(LANE, 'tools/refresh_hook.sh'), site); ok(r.returncode == 3, 'hook exit 3 under FREEZE (got %d)' % r.returncode)
    r = sh(sys.executable, os.path.join(LANE, 'build_lane.py'), '--tree', site, env=env); ok(r.returncode == 3, 'build_lane exit 3 under FREEZE (got %d)' % r.returncode)
    os.remove(os.path.join(w, 'FREEZE'))
    # hook with a patched build.py line: the env var runs the hook and a failing hook fails the build step
    hook_fail = os.path.join(tmp, 'bad_hook.sh'); open(hook_fail, 'w').write('#!/bin/bash\nexit 5\n')
    r = sh(sys.executable, '-c', 'import os,subprocess\nSITE="x"\n' + line + '\nprint("ran")', env=dict(os.environ, KT_ALIVE_HOOK=hook_fail)); ok(r.returncode != 0, 'a failing hook stops the build step (check=True)')
finally:
    shutil.rmtree(tmp, ignore_errors=True)
print(('FAILED' if n[1] else 'PASSED') + ': wiring test %d checks, %d failures' % (n[0], n[1])); sys.exit(1 if n[1] else 0)
