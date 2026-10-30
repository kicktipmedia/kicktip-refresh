#!/usr/bin/env python3
"""Exporter for data/tb/resume.json (Set 2b, tool strength_of_record). Run in the refresh step right after sim-bundle.json is written (same place as gen_needs_by_record.js / gen_ccg_games.js).
  python3 gen_resume.py --pipeline <pipeline root with src/ratings.py, data/store/games_rated.json, data/ref/conf_2026.json> --bundle <site data/sim-bundle.json> --out <data/tb/resume.json>
No new source and no network: it calls the pipeline's own ratings.fit() on the games file the refresh already wrote, i.e. the run that produced sim-bundle.
Fail-closed: the fit must reproduce the bundle's published colley[] (to 1e-6), sor_sd and resume_sd (to 1e-9), otherwise the games file is not the bundle's run and nothing is written.
resume = 0.7*z(sor) + 0.3*z(colley) over the 138 FBS teams (ratings.py W_SOR / W_COLLEY), rk 1..138 by resume (ties by slug). Nothing here ships (tools/ is never copied into a build)."""
import argparse, importlib.util, json, os, sys
import numpy as np
ap = argparse.ArgumentParser(); ap.add_argument('--pipeline', required=True); ap.add_argument('--bundle', required=True); ap.add_argument('--out', required=True); a = ap.parse_args()
spec = importlib.util.spec_from_file_location('kt_ratings', os.path.join(a.pipeline, 'src', 'ratings.py')); R = importlib.util.module_from_spec(spec); spec.loader.exec_module(R)
G = json.load(open(os.path.join(a.pipeline, 'data', 'store', 'games_rated.json'))); G.sort(key=lambda g: g['date'])
conf = json.load(open(os.path.join(a.pipeline, 'data', 'ref', 'conf_2026.json')))
m = R.fit(G, conf); B = json.load(open(a.bundle)); M = B['model']; n = B['n']; F = [i for i in range(n) if i != B['fcs']]
assert m['n'] == n and len(M['colley']) == n, 'team count differs from the bundle'
err_c = float(np.max(np.abs(np.round(m['colley'], 6) - np.array(M['colley']))))
assert err_c <= 1e-6, 'colley differs from the bundle (%g): games file is not this bundle\'s run' % err_c
assert abs(m['sor_sd'] - M['sor_sd']) < 1e-9 and abs(m['resume_sd'] - M['resume_sd']) < 1e-9, 'sor_sd / resume_sd differ from the bundle'
sor = np.array(m['sor']); col = np.array(M['colley'])
z = lambda v: (v - v[F].mean()) / v[F].std()
res = R.W_SOR * z(sor) + R.W_COLLEY * z(col)
assert abs(float(res[F].std()) - M['resume_sd']) < 1e-6
slug = {i: B['teams'][i]['g'] for i in F}
order = sorted(F, key=lambda i: (-round(float(res[i]), 6), slug[i]))
t = {slug[i]: {'rk': k + 1, 'z': round(float(res[i]), 4), 'sor': round(float(sor[i]), 4)} for k, i in enumerate(order)}
out = {'v': 1, 'asof': B['as_of'], 'model_label': B.get('model_label'), 'n': len(F), 'w_sor': R.W_SOR, 'w_colley': R.W_COLLEY,
       'doc': 'Set 2b resume. t[slug]: rk = KickTip resume rank (1 = hardest record to match), z = resume score = w_sor*z(sor) + w_colley*z(colley) over the FBS teams, sor = record-against-schedule score (wins minus the chance a top-25 level team wins the same games, same opponents and sites); colley = sim-bundle model.colley. From the pipeline ratings run that produced sim-bundle (as-of above).',
       'sd': {'sor': round(M['sor_sd'], 9), 'resume': round(M['resume_sd'], 9)}, 't': dict(sorted(t.items()))}
json.dump(out, open(a.out, 'w'), separators=(',', ':'), sort_keys=False)
print('wrote', a.out, os.path.getsize(a.out), 'bytes teams', len(t), 'colley err', err_c)
