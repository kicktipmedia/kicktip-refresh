#!/usr/bin/env python3
"""apply_data.py: put a new KickTip pipeline run onto a LIVE site zip, data-derived files only.
usage: apply_data.py --base-zip Z [--base-sha SHA] --s0 <pipeline site built from the base's data> --s1 <pipeline site of the new run>
                     --pipeline <pipeline tree root (data/store, data/ref, data/ccg.json)> --out OUT.zip [--report R.json] [--no-network] [--ranks ranks.json]
Method (same as toolbox9c, generalised):
 1. extract base; old as-of = base data/sim-bundle as_of (must equal S0's), new = S1's.
 2. 3-way merge live + (S0 -> S1) per file (tools/merge3.py: JSON leaf-wise, HTML git merge-file); any conflict = exit 2.
 3. post-fixes the live builds apply: ' (model)' strip, 'time TBA' -> 'time TBD'.
 4. regenerate derived data: tile-data, data/tb/* (conf-bids, conf-outcome, team-stats, history, resume, ccg-games, needs-by-record,
    path-by-stage, trend, ccg-alive, ccg-paths + per-conf split, cfp-rankings).
 5. as-of stamps in every html/json/js text file: all known display forms old -> new, including data-asof="YYYY-MM-DD HH:MM" (home7c).
 5a. merged: tools/polish_refresh.py re-derives the team chances-card record line (pc-sub) from the merged page text.
 5b. nojs1 (if the base has assets/stamp.js): the base is unbaked before the merge; after step 5 tools/bake_static.js bakes numbers + 'Updated'
     stamps into HTML and --verify fails the run if any page is stale.
 6. restamp ?v= tokens; allow-list check: every changed file is html, data/**, or a token-only change; _worker.js identical.
 7. deterministic zip (sorted, 2026-01-01 00:00, 0644, deflate) built twice, sha must match.
Exit 0 ok; 2 merge conflict; 3 check failed; 4 non-deterministic."""
import argparse, datetime, hashlib, json, os, re, shutil, subprocess, sys, tempfile, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
def sha(b): return hashlib.sha256(b).hexdigest()
def rd(p): return open(p, 'rb').read()
def walk(root):
    for d, dn, fn in os.walk(root):
        dn.sort()
        for f in sorted(fn): p = os.path.join(d, f); yield os.path.relpath(p, root).replace(os.sep, '/'), p
def die(code, msg): print('APPLY_DATA FAIL:', msg, file=sys.stderr); sys.exit(code)
def forms(asof):
    d = datetime.datetime.strptime(asof.replace(' MT', ''), '%Y-%m-%d %H:%M')
    h = d.strftime('%I').lstrip('0'); tm = '%s:%s %s' % (h, d.strftime('%M'), d.strftime('%p'))
    md = '%s %d' % (d.strftime('%b'), d.day)
    return [('%s, %s, %d, %s MT' % (d.strftime('%a'), md, d.year, tm)), ('%s, %d, %s MT' % (md, d.year, tm)), ('%s, %s MT' % (md, tm)),
            d.strftime('%Y-%m-%d %H:%M') + ' MT', 'data-asof="%s"' % d.strftime('%Y-%m-%d %H:%M'), ('"%s, %s"' % (md, tm)),
            'recalculated %s, %d.' % (md, d.year), d.strftime('%Y-%m-%d_%H%M')]
def run(cmd, env, what):
    r = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if r.returncode != 0: die(3, '%s failed rc=%d: %s' % (what, r.returncode, (r.stdout + r.stderr)[-1500:]))
    return r.stdout
