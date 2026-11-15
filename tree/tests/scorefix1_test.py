"""scorefix1: refresh.correct_scores updates a saved final only for an ESPN STATUS_FINAL, non 0-0 score with the same winner; everything else is held
(saved row unchanged, logged "held: <id> <reason>"). Scores are logged home-away. python3 tests/scorefix1_test.py [inputs dir with data/store]"""
import os, sys, json, copy
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(ROOT + '/src/refresh.py').read(); ns = {}
i = src.index('def correct_scores'); exec(src[i:src.index('\ndef ', i + 5)], ns); C = ns['correct_scores']; fails = []; n = 0
def ok(name, c, d=''):
    global n; n += 1
    if not c: fails.append('%s %s' % (name, d))
def saved(): return dict(id='9', home='98', away='55', hs=28, as_=21, box={'98': {'yds': 400}}, q3=[21, 14])
def run(status, hs, as_):
    r = {'9': saved()}; s = {'9': dict(id='9', home='98', away='55', hs=hs, as_=as_, done=True, status=status, an='Away U', hn='Home U')}
    f, h = C(r, s); return r['9'], f, h
for name, st, hs, as_ in (('0-0 final', 'STATUS_FINAL', 0, 0), ('cancelled 0-0', 'STATUS_CANCELED', 0, 0), ('postponed 0-0', 'STATUS_POSTPONED', 0, 0),
                          ('forfeit 1-0', 'STATUS_FORFEIT', 1, 0), ('winner flip', 'STATUS_FINAL', 21, 28), ('tie', 'STATUS_FINAL', 24, 24)):
    r, f, h = run(st, hs, as_)
    ok(name + ': saved row unchanged', (r['hs'], r['as_']) == (28, 21) and r['box'] == {'98': {'yds': 400}}, r)
    ok(name + ': held, not fixed', f == [] and len(h) == 1 and h[0].startswith('held: 9 '), (f, h))
r, f, h = run('STATUS_FINAL', 27, 21)
ok('same-winner correction applied', (r['hs'], r['as_']) == (27, 21) and r['box'] == {'98': {'yds': 400}} and r['q3'] == [21, 14] and h == [], r)
ok('log is home-away', f == ['9 Away U at Home U (home-away): 28-21 -> 27-21'], f)
r2 = {'9': r}; f2, h2 = C(r2, {'9': dict(id='9', home='98', away='55', hs=27, as_=21, done=True, status='STATUS_FINAL')})
ok('rerun idempotent', f2 == [] and h2 == [] and (r['hs'], r['as_']) == (27, 21), (f2, h2))
r, f, h = run('STATUS_IN_PROGRESS', 35, 21); ok('completed flag but status not final: held', f == [] and len(h) == 1 and 'STATUS_IN_PROGRESS' in h[0] and r['hs'] == 28, (f, h))
r = {'9': saved()}; f, h = C(r, {'9': dict(id='9', home='98', away='55', hs=None, as_=None, done=False, status='STATUS_IN_PROGRESS')})
ok('not done: ignored', f == [] and h == [] and r['9']['hs'] == 28, (f, h))
if len(sys.argv) > 1:   # real inputs (run 43661584986): exactly the JXST-WKU correction, nothing held, then idempotent
    S = {g['id']: g for g in json.load(open(sys.argv[1] + '/data/store/schedule.json'))}; R = {g['id']: g for g in json.load(open(sys.argv[1] + '/data/store/games_rated.json'))}
    f, h = C(R, S); print('real inputs:', f, h)
    ok('real: one correction', f == ['401870752 Jacksonville State Gamecocks at Western Kentucky Hilltoppers (home-away): 35-24 -> 34-24'], f)
    ok('real: nothing held', h == [], h)
    ok('real: no mismatch left', not [k for k, x in R.items() if k in S and S[k]['done'] and (S[k]['hs'], S[k]['as_']) != (x['hs'], x['as_'])])
    ok('real: rerun idempotent', C(R, S) == ([], []))
print('%d checks, %d failed' % (n, len(fails))); [print('FAIL', x) for x in fails]; sys.exit(1 if fails else 0)
