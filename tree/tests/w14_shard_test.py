"""w14 shard: a new what-if week file (first remaining game in that week) must be
copied into the merged tree, the index must not list a shard that was not written,
and build_tile_data must skip a legitimately empty week but fail closed when a
week with games is missing its file.

Repro: run 44964427509, 2026-11-21, apply_data exit 16. Jacksonville State at
Liberty entered remaining games as the first week-14 matchup; S1 wrote
data/whatif/w14.json and listed it in index.shards; live did not have the file;
merge3 skipped it as missing_live; tile-data raised FileNotFoundError.

usage: python3 tests/w14_shard_test.py
Set KT_W14_LIVE_DATA to a tree of today's live data/ files (whatif/index.json and
shards, sim-bundle.json, pred-teams.json) to also exercise the merge against
today's published index.
"""
import json, os, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TREE = os.path.dirname(HERE)
REPO = os.path.dirname(TREE)
TOOLS = os.path.join(TREE, 'tools')
fails = []

n_checks = [0]
def ok(cond, msg):
    n_checks[0] += 1
    if not cond:
        fails.append(msg)

def write_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(obj, f, separators=(',', ':'))

def load(path):
    return json.load(open(path, encoding='utf-8'))

def run_merge3(live, s0, s1, out, rep):
    r = subprocess.run([sys.executable, os.path.join(TOOLS, 'merge3.py'), live, s0, s1, out, rep],
                       capture_output=True, text=True)
    return r

def run_old_merge3(live, s0, s1, out, rep):
    """The merge3 at 6902202d: skip every changed file that is not already on live."""
    src = open(os.path.join(TOOLS, 'merge3.py'), encoding='utf-8').read()
    # Prefer the exact merge3 from the failing main sha; fall back to reversing this PR's block.
    try:
        old = subprocess.check_output(
            ['git', 'show', '6902202d189b2a997623ed27679a0a50fd19d381:tree/tools/merge3.py'],
            cwd=REPO, text=True)
    except subprocess.CalledProcessError:
        old = src.replace(
            "WHATIF_SHARD=re.compile(r'^data/(m/(elo|eff)/)?whatif/w\\d+\\.json$')\n"
            "for f in changed:\n"
            "    lp=L+'/'+f\n"
            "    if not os.path.exists(lp):\n"
            "        b=rd(S1+'/'+f)\n",
            "for f in changed:\n"
            "    lp=L+'/'+f\n"
            "    if not os.path.exists(lp): rep['missing_live'].append(f); continue\n"
            "    # fallback-old: dropped the new-shard copy and the rest of the if-not-exists block\n")
        # If the surgical replace missed, cut the new if-not-exists body back to the skip.
        if 'new in S1, not on live' in old:
            import re as _re
            old = _re.sub(
                r"if not os\.path\.exists\(lp\):\n(?:.*\n)*?        rep\['missing_live'\]\.append\(f\); continue\n",
                "if not os.path.exists(lp): rep['missing_live'].append(f); continue\n",
                old, count=1)
    td = tempfile.mkdtemp()
    path = os.path.join(td, 'merge3.py')
    open(path, 'w').write(old)
    r = subprocess.run([sys.executable, path, live, s0, s1, out, rep], capture_output=True, text=True)
    shutil.rmtree(td, ignore_errors=True)
    return r

ASOF = '2026-11-21 15:18 MT'
METRICS = ['ccg', 'title', 'cfp12', 'bye']

def mini_index(shards, games=None):
    return {
        'label': 'Single-game what-ifs from 6,000 simulated seasons (KickTip estimates, for information only). Values are per-mille.',
        'as_of': ASOF, 'seasons': 6000, 'seed': 2026, 'min_move_permille': 3,
        'metrics': METRICS, 'team_names': ['Alpha', 'Beta'],
        'baseline': [[100, 50, 20, 0], [80, 40, 10, 0]],
        'games': games or [{'id': 'g13', 'week': 13, 'h': 0, 'a': 1, 'neutral': False, 'p_home': 500}],
        'shards': shards, 'model': 'blend', 'model_label': 'KickTip blend',
    }