def build_once(tmp, a, network):
    env = dict(os.environ, PYTHONHASHSEED='0', TZ='UTC', LC_ALL='C')
    base = os.path.join(tmp, 'base'); out = os.path.join(tmp, 'out'); os.makedirs(base)
    with zipfile.ZipFile(a.base_zip) as z: names = z.namelist(); z.extractall(base)
    BAKE = os.path.exists(base + '/assets/stamp.js')   # nojs1: base carries baked numbers -> unbake so the 3-way merge sees pipeline-shaped HTML; re-baked after step 4
    if BAKE: run(['node', HERE + '/bake_static.js', base, '--unbake'], env, 'unbake')
    shutil.copytree(base, out)
    B0 = json.load(open(base + '/data/sim-bundle.json'))['as_of']; S0a = json.load(open(a.s0 + '/data/sim-bundle.json'))['as_of']; S1a = json.load(open(a.s1 + '/data/sim-bundle.json'))['as_of']
    if B0 != S0a: die(3, 'base as_of %s != s0 as_of %s (wrong S0 pipeline site)' % (B0, S0a))
    F0, F1 = forms(B0), forms(S1a)
    # 2. merge
    rep_p = os.path.join(tmp, 'merge.json')
    run([sys.executable, HERE + '/merge3.py', base, a.s0, a.s1, out, rep_p, json.dumps(list(zip(F0[:4], F1[:4])))], env, 'merge3')
    rep = json.load(open(rep_p))
    if rep['conflict'] or rep['json_conflicts']: die(2, 'merge conflicts: %s %s' % (rep['conflict'][:10], list(rep['json_conflicts'])[:10]))
    # stale what-if shards (week no longer simulated)
    deleted = []
    for rel, p in list(walk(out)):
        if re.match(r'^data/(m/(elo|eff)/)?whatif/w\d+\.json$', rel) and os.path.exists(a.s0 + '/' + rel) and not os.path.exists(a.s1 + '/' + rel):
            os.remove(p); deleted.append(rel)
    # 3. post-fixes of the live builds
    for rel, p in walk(out):
        if rel.endswith(('.html', '.js', '.json')) and rel not in ('_worker.js', 'scnai.js') and os.path.exists(base + '/' + rel) and rd(p) != rd(base + '/' + rel):
            t = open(p, encoding='utf-8').read(); t2 = t.replace(' (model)', '').replace('time TBA', 'time TBD')
            if t2 != t: open(p, 'w', encoding='utf-8').write(t2)
    # 2b. national ranks (optional --ranks FILE from tools/ranks_step.sh): replace data/ranks.json only if the live site has it
    if getattr(a, 'ranks', None) and os.path.exists(a.ranks) and os.path.exists(out + '/data/ranks.json'):
        rj = json.load(open(a.ranks, encoding='utf-8'))
        if not (rj.get('v') == 1 and len(rj.get('t', {})) >= 130 and len(rj.get('cats', [])) == 9): die(3, 'bad --ranks file %s' % a.ranks)
        if rd(a.ranks) != rd(out + '/data/ranks.json'): shutil.copyfile(a.ranks, out + '/data/ranks.json')
    # 4. derived data
    T, P, S, Bn = HERE, a.pipeline, out, out + '/data/sim-bundle.json'; SIM = out + '/assets/ks/sim.js'; tb = out + '/data/tb'
    steps = [
        (['python3', T + '/build_tile_data.py', S], 'tile-data'),
        (['node', T + '/gen_conf_bids.js', '--sim', SIM, '--bundle', Bn, '--out', tb + '/conf-bids.json'], 'conf-bids'),
        (['node', T + '/gen_conf_outcome.js', '--sim', SIM, '--bundle', Bn, '--out', tb + '/conf-outcome.json'], 'conf-outcome'),
        (['python3', T + '/gen_team_stats.py', '--pipeline', P, '--bundle', Bn, '--out', tb + '/team-stats.json'], 'team-stats'),
        (['python3', T + '/gen_history.py', '--pipeline', P, '--bundle', Bn, '--out', tb + '/history.json'], 'history'),
        (['python3', T + '/gen_resume.py', '--pipeline', P, '--bundle', Bn, '--out', tb + '/resume.json'], 'resume'),
        (['node', T + '/gen_ccg_games.js', '--sim', SIM, '--bundle', Bn, '--slots', P + '/data/ccg.json', '--out', tb + '/ccg-games.json'], 'ccg-games'),
        (['node', T + '/gen_needs_by_record.js', '--sim', SIM, '--bundle', Bn, '--whatif', out + '/data/whatif', '--out', tb + '/needs-by-record.json'], 'needs-by-record'),
        (['node', T + '/gen_path_by_stage.js', '--sim', SIM, '--bundle', Bn, '--out', tb + '/path-by-stage.json'], 'path-by-stage'),
        (['node', T + '/gen_trend.js', '--pred', out + '/data/pred-teams.json', '--bundle', Bn, '--out', tb + '/trend.json'], 'trend'),
        (['node', T + '/lanes/conf_race_alive/tools/build_alive.js', '--root', S], 'ccg-alive'),
        (['node', T + '/lanes/p4/tools/build_ccg_paths.js', '--root', S, '--alive', tb + '/ccg-alive.json', '--out', tb + '/ccg-paths.json'], 'ccg-paths'),
        (['node', T + '/gen_ccg_paths_conf.js', S], 'ccg-paths split')]
    if network: steps.append((['python3', T + '/export_cfp_rankings.py', S], 'cfp-rankings'))
    else:
        j = json.load(open(tb + '/cfp-rankings.json'))
        if j.get('released'): die(3, '--no-network but cfp rankings are released; cannot regenerate offline')
        open(tb + '/cfp-rankings.json', 'w').write(json.dumps({'asof': S1a, 'released': False, 'teams': []}, separators=(',', ':')))
    if B0 == S1a: steps = [s for s in steps if s[1] != 'ccg-alive']  # proof mode: live card carries the engine hash it was built with
    for cmd, what in steps: run(cmd, env, what)
    tbad = [rel for rel, p in walk(out) if rel.endswith(('.html', '.json')) and 'time TBA' in open(p, encoding='utf-8', errors='ignore').read()]
    for rel in tbad:
        p = out + '/' + rel; t = open(p, encoding='utf-8').read(); open(p, 'w', encoding='utf-8').write(t.replace('time TBA', 'time TBD'))
    for f in os.listdir(tmp):
        if f.endswith('ccg-alive-proof.json'): os.remove(os.path.join(tmp, f))
    # 5. stamps
    if B0 != S1a:
        for rel, p in walk(out):
            if rel == '_worker.js' or not rel.endswith(('.html', '.json', '.js')): continue
            t = open(p, encoding='utf-8').read(); t2 = t
            for o, n in zip(F0, F1): t2 = t2.replace(o, n)
            if t2 != t: open(p, 'w', encoding='utf-8').write(t2)
    # 5a. merged build: re-derive the polish chances-card record line from the merged page text (else a refresh leaves it stale)
    if os.path.exists(out + '/assets/polish.js'): run([sys.executable, HERE + '/polish_refresh.py', out], env, 'polish-refresh')
    # 5b. nojs1: bake default-model numbers + exact 'Updated' stamps into static HTML from the regenerated data (after step 5 so every data-asof is already new), then verify nothing is stale
    if BAKE:
        run(['node', HERE + '/bake_static.js', out, '--check'], env, 'bake-static')
        run(['node', HERE + '/bake_static.js', out, '--verify'], env, 'bake-verify')
    # 6. tokens + checks
    run([sys.executable, T + '/restamp.py', out, base], env, 'restamp')
    bf = {rel: sha(rd(p)) for rel, p in walk(base)}; of = {rel: p for rel, p in walk(out)}
    new = sorted(set(of) - set(bf)); gone = sorted(set(bf) - set(of))
    if new: die(3, 'unexpected new files %s' % new[:10])
    if gone != sorted(deleted): die(3, 'unexpected removed files %s' % gone[:10])
    TOK = re.compile(r'\?v=[0-9a-f]{10}'); changed = {}
    for rel in sorted(of):
        if sha(rd(of[rel])) == bf[rel]: continue
        if rel == '_worker.js': die(3, '_worker.js changed')
        if rel.endswith('.html'): changed[rel] = 'html: data/stamps/tokens'
        elif rel.startswith('data/'): changed[rel] = 'data'
        else:
            try: same = TOK.sub('?v=0', open(of[rel], encoding='utf-8').read()) == TOK.sub('?v=0', open(base + '/' + rel, encoding='utf-8').read())
            except UnicodeDecodeError: same = False
            if not same: die(3, 'non-data file changed beyond ?v= tokens: ' + rel)
            changed[rel] = 'token-only'
    for k in ('data/sim-bundle.json', 'data/tile-data.json', 'data/ccg-sim.json', 'data/whatif/index.json'):
        try: j = json.load(open(of[k]))
        except ValueError: die(3, 'unparseable output %s (%d bytes)' % (k, os.path.getsize(of[k])))
        v = j.get('as_of') or j.get('asof')
        if v != S1a: die(3, 'as-of mismatch %s: %s != %s' % (k, v, S1a))
    left = [rel for rel, p in of.items() if B0 != S1a and rel.endswith(('.html', '.json')) and any(f in open(p, encoding='utf-8', errors='ignore').read() for f in F0[:5])]
    if left: die(3, 'old as-of left in %s' % left[:10])
    z_out = os.path.join(tmp, 'site.zip')
    with zipfile.ZipFile(z_out, 'w', zipfile.ZIP_DEFLATED) as z:
        for rel in sorted(of):
            zi = zipfile.ZipInfo(rel, (2026, 1, 1, 0, 0, 0)); zi.compress_type = zipfile.ZIP_DEFLATED; zi.external_attr = 0o644 << 16; z.writestr(zi, rd(of[rel]))
    return z_out, {'base_asof': B0, 'new_asof': S1a, 'changed': changed, 'deleted': deleted, 'merge': {k: len(v) for k, v in rep.items()}, 'entries': len(of)}, out
