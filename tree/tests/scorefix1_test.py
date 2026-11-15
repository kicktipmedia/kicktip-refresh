"""scorefix1: refresh.correct_scores updates a rated game's final score to the current ESPN final (keeps box/q3); untouched otherwise. python3 tests/scorefix1_test.py [inputs dir with data/store]"""
import os, sys, json
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, ROOT + '/src')
src = open(ROOT + '/src/refresh.py').read(); ns = {}
exec(src[src.index('def correct_scores'):src.index('\ndef ', src.index('def correct_scores') + 5)], ns); fails = []
rated = {'1': dict(id='1', home='98', away='55', hs=35, as_=24, box={'98': {'yds': 400}}, q3=[28, 17]), '2': dict(id='2', home='1', away='2', hs=10, as_=7)}
sched = {'1': dict(id='1', home='98', away='55', hs=34, as_=24, done=True, an='Jacksonville State', hn='Western Kentucky'), '2': dict(id='2', home='1', away='2', hs=10, as_=7, done=True)}
f = ns['correct_scores'](rated, sched)
if (rated['1']['hs'], rated['1']['as_']) != (34, 24) or rated['1']['box'] != {'98': {'yds': 400}} or len(f) != 1: fails.append('correction: %r %r' % (rated['1'], f))
if (rated['2']['hs'], rated['2']['as_']) != (10, 7): fails.append('untouched game changed')
if len(sys.argv) > 1:   # real inputs: after correction every rated game's score equals the schedule final
    S = {g['id']: g for g in json.load(open(sys.argv[1] + '/data/store/schedule.json'))}; R = {g['id']: g for g in json.load(open(sys.argv[1] + '/data/store/games_rated.json'))}
    f2 = ns['correct_scores'](R, S); print('real inputs corrections:', f2)
    left = [k for k, r in R.items() if k in S and S[k]['done'] and (S[k]['hs'], S[k]['as_']) != (r['hs'], r['as_'])]
    if left: fails.append('left mismatches %s' % left)
print('3 checks, %d failed' % len(fails)); [print('FAIL', x) for x in fails]; sys.exit(1 if fails else 0)