def mini_bundle():
    return {
        'as_of': ASOF,
        'teams': [
            {'n': 'Alpha', 's': 'Alpha', 'g': 'alpha'},
            {'n': 'Beta', 's': 'Beta', 'g': 'beta'},
        ],
        'games': [{'id': 'g13', 'date': '2026-11-28T20:00Z', 'ip': False}],
    }

def mini_pred():
    return {'teams': {
        'alpha': {'p': 0.02, 'c': 0.1},
        'beta': {'p': 0.01, 'c': 0.05},
    }}

def write_site(root, shards_index, shard_files, extra_bundle_games=None, extra_index_games=None):
    idx = mini_index(shards_index, games=None)
    if extra_index_games:
        idx['games'] = list(idx['games']) + extra_index_games
    write_json(os.path.join(root, 'data/whatif/index.json'), idx)
    for name, body in shard_files.items():
        write_json(os.path.join(root, 'data/whatif', name), body)
    bun = mini_bundle()
    if extra_bundle_games:
        bun['games'] = list(bun['games']) + extra_bundle_games
    write_json(os.path.join(root, 'data/sim-bundle.json'), bun)
    write_json(os.path.join(root, 'data/pred-teams.json'), mini_pred())

SH13 = {'g13': {'h': [[0, 200, 80, 40, 0]], 'a': [[0, 50, 10, 5, 0], [1, 90, 45, 12, 0]]}}
SH14 = {'401869535': {'h': [[0, 110, 55, 22, 0]], 'a': [[0, 90, 45, 18, 0]]}}

def setup_merge_sides(td):
    live, s0, s1, out = [os.path.join(td, n) for n in ('L', 'S0', 'S1', 'O')]
    # Live and S0: weeks 12/13/15, no w14 (today's published shape).
    files_live = {'w13.json': SH13, 'w12.json': {}, 'w15.json': {}}
    shards_live = {'12': 'w12.json', '13': 'w13.json', '15': 'w15.json'}
    write_site(live, shards_live, files_live)
    shutil.copytree(live, s0)
    # S1 adds the first week-14 remaining game and writes w14.json.
    extra_g = [{'id': '401869535', 'week': 14, 'h': 0, 'a': 1, 'neutral': False, 'p_home': 600}]
    extra_b = [{'id': '401869535', 'date': '2026-12-05T00:00Z', 'ip': False}]
    files_s1 = dict(files_live)
    files_s1['w14.json'] = SH14
    shards_s1 = dict(shards_live)
    shards_s1['14'] = 'w14.json'
    write_site(s1, shards_s1, files_s1, extra_bundle_games=extra_b, extra_index_games=extra_g)
    shutil.copytree(live, out)
    return live, s0, s1, out

# --- 1. Repro with the unfixed merge3: new w14 is not copied, index lists it ---
td = tempfile.mkdtemp(prefix='w14old_')
try:
    live, s0, s1, out = setup_merge_sides(td)
    r = run_old_merge3(live, s0, s1, out, os.path.join(td, 'rep.json'))
    ok(r.returncode == 0, 'old merge3 should still exit 0: %s %s' % (r.returncode, r.stderr[-400:]))
    rep = load(os.path.join(td, 'rep.json'))
    ok(not os.path.isfile(os.path.join(out, 'data/whatif/w14.json')), 'repro: old merge3 must not copy w14.json')
    ok(any('data/whatif/w14.json' in x for x in rep.get('missing_live') or []),
       'repro: old merge3 should record w14.json as missing_live, got %s' % rep.get('missing_live'))
    idx = load(os.path.join(out, 'data/whatif/index.json'))
    ok(idx.get('shards', {}).get('14') == 'w14.json', 'repro: merged index lists w14.json: %s' % idx.get('shards'))
    # Unfixed tile-data (one-line loader) would crash; current code fail-closes because week 14 has games.
    rtd = subprocess.run([sys.executable, os.path.join(TOOLS, 'build_tile_data.py'), out],
                         capture_output=True, text=True)
    # After the fix, this merged-out (file missing, games present) must fail closed, not FileNotFoundError.
    ok(rtd.returncode != 0, 'tile-data must fail closed when week 14 games exist and w14.json is missing')
    err = (rtd.stdout + rtd.stderr)
    ok('FileNotFoundError' not in err, 'tile-data must not raise FileNotFoundError: %s' % err[-400:])
    ok('whatif shard file missing' in err and 'w14.json' in err, 'tile-data fail-closed message: %s' % err[-400:])