if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--base-zip', required=True); ap.add_argument('--base-sha'); ap.add_argument('--s0', required=True); ap.add_argument('--s1', required=True)
    ap.add_argument('--pipeline', required=True); ap.add_argument('--out', required=True); ap.add_argument('--report'); ap.add_argument('--site-out'); ap.add_argument('--no-network', action='store_true'); ap.add_argument('--ranks'); a = ap.parse_args()
    if a.base_sha and sha(rd(a.base_zip)) != a.base_sha: die(3, 'base zip sha %s != expected' % sha(rd(a.base_zip)))
    res = []
    for tag in 'AB':
        tmp = tempfile.mkdtemp(prefix='apply_%s_' % tag)
        try:
            z, info, out = build_once(tmp, a, not a.no_network); h = sha(rd(z)); res.append((h, info)); print('build %s sha256 %s' % (tag, h))
            if tag == 'A':
                shutil.copy(z, a.out + '.tmp')
                if a.site_out: shutil.rmtree(a.site_out, ignore_errors=True); shutil.copytree(out, a.site_out)
        finally: shutil.rmtree(tmp, ignore_errors=True)
    if res[0][0] != res[1][0]: die(4, 'NOT DETERMINISTIC %s vs %s' % (res[0][0], res[1][0]))
    os.replace(a.out + '.tmp', a.out); info = res[0][1]; info['sha256'] = res[0][0]
    if a.report: json.dump(info, open(a.report, 'w'), indent=1)
    print('OK', a.out, res[0][0], 'changed', len(info['changed']), 'deleted', len(info['deleted']), 'asof', info['base_asof'], '->', info['new_asof'])
