#!/usr/bin/env python3
"""Derives conf_race_alive expectations INDEPENDENTLY of the tool module (assets/tb/conf_race_alive.js) and of the search code (tools/alive_core.js).
Inputs (read only): <tree>/data/ccg-sim.json (results), <tree>/data/ccg-rules.json (conference names), <tree>/data/tb/ccg-alive.json (the precompute under test: lists of in / out / tie-only teams).
What is recomputed here from the raw results, in plain Python:
  * every team's conference record, games left and best possible finish (wins counted from games with w not null; w truthy = home win, as ccgsim.js does)
  * an independent counting certificate for every out team: at least `slots` rivals (2 for top-2 formats, 1 per division for division formats) whose MINIMUM final winning pct is strictly above the team's MAXIMUM final pct
    (the same pigeonhole idea as the tests, written again here with no shared code). The generator FAILS if the precompute marks a team out that the certificate cannot prove, or if the certificate proves a team out that the precompute keeps in.
What is taken from the precompute because only the search can know it: which teams are tie-only (in the race only through a ranking, draw or reading step).
usage: gen_conf_race_alive_fixtures.py <built tree>   -> writes conf_race_alive.test.json next to this file"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); T = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, '..', '..', '..', '..', 'out-tb'))
S = json.load(open(T + '/data/ccg-sim.json')); RJ = json.load(open(T + '/data/ccg-rules.json'))['rules']; A = json.load(open(T + '/data/tb/ccg-alive.json'))
VER = json.load(open(os.path.join(HERE, '..', '..', 'tools', 'analyst_verdicts.json')))['conferences']
MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
d, t = S['asof'].split(' ')[0:2]; y, mo, da = d.split('-'); hh, mm = t.split(':'); h = int(hh)
LABEL = '%s %d, %s, %d:%s %s MT' % (MON[int(mo) - 1], int(da), y, (h % 12) or 12, mm, 'PM' if h >= 12 else 'AM')
assert A['asof'] == S['asof']
def commas(n): return '{:,}'.format(n)
LIM = {'ranking_step': 'Some tiebreakers use an outside ranking.', 'draw_step': 'Some tiebreakers end in a draw.', 'immunity_step': 'One tiebreaker step depends on a late-season ranking and the final game.',
       'two_readings': 'The published rules can be read two ways here.', 'unequal_schedules': 'Teams here play different numbers of conference games', 'divisions': 'The two division winners meet',
       'rules_text_not_2026': 'The newest tiebreaker text KickTip found is for an earlier season or may be stale.'}
def facts_for(code):
    c = S['confs'][code]; n = len(c['teams']); W = [0] * n; G = [0] * n; L = [0] * n
    for g in c['games']:
        if g['w'] is None: L[g['h']] += 1; L[g['a']] += 1; continue
        win, lose = (g['h'], g['a']) if g['w'] else (g['a'], g['h']); W[win] += 1; G[win] += 1; G[lose] += 1
    slots = 2 if RJ[code]['fmt'] == 'top2' else 1
    rows = []
    for i, tm in enumerate(c['teams']):
        fg = G[i] + L[i]; rows.append(dict(name=tm['short'], slug=tm['slug'], w=W[i], l=G[i] - W[i], left=L[i], bw=W[i] + L[i], bl=G[i] - W[i], lo=W[i] / fg, hi=(W[i] + L[i]) / fg, i=i, div=(c['div'] or [None] * n)[i] if c['div'] else None))
    for r in rows:
        if r['slug'] in ('x',): pass
    # certificate
    cert = set()
    for r in rows:
        pool = [q for q in rows if q is not r and (slots == 2 or (c['div'] and False) or True)]
        if RJ[code]['fmt'] == 'div':
            # division format: a team is out of its division race if some rival IN ITS DIVISION has min pct above its max pct. Division membership comes from the results file's div table.
            dv = c['div']
            pool = [q for q in rows if q is not r and dv and dv[q['i']] == dv[r['i']]] if dv else []
        if sum(1 for q in pool if q['lo'] > r['hi'] + 1e-12) >= slots: cert.add(r['slug'])
    return c, rows, cert, slots
def pigeon(S, code, rows, c, slots):
    """Global-wins certificate, no tiebreaker involved: every game gives one win, so final wins add up to T = number of conference games. X is in the top `slots` only if at most slots-1 rivals finish strictly ahead of X's final pct.
    With wx final wins for X, a rival that is not ahead can hold at most floor(wx*fin_i/fin_x) wins (and at most its own maximum); the slots-1 rivals allowed ahead reach their maximum. If that total is below T for every wx, X is out. k = how many MORE rivals could be ruled ineligible (uncapped) and the call still stands (-1 = not proven)."""
    if RJ[code]['fmt'] != 'top2' or RJ[code].get('tie_group', 'equal') != 'equal': return {}
    T = len(c['games']); fin = {r['slug']: r['w'] + r['l'] + r['left'] for r in rows}; mx = {r['slug']: r['bw'] for r in rows}; res = {}
    for r in rows:
        def possible(k):
            for wx in range(r['w'], r['bw'] + 1):
                tot = wx; gains = []
                for q in rows:
                    if q is r: continue
                    cap = min(mx[q['slug']], (wx * fin[q['slug']]) // fin[r['slug']]); tot += cap; gains.append(mx[q['slug']] - cap)
                gains.sort(reverse=True); tot += sum(gains[:slots - 1 + k])
                if tot >= T: return True
            return False
        if not possible(0):
            k = 0
            while k < len(rows) and not possible(k + 1): k += 1
            res[r['slug']] = k
    return res
cases, invalid, match = [], [], []
def line_in(r): return '%s: %d-%d, %s, best finish %d-%d' % (r['name'], r['w'], r['l'], 'no games left' if r['left'] == 0 else 'one game left' if r['left'] == 1 else '%d games left' % r['left'], r['bw'], r['bl'])
def line_out(r): return '%s is out of the race on our reading of the rules, at %d-%d with best finish %d-%d.' % (r['name'], r['w'], r['l'], r['bw'], r['bl'])
summary = {}; SEARCH_OUT = []; OUTS = {}
for code in S['confs']:
    c, rows, cert, slots = facts_for(code); X = A['confs'][code]; by = {r['slug']: r for r in rows}
    out = [t['s'] for t in X['teams'] if t['st'] == 'out']; tie = [t['s'] for t in X['teams'] if t['st'] == 'in' and t['sure'] is False]
    assert set(cert) <= set(out), '%s: counting certificate proves %s out but the precompute keeps them in' % (code, sorted(set(cert) - set(out)))
    PK = pigeon(S, code, rows, c, slots)
    for s in set(out) - set(cert):   # not provable by the per-team counting argument: must be provable by the global-wins argument, which needs no tiebreaker at all
        assert s in PK, (code, s, 'out call without an independent certificate')
        SEARCH_OUT.append(code + '/' + s + ' (global wins, k=%d)' % PK[s])
    assert set(PK) - set(out) == set(), (code, 'global-wins certificate proves a team out that the precompute keeps in', set(PK) - set(out))
    for t in X['teams']:   # records in the precompute equal the independently counted ones
        r = by[t['s']]; assert (t['w'], t['l'], t['left'], t['best']['w'], t['best']['l']) == (r['w'], r['l'], r['left'], r['bw'], r['bl']), (code, t['s'])
    OUTS[code] = out
    rem = sum(1 for g in c['games'] if g['w'] is None); name = RJ[code]['name']
    n_in = len(rows) - len(out); n_main = n_in - len(tie)
    contains = [name + ': the race for the conference championship game', 'In the race (%d)' % n_main, 'Out of the race (%d)' % len(out),
                'Understood as: which %s teams are in the race, and which are out of the race on our reading of the rules.' % name,
                'In the race means some set of results from the games left puts a team in the game.',
                'Race status is our reading of the conference\'s published tiebreaker rules, not a chance estimate.',
                'As of %s. Chances and ranks on KickTip are estimates, not forecasts.' % LABEL]
    an = VER[code]['verdict']
    if an == 'none': contains.append('A person has not yet checked this conference\'s rules text against its source.')
    elif an != 'verified': contains.append('A person who compared that reading with the published text found steps KickTip does not yet match, so some calls could change.')
    contains.append(('%s conference games are still to be played.' % commas(rem)) if rem > 1 else 'One conference game is still to be played.' if rem == 1 else 'All conference games have been played.')
    contains += [LIM[k] for k in X['limits']]
    contains += [line_in(by[r['slug']]) for r in rows if r['slug'] not in out]; contains += [line_out(by[s]) for s in out]
    if tie: contains.append('In the race, but only if a tiebreaker step KickTip cannot see goes their way (%d)' % len(tie))
    if not out: contains.append('None yet.')
    exp = {'facts.conference.id': code, 'facts.conference.name': name, 'facts.conference.remaining': rem, 'facts.counts.teams': len(rows), 'facts.counts.in_race': n_in, 'facts.counts.out': len(out), 'facts.counts.tie_only': len(tie),
           'facts.counts.clinched': 0, 'facts.wording': 'neutral', 'facts.verified': False, 'facts.analyst': an, 'facts.view': 'all', 'asof.label': LABEL}
    cases.append({'id': 'RACE-RUN-%s' % code, 'params': {'conference': code}, 'expect': exp,
                  'render': {'contains': contains, 'not_contains': ['clinched', 'Clinched', 'eliminated', 'Eliminated', 'all teams', 'every team is', 'CCG', 'title game', 'has been checked by a person against its source'] + (['has not yet checked'] if an != 'none' else []) + (['found steps KickTip does not yet match'] if an in ('verified', 'none') else [])}})
    summary[code] = (len(rows), len(out), len(tie), rem)
    for s in out:
        r = by[s]; cases.append({'id': 'RACE-TEAM-out-%s' % s, 'params': {'conference': code, 'team': s}, 'expect': {'facts.view': 'team', 'facts.team.standing': 'out', 'facts.team.w': r['w'], 'facts.team.l': r['l'], 'facts.team.left': r['left'], 'facts.team.best': {'w': r['bw'], 'l': r['bl']}, 'facts.team.id': s},
            'render': {'contains': ['%s: the race for the conference championship game' % r['name'], '%s is out of the race on our reading of the rules.' % r['name'], 'Understood as: whether %s is out of the race on our reading of the rules.' % r['name'],
                                    'Conference record %d-%d with %s. Best possible finish %d-%d.' % (r['w'], r['l'], ('%d games left' % r['left']) if r['left'] > 1 else 'one game left' if r['left'] == 1 else 'no games left', r['bw'], r['bl']),
                                    'No set of results from the games left puts it in the game under the rules we read.' ], 'not_contains': ['eliminated', 'In the race (', 'is in the race, but', 'is in the race for']}})
    for s in tie:
        r = by[s]; cases.append({'id': 'RACE-TEAM-tie-%s' % s, 'params': {'team': s}, 'expect': {'facts.conference.id': code, 'facts.team.standing': 'in_tie', 'facts.team.tie_only': True},
            'render': {'contains': ['%s is in the race, but only if a tiebreaker step KickTip cannot see goes its way.' % r['name']], 'not_contains': ['out of the race on our reading', 'clinched']}})
    top = [r for r in rows if r['slug'] not in out and r['slug'] not in tie][0]
    cases.append({'id': 'RACE-TEAM-in-%s' % top['slug'], 'params': {'team': top['slug']}, 'expect': {'facts.conference.id': code, 'facts.team.standing': 'in', 'facts.team.w': top['w'], 'facts.team.l': top['l']},
        'render': {'contains': ['%s is in the race for the conference championship game.' % top['name']], 'not_contains': ['clinched', 'only if a tiebreaker', 'out of the race on our reading of the rules.']}})
# status views (from the independent certificate lists)
bo = [r for r in facts_for('big10')[1] if r['slug'] in OUTS['big10']]
cases.append({'id': 'RACE-VIEW-big10-out', 'params': {'conference': 'big10', 'status': 'out'}, 'expect': {'facts.view': 'out', 'facts.counts.out': len(bo)},
              'render': {'contains': ['which Big Ten teams are out of the race on our reading of the rules'] + [line_out(r) for r in bo], 'not_contains': ['In the race (', 'Big Ten teams are in the race']}})
cases.append({'id': 'RACE-VIEW-sec-in', 'params': {'conference': 'sec', 'status': 'in'}, 'expect': {'facts.view': 'in'},
              'render': {'contains': ['which SEC teams are in the race.', 'In the race ('], 'not_contains': ['Out of the race (', 'Vanderbilt is out of the race', 'are out of the race']}})
cases.append({'id': 'RACE-VIEW-acc-out-empty', 'params': {'conference': 'acc', 'status': 'out'}, 'expect': {'facts.view': 'out', 'facts.counts.out': 0},
              'render': {'contains': ['Out of the race (0)', 'None yet.'], 'not_contains': ['In the race (', 'No team is out of the race']}})
for p, why in [({}, 'nothing asked'), ({'conference': 'big13'}, 'unknown conference'), ({'team': 'Utah'}, 'team must be a slug'), ({'team': 'not-a-team'}, 'unknown team'), ({'conference': 'sec', 'status': 'clinched'}, 'gated status not offered'),
               ({'conference': 'sec', 'status': 'alive'}, 'status not in list'), ({'conference': 'sec', 'team': 'michigan-state'}, 'team not in that conference')]:
    invalid.append({'id': 'RACE-BAD-%d' % (len(invalid) + 1), 'params': p, 'reason': 'bad_param', 'note': why})
invalid.append({'id': 'RACE-BAD-ind-conf', 'params': {'conference': 'big12', 'team': 'notre-dame'}, 'reason': 'bad_param', 'note': 'an independent is not in the Big 12'})
for slug, nm in [('notre-dame', 'Notre Dame'), ('uconn', 'UConn')]:
    cases.append({'id': 'RACE-INDEP-%s' % slug, 'params': {'team': slug}, 'expect': {'facts.view': 'independent', 'facts.conference.id': 'ind', 'facts.team.id': slug, 'facts.team.name': nm, 'asof.label': LABEL},
                  'render': {'contains': ['%s: the race for the conference championship game' % nm, 'Understood as: whether %s is in a conference race.' % nm, '%s plays as an independent, so it is not in a conference race.' % nm,
                                          'As of %s. Chances and ranks on KickTip are estimates, not forecasts.' % LABEL], 'not_contains': ['out of the race', 'In the race (', 'clinched', 'eliminated']}})
cases.append({'id': 'RACE-INDEP-conf', 'params': {'conference': 'ind'}, 'expect': {'facts.view': 'independent', 'facts.conference.id': 'ind', 'facts.conference.name': 'Independents'},
              'render': {'contains': ['Independents: the race for the conference championship game', 'Notre Dame and UConn play as independents, so they are not in a conference race.', 'As of %s.' % LABEL], 'not_contains': ['out of the race', 'In the race (']}})

def M(i, text, params, page=None):
    d = {'id': 'RACE-M-%02d' % i, 'text': text, 'expect': {'tool': 'conf_race_alive', 'params': params}}
    if page: d['page'] = page
    match.append(d)
M(1, 'Who is still in the mix for the Big 12 championship game?', {'conference': 'big12', 'status': 'in'})
M(2, 'which teams can still reach the SEC championship game', {'conference': 'sec', 'status': 'in'})
M(3, 'who is eliminated from the Big Ten championship game race', {'conference': 'big10', 'status': 'out'})
M(4, 'Is Arizona State out of the Big 12 championship game race?', {'conference': 'big12', 'team': 'arizona-state'})
M(5, "is Texas Tech still alive for the conference championship game", {'team': 'texas-tech'})
M(6, 'who is still alive in the ACC race', {'conference': 'acc', 'status': 'in'})
M(7, 'who is still alive?', {'conference': 'big12', 'status': 'in'}, {'mode': 'conference', 'conf': 'big12'})
M(8, 'Which MAC teams are out of the race for the conference title game', {'conference': 'midam', 'status': 'out'})
M(10, 'who is out of the Sun Belt race', {'conference': 'belt', 'status': 'out'})
M(11, 'is Notre Dame still alive for a conference championship game', {'team': 'notre-dame'})
M(12, 'is Michigan State eliminated from the Big Ten championship game race', {'conference': 'big10', 'team': 'michigan-state'})
M(13, "Who's eliminated in the SEC?", {'conference': 'sec', 'status': 'out'})
M(14, 'who is eliminated in the Big Ten', {'conference': 'big10', 'status': 'out'})
M(15, 'which teams are ruled out in the MAC', {'conference': 'midam', 'status': 'out'})
M(16, "who's eliminated?", {'conference': 'big12', 'status': 'out'}, {'mode': 'conference', 'conf': 'big12'})
M(9, 'Is Utah still alive for the conference championship game?', {'team': 'utah'})   # core: Utah resolves to Utah, no chooser (CONTRACT 4.2)
match.append({'id': 'RACE-M-17', 'text': 'Are the Bears still alive for the conference championship game?', 'expect_clarify': {'tool': 'conf_race_alive', 'param': 'team', 'options': ['baylor', 'missouri-state']}})
M(18, 'who is out of the Mid-American race', {'conference': 'midam', 'status': 'out'})   # longer name wins: not American
M(19, 'who is in the race in the American Athletic Conference', {'conference': 'American', 'status': 'in'})
M(20, 'is the U still alive for the conference championship game', {'team': 'utah'})
def N(i, text, extra=None):
    d = {'id': 'RACE-N-%02d' % i, 'text': text, 'expect': None}; d.update(extra or {}); match.append(d)
N(1, "what are Arizona State's chances to reach the Big 12 championship game")
N(2, 'who will win the Big 12 championship game')
N(3, 'who is still alive for the playoff')
N(4, 'who has clinched the Big 12 championship game')
N(5, 'is anyone still alive for the national championship')
N(6, 'if Utah beats Texas Tech is Utah still alive for the Big 12 championship game')
N(7, 'who is still alive in the Big 12 or the SEC championship race')
N(8, 'is Arizona State alive')
N(9, 'what does Arizona State need to reach the Big 12 championship game')
N(10, 'Utah or Texas Tech still alive for the Big 12 championship game')
N(11, 'who is still alive in the Big 12')
N(12, 'who is still in the mix for the 12-team playoff field')
N(13, 'put $20 on Utah to be alive for the Big 12 championship game', {'expect_gate': 'money'})
N(14, 'who is alive in the Big 12 championship game race and what are the odds')
N(15, 'is Notre Dame in the Big 12 race')
N(16, 'who is out of the race for the Independents championship game')
N(17, 'what time is the Big 12 championship game')
N(18, 'how is Arizona State doing in the Big 12 race')
N(19, 'who is still alive in the Big 12 championship game race compared with the SEC')
N(20, 'which seeds are still in the mix for a first round bye')
N(21, 'who is eliminated from the playoff')
N(22, "who's eliminated?")
N(23, 'who is eliminated in the Big 12 or the SEC')
N(24, 'is Utah eliminated')
N(25, 'who is eliminated in the Independents')
N(26, 'what are the odds Vanderbilt is eliminated in the SEC')
doc = {'tool': 'conf_race_alive', 'schema': 1, 'frozen': '2026-10-24', 'run': cases, 'invalid': invalid, 'match': match}
json.dump(doc, open(os.path.join(HERE, 'conf_race_alive.test.json'), 'w'), indent=1)
print('wrote', len(cases), 'run cases,', len(invalid), 'invalid,', len(match), 'match;', 'out calls proved only by the global-wins argument:', SEARCH_OUT, summary)