finally:
    shutil.rmtree(td, ignore_errors=True)

# --- 2. Fixed merge3 copies the new shard ---
td = tempfile.mkdtemp(prefix='w14new_')
try:
    live, s0, s1, out = setup_merge_sides(td)
    r = run_merge3(live, s0, s1, out, os.path.join(td, 'rep.json'))
    ok(r.returncode == 0, 'fixed merge3 exit 0: %s %s' % (r.returncode, r.stderr[-400:]))
    rep = load(os.path.join(td, 'rep.json'))
    ok(os.path.isfile(os.path.join(out, 'data/whatif/w14.json')), 'fixed merge3 copies w14.json into out')
    ok(any('data/whatif/w14.json' in x and 'new in S1' in x for x in rep.get('taken') or []),
       'fixed merge3 records w14.json as taken, got %s' % rep.get('taken'))
    ok('data/whatif/w14.json' not in (rep.get('missing_live') or []),
       'fixed merge3 must not list w14.json as missing_live')
    idx = load(os.path.join(out, 'data/whatif/index.json'))
    ok(idx.get('shards', {}).get('14') == 'w14.json', 'fixed merge keeps w14 in the index')
    rtd = subprocess.run([sys.executable, os.path.join(TOOLS, 'build_tile_data.py'), out],
                         capture_output=True, text=True)
    ok(rtd.returncode == 0, 'tile-data succeeds when w14.json was copied: %s' % (rtd.stdout + rtd.stderr)[-400:])
finally:
    shutil.rmtree(td, ignore_errors=True)

# --- 3. apply_data reconcile: drop an empty leftover week; fail closed when games exist ---
sys.path.insert(0, TOOLS)
import apply_data as AD

td = tempfile.mkdtemp(prefix='w14rec_')
try:
    tree = os.path.join(td, 'out')
    # Empty week 14 listed, no file, no games: drop it.
    write_site(tree, {'13': 'w13.json', '14': 'w14.json'}, {'w13.json': SH13})
    AD.reconcile_whatif_shards(tree, s1=None)
    idx = load(os.path.join(tree, 'data/whatif/index.json'))
    ok(idx['shards'] == {'13': 'w13.json'}, 'reconcile drops empty missing week 14, got %s' % idx['shards'])
    # Week 14 has games, file still missing: fail closed.
    tree2 = os.path.join(td, 'out2')
    extra_g = [{'id': '401869535', 'week': 14, 'h': 0, 'a': 1, 'neutral': False, 'p_home': 600}]
    write_site(tree2, {'13': 'w13.json', '14': 'w14.json'}, {'w13.json': SH13}, extra_index_games=extra_g)
    rc = 0
    try:
        AD.reconcile_whatif_shards(tree2, s1=None)
    except SystemExit as e:
        rc = e.code if isinstance(e.code, int) else 1
    ok(rc == 3, 'reconcile fail-closes (exit 3) when week 14 games exist and the file is missing, got %s' % rc)
    # S1 has the file: copy it, keep the index entry.
    tree3 = os.path.join(td, 'out3'); s1 = os.path.join(td, 's1b')
    write_site(tree3, {'13': 'w13.json', '14': 'w14.json'}, {'w13.json': SH13}, extra_index_games=extra_g)
    write_json(os.path.join(s1, 'data/whatif/w14.json'), SH14)
    write_json(os.path.join(s1, 'data/whatif/index.json'), mini_index({'13': 'w13.json', '14': 'w14.json'}, games=extra_g))
    AD.reconcile_whatif_shards(tree3, s1=s1)
    ok(os.path.isfile(os.path.join(tree3, 'data/whatif/w14.json')), 'reconcile copies w14.json from S1')
    ok(load(os.path.join(tree3, 'data/whatif/index.json'))['shards'].get('14') == 'w14.json',
       'reconcile keeps w14 once the file is present')
finally:
    shutil.rmtree(td, ignore_errors=True)

# --- 4. build_tile_data skips a legitimately empty listed week ---
td = tempfile.mkdtemp(prefix='w14empty_')
try:
    tree = os.path.join(td, 'site')
    write_site(tree, {'13': 'w13.json', '14': 'w14.json'}, {'w13.json': SH13})  # no w14 file, no week 14 games
    rtd = subprocess.run([sys.executable, os.path.join(TOOLS, 'build_tile_data.py'), tree],
                         capture_output=True, text=True)
    ok(rtd.returncode == 0, 'tile-data skips empty missing week 14: %s' % (rtd.stdout + rtd.stderr)[-400:])
    outp = os.path.join(tree, 'data/tile-data.json')
    ok(os.path.isfile(outp), 'tile-data.json written')
finally:
    shutil.rmtree(td, ignore_errors=True)

# --- 5. Optional: today's live index + a new w14 shard ---
live_data = os.environ.get('KT_W14_LIVE_DATA', '').strip()
if live_data and os.path.isfile(os.path.join(live_data, 'whatif/index.json')):
    td = tempfile.mkdtemp(prefix='w14live_')
    try:
        live_idx = load(os.path.join(live_data, 'whatif/index.json'))
        ok(live_idx.get('shards') == {'12': 'w12.json', '13': 'w13.json', '15': 'w15.json'},
           'today live shards should be 12/13/15, got %s' % live_idx.get('shards'))
        def plant(root, with_w14=False):
            dstd = os.path.join(root, 'data')
            shutil.copytree(live_data, dstd)
            if with_w14:
                idx = load(os.path.join(dstd, 'whatif/index.json'))
                idx['shards'] = dict(idx['shards'])
                idx['shards']['14'] = 'w14.json'
                idx['games'] = list(idx['games']) + [
                    {'id': '401869535', 'week': 14, 'h': 0, 'a': 1, 'neutral': False, 'p_home': 600}
                ]
                write_json(os.path.join(dstd, 'whatif/index.json'), idx)
                write_json(os.path.join(dstd, 'whatif/w14.json'), SH14)
                bun = load(os.path.join(dstd, 'sim-bundle.json'))
                bun['games'] = list(bun.get('games') or []) + [{'id': '401869535', 'date': '2026-12-05T00:00Z', 'ip': False}]
                write_json(os.path.join(dstd, 'sim-bundle.json'), bun)
        live, s0, s1, out = [os.path.join(td, n) for n in ('L', 'S0', 'S1', 'O')]
        plant(live, False); shutil.copytree(live, s0); plant(s1, True); shutil.copytree(live, out)
        r = run_old_merge3(live, s0, s1, out, os.path.join(td, 'rep-old.json'))
        ok(r.returncode == 0 and not os.path.isfile(os.path.join(out, 'data/whatif/w14.json')),
           'today data: old merge3 leaves w14.json off the merged tree')
        shutil.rmtree(out); shutil.copytree(live, out)
        r = run_merge3(live, s0, s1, out, os.path.join(td, 'rep-new.json'))
        ok(r.returncode == 0 and os.path.isfile(os.path.join(out, 'data/whatif/w14.json')),
           'today data: fixed merge3 copies w14.json')
        rtd = subprocess.run([sys.executable, os.path.join(TOOLS, 'build_tile_data.py'), out],
                             capture_output=True, text=True)
        ok(rtd.returncode == 0, 'today data: tile-data green after the copy: %s' % (rtd.stdout + rtd.stderr)[-500:])
    finally:
        shutil.rmtree(td, ignore_errors=True)
else:
    print('note: KT_W14_LIVE_DATA not set; skipped today-live merge check')

print('%d checks, %d failed' % (n_checks[0], len(fails)))
for f in fails:
    print('FAIL', f)
sys.exit(1 if fails else 0)
