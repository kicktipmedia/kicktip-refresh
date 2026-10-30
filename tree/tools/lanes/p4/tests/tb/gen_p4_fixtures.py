#!/usr/bin/env python3
"""Generate team_path.test.json and path_compare.test.json from the RAW data (frozen pred-teams and sim-bundle, tb/ccg-alive, tb/needs-by-record, tb/ccg-paths, tb/path-by-stage), independent of the modules.
usage: gen_p4_fixtures.py [frozen dir] [tb data dir (default: lane data/tb dirs)]"""
import json, os, sys, re
HERE = os.path.dirname(os.path.abspath(__file__)); LANES = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
FZ = sys.argv[1] if len(sys.argv) > 1 else os.path.join(LANES, '..', 'core', 'tests', 'tb', 'frozen', '2026-10-24')
def J(p): return json.load(open(p, encoding='utf8'))
P = J(FZ + '/pred-teams.json')['teams']; B = J(FZ + '/sim-bundle.json')
AL = J(os.path.join(LANES, '..', '..', 'work', 'tb1', 'data', 'tb', 'ccg-alive.json')) if os.path.exists(os.path.join(LANES, '..', '..', 'work', 'tb1')) else J(os.path.join(HERE, 'frozen', 'ccg-alive.json'))
NB = J(os.path.join(LANES, 'c', 'data', 'tb', 'needs-by-record.json')); CP = J(os.path.join(LANES, 'p4', 'data', 'tb', 'ccg-paths.json')); PS = J(os.path.join(LANES, 'p4', 'data', 'tb', 'path-by-stage.json'))
for d in (AL, NB, CP, PS): assert d['asof'] == B['as_of'], d['asof']
sys.path.insert(0, os.path.join(LANES, 'c', 'tests', 'tb')); import c_derive as D
fp = D.fmt_pct
idx = {t['g']: i for i, t in enumerate(B['teams']) if 'g' in t}
miss = [x for x in P if x not in idx]; assert not miss, miss[:5]
NM_ = {x: B['teams'][idx[x]]['s'] for x in P}
CONF = {slug: p['cs'] for slug, p in P.items()}
def left_games(i): return [g for g in B['games'] if g['h'] == i or g['a'] == i]
def played(i): return [g for g in B['played'] if g[0] == i or g[1] == i]
def alive_row(slug):
    for code, X in AL['confs'].items():
        for t in X['teams']:
            if t['s'] == slug: return code, X, t
    return None, None, None
PH = {'championship_game': ('Cg', 'the conference championship game'), 'playoff': ('Field', 'the 12-team playoff field'), 'bye': ('Bye', 'a first-round bye')}
TITLE = {'championship_game': '%s: path to the conference championship game', 'playoff': '%s: path to the 12-team playoff field', 'bye': '%s: path to a first-round bye'}
UND = {'championship_game': "%s's path to the conference championship game", 'playoff': "%s's path to the 12-team playoff field", 'bye': "%s's path to a first-round bye"}
def facts(slug, goal):
    p = P[slug]; i = idx[slug]; ind = p['cs'] == 'independents'
    e = {'facts.team.slug': slug, 'facts.team.name': NM_[slug], 'facts.goal': goal, 'facts.ind': ind,
         'facts.game_chance': None if ind else p['c'], 'facts.field_chance': p['p'], 'facts.bye_chance': p['b'], 'facts.left': len(left_games(i)), 'facts.total': len(left_games(i)) + len(played(i)), 'asof.label': D.asof_label()}
    e['facts.now'] = e['facts.game_chance'] if goal == 'championship_game' else p['p'] if goal == 'playoff' else p['b']
    if goal == 'championship_game' and not ind:
        code, X, row = alive_row(slug); assert row, slug
        e['facts.cg.rec'] = {'w': row['w'], 'l': row['l']}; e['facts.cg.left'] = row['left']; e['facts.cg.best'] = {'w': row['best']['w'], 'l': row['best']['l']}
        e['facts.cg.status'] = 'out' if row['st'] == 'out' else ('in' if row.get('sure') is not False else 'tie') if row['st'] == 'in' else 'unknown'
        pe = CP['confs'][code][slug]; assert len(pe['o']) == row['left']
        e['facts.cg.paths'] = True; e['facts.cg.minw'] = pe['m']; e['facts.cg.losses_allowed'] = None if pe['m'] is None else row['left'] - pe['m']
        e['facts.cg.tab'] = [{'wins': k, 'code': pe['t'][k], 'rec': {'w': row['w'] + k, 'l': row['l'] + row['left'] - k}} for k in range(row['left'] + 1)]
        e['facts.cg.exh'] = pe['e'] == 1
        must = []
        for gid in pe['k']:
            g = next(x for x in B['games'] if x['id'] == gid); o = g['a'] if g['h'] == idx[slug] else g['h']
            must.append({'id': gid, 'opp_name': 'FCS opponent' if o == B['fcs'] else B['teams'][o]['s'], 'site': 'neutral' if g.get('neu') else 'home' if g['h'] == idx[slug] else 'away', 'week': g['wk']})
        e['facts.cg.must'] = must
    if goal != 'championship_game':
        R = NB['byrec'][slug]; total = len(left_games(i)) + len(played(i)); recs = []
        for k, n in enumerate(R['n']):
            if n >= NB['seasons'] * 0.01: recs.append({'wins': R['w0'] + k, 'rec': {'w': R['w0'] + k, 'l': total - (R['w0'] + k)}, 'field': R['p'][k] / n, 'bye': R['b'][k] / n, 'share': n / NB['seasons']})
        recs.sort(key=lambda r: -r['wins']); e['facts.by_record'] = recs
        ck = 'bye' if goal == 'bye' else 'field'; asc = sorted(recs, key=lambda r: r['wins'])
        hit = next((r for r in asc if r[ck] >= 0.5), None); lo = next((r for r in asc if r[ck] >= 0.05), None)
        e['facts.cross'] = None if not hit else {'rec': hit['rec'], 'wins': hit['wins'], 'losses': hit['rec']['l']}; e['facts.low_rec'] = None if not lo else {'rec': lo['rec'], 'wins': lo['wins'], 'losses': lo['rec']['l']}
        e['facts.tables'] = True
        S = PS['t'][slug]; ch = []
        for z in (0, 1, 2):
            if S['n'][z] >= PS['seasons'] * 0.01 and (not ind or z == 0): ch.append({'state': z, 'share': None if ind else S['n'][z] / PS['seasons'], 'field': S['p'][z] / S['n'][z], 'bye': S['b'][z] / S['n'][z]})
        e['facts.chain'] = ch; e['facts.win_it'] = None if ind or S['n'][1] + S['n'][2] < PS['seasons'] * 0.01 else S['n'][2] / (S['n'][1] + S['n'][2])
    return e
def contains(slug, goal, focus='overview'):
    p = P[slug]; nm = NM_[slug]; ind = p['cs'] == 'independents'; k = PH[goal][0]
    suffix = {'overview': '', 'min_record': 'Min', 'losses_allowed': 'Loss', 'help': 'Help', 'key_games': 'Key'}[focus]
    c = [TITLE[goal] % nm, 'As of ' + D.asof_label()]
    if goal == 'championship_game' and ind: c += [nm + ' plays as an independent, so it has no conference championship game.']
    elif goal == 'championship_game':
        code, X, row = alive_row(slug); c.append('Conference record %d-%d with' % (row['w'], row['l']))
        c.append({'out': ' is out of the race on our reading of the rules.', 'in': ' is in the race for the conference championship game.'}.get(('out' if row['st'] == 'out' else 'tie' if (row['st'] == 'in' and row.get('sure') is False) else 'in' if row['st'] == 'in' else 'unk'), ' is in the race, but only if a tiebreaker step KickTip cannot see goes its way.' if row['st'] == 'in' else ' is not worked out yet.'))
    else:
        key = 'p' if goal == 'playoff' else 'b'
        c.append(('Estimated chance to make the playoff field: ' if goal == 'playoff' else 'Estimated chance to earn a first-round bye: ') + fp(P[slug][key]))
    return c
def understood(slug, goal, focus):
    nm = NM_[slug]; g = PH[goal][0]
    T = {'Cg': {'overview': "%s's path to the conference championship game", 'min_record': 'the fewest wins %s needs to keep a path to the conference championship game', 'losses_allowed': 'how many games %s can lose and still keep a path to the conference championship game', 'help': 'which other results help %s reach the conference championship game', 'key_games': 'which games %s cannot lose on its path to the conference championship game'}}
    if goal == 'championship_game': return T['Cg'][focus] % nm
    what = 'the 12-team playoff field' if goal == 'playoff' else 'a first-round bye'; verb = 'make the 12-team playoff field' if goal == 'playoff' else 'earn a first-round bye'
    return {'overview': "%s's path to " + what, 'min_record': 'the finishing record that usually works for %s to ' + verb, 'losses_allowed': 'how many games %s can lose and still usually ' + verb, 'help': "%s's path to " + what, 'key_games': "which games matter most for %s's path to " + what}[focus] % nm

run = []; slugs = sorted(P)
for g in ('championship_game', 'playoff', 'bye'):
    for s in slugs:
        run.append({'id': 'TP-RUN-%s-%s' % (s, g), 'params': {'team': s, 'goal': g}, 'expect': facts(s, g), 'render': {'contains': contains(s, g + '' if True else g)}})
for s in ['utah', 'byu', 'arizona', 'indiana', 'ohio-state', 'notre-dame', 'washington-state', 'toledo', 'alabama', 'texas-tech', 'oregon', 'boise-state']:
    for g in ('championship_game', 'playoff', 'bye'):
        for f in ('min_record', 'losses_allowed', 'help', 'key_games'):
            if g != 'championship_game' and f == 'help': continue
            cs = contains(s, g, f)[:1] + ['Understood as: ' + understood(s, g, f) + '.']
            run.append({'id': 'TP-RUN-%s-%s-%s' % (s, g, f), 'params': {'team': s, 'goal': g, 'focus': f}, 'expect': dict(facts(s, g), **{}), 'render': {'contains': cs}})
for r in run:
    r['render']['not_contains'] = [' 0.0%', ' 100.0%', 'undefined']
    if 'focus' not in r['params']: r['render']['contains'].append('Understood as: ' + UND[r['params']['goal']] % NM_[r['params']['team']] + '.')
invalid = [{'id': 'TP-INV-noteam', 'params': {'goal': 'bye'}, 'reason': 'bad_param'}, {'id': 'TP-INV-nogoal', 'params': {'team': 'utah'}, 'reason': 'bad_param'}, {'id': 'TP-INV-badgoal', 'params': {'team': 'utah', 'goal': 'conference'}, 'reason': 'bad_param'},
           {'id': 'TP-INV-badfocus', 'params': {'team': 'utah', 'goal': 'bye', 'focus': 'chances'}, 'reason': 'bad_param'}, {'id': 'TP-INV-badteam', 'params': {'team': 'not-a-team', 'goal': 'bye'}, 'reason': 'bad_param'},
           {'id': 'TP-INV-fcs', 'params': {'team': 'montana-state', 'goal': 'playoff'}, 'reason': 'bad_param'}]
def M(i, t, tool, params, page=None):
    d = {'id': i, 'text': t, 'expect': {'tool': tool, 'params': params}}
    if page: d['page'] = page
    return d
def NM(i, t, page=None):
    d = {'id': i, 'text': t, 'expect': None}
    if page: d['page'] = page
    return d
match = [
 M('TP-M-br04', "What is Utah's path to the conference championship game?", 'team_path', {'team': 'utah', 'goal': 'championship_game'}),
 M('TP-M-br05', 'How can BYU reach the conference championship game?', 'team_path', {'team': 'byu', 'goal': 'championship_game'}),
 M('TP-M-br06', "What is Indiana's path to a first-round bye?", 'team_path', {'team': 'indiana', 'goal': 'bye'}),
 M('TP-M-br07', 'How can Ohio State get into the playoff field?', 'team_path', {'team': 'ohio-state', 'goal': 'playoff'}),
 M('TP-M-br10', 'How many games can Utah lose and still reach the conference championship game?', 'team_path', {'team': 'utah', 'goal': 'championship_game', 'focus': 'losses_allowed'}),
 M('TP-M-road', "What is Arizona's road to the Big 12 championship game?", 'team_path', {'team': 'arizona', 'goal': 'championship_game'}),
 M('TP-M-minrec', "What is Indiana's minimum record to make the playoff?", 'team_path', {'team': 'indiana', 'goal': 'playoff', 'focus': 'min_record'}),
 M('TP-M-fewest', 'What is the fewest wins Utah can have and still reach the conference championship game?', 'team_path', {'team': 'utah', 'goal': 'championship_game', 'focus': 'min_record'}),
 M('TP-M-afford', 'How many games can Oregon afford to lose and still make the playoff?', 'team_path', {'team': 'oregon', 'goal': 'playoff', 'focus': 'losses_allowed'}),
 M('TP-M-usu', "What is Utah State's path to the conference championship game?", 'team_path', {'team': 'utah-state', 'goal': 'championship_game'}),
 M('TP-M-usu2', "What is USU's path to a bye?", 'team_path', {'team': 'utah-state', 'goal': 'bye'}),
 M('TP-M-theu', "What is the U's path to a bye?", 'team_path', {'team': 'utah', 'goal': 'bye'}),
 M('TP-M-utes', 'How can the Utes reach the conference championship game?', 'team_path', {'team': 'utah', 'goal': 'championship_game'}),
 M('TP-M-nd', "What is Notre Dame's path to a first-round bye?", 'team_path', {'team': 'notre-dame', 'goal': 'bye'}),
 M('TP-M-nogoal', "What is Utah's path?", 'team_path', {'team': 'utah'}),
 M('TP-M-page', 'What is our path to a bye?', 'team_path', {'team': 'byu', 'goal': 'bye'}, {'mode': 'team', 'team': 'byu'}),
 {'id': 'TP-M-state', 'text': "What is State's path to a bye?", 'expect_clarify': {'tool': 'team_path', 'param': 'team', 'options': ['utah-state', 'ohio-state', 'michigan-state']}},
 {'id': 'TP-M-tech', 'text': "What is Tech's path to the playoff?", 'expect_clarify': {'tool': 'team_path', 'param': 'team', 'options': ['texas-tech', 'georgia-tech', 'virginia-tech']}},
 {'id': 'TP-M-aggies', 'text': "What is the Aggies path to a bye?", 'expect_clarify': {'tool': 'team_path', 'param': 'team', 'options': ['new-mexico-state', 'texas-a-m', 'utah-state']}},
 NM('TP-M-near-need', 'What does Arizona need to reach the conference championship game?'), NM('TP-M-near-need2', 'How can Utah reach the conference championship game, and what does it need?'),
 NM('TP-M-near-needpath', 'What does BYU need to do on its path to the playoff?'), NM('TP-M-near-wins', 'How many wins does Utah need?'), NM('TP-M-near-happen', 'What has to happen for Indiana to make the playoff?'),
 NM('TP-M-near-title', 'How can Utah win the Big 12?'), NM('TP-M-near-whatif', 'What if Utah loses to BYU, what is its path to the playoff?'), NM('TP-M-near-two', "What are Utah and BYU's paths to the playoff?"),
 NM('TP-M-near-clinch', 'Can Indiana still reach the playoff or has it been eliminated?'), NM('TP-M-near-sport', "What is Utah's path to the basketball tournament?"), NM('TP-M-near-nonfbs', "What is Montana State's path to the playoff?"),
 NM('TP-M-near-sched', "What is Utah's schedule?"), NM('TP-M-near-chance', 'What are the chances Utah makes the playoff?'), NM('TP-M-near-past', "What was Indiana's path to the playoff in 2019?"),
 NM('TP-M-near-bet', 'What is a safe bet for Utah to make the playoff?'), NM('TP-M-near-standings', 'Big 12 standings'), NM('TP-M-near-compare', "Compare Utah's and Arizona's path to a bye."),
]
json.dump({'tool': 'team_path', 'schema': 1, 'frozen': '2026-10-24', 'run': run, 'invalid': invalid, 'match': match}, open(os.path.join(HERE, 'team_path.test.json'), 'w'), indent=1)
print('team_path: run %d invalid %d match %d' % (len(run), len(invalid), len(match)))

# ---------------------------------------------------------------- path_compare
PCT = {'championship_game': 'Estimated chance to reach the conference championship game', 'playoff': 'Estimated chance to make the playoff field', 'bye': 'Estimated chance to earn a first-round bye'}
pairs = [('utah', 'arizona'), ('byu', 'utah'), ('indiana', 'ohio-state'), ('notre-dame', 'utah'), ('washington-state', 'toledo'), ('alabama', 'georgia'), ('texas-tech', 'oklahoma'), ('boise-state', 'utah-state'), ('oregon', 'washington'), ('miami-fl', 'notre-dame')]
pairs = [(a, b) for a, b in pairs if a in P and b in P]
prun = []
for a, b in pairs:
    for g in ('championship_game', 'playoff', 'bye'):
        ex = {'facts.goal': g, 'facts.teams.0.team.slug': a, 'facts.teams.1.team.slug': b, 'facts.teams.0.team.name': NM_[a], 'facts.teams.1.team.name': NM_[b], 'asof.label': D.asof_label()}
        fa, fb = facts(a, g), facts(b, g)
        for k in ('now', 'game_chance', 'field_chance', 'bye_chance', 'left', 'ind'): ex['facts.teams.0.' + k] = fa['facts.' + k]; ex['facts.teams.1.' + k] = fb['facts.' + k]
        for k in ('cg.rec', 'cg.left', 'cg.status', 'cg.minw', 'cg.losses_allowed'):
            if 'facts.' + k in fa: ex['facts.teams.0.' + k] = fa['facts.' + k]
            if 'facts.' + k in fb: ex['facts.teams.1.' + k] = fb['facts.' + k]
        for k in ('cross', 'low_rec'):
            if 'facts.' + k in fa: ex['facts.teams.0.' + k] = fa['facts.' + k]
            if 'facts.' + k in fb: ex['facts.teams.1.' + k] = fb['facts.' + k]
        ia, ib = idx[a], idx[b]; mt = next((x for x in B['games'] if {x['h'], x['a']} == {ia, ib}), None)
        ex['facts.meet'] = None if not mt else {'id': mt['id'], 'week': mt['wk']}
        pk = {'championship_game': 'c', 'playoff': 'p', 'bye': 'b'}[g]
        cs = [(TITLE[g] % ('%s and %s' % (NM_[a], NM_[b]))).replace(': path to', ': path to'), PCT[g], 'Measure']
        if g != 'championship_game': cs += [fp(P[a][pk]), fp(P[b][pk])]
        else:
            if P[a]['c'] is not None: cs.append(fp(P[a]['c']))
            if P[b]['c'] is not None: cs.append(fp(P[b]['c']))
        if mt: cs.append('play each other in week %d' % mt['wk'])
        prun.append({'id': 'PC-RUN-%s-%s-%s' % (a, b, g), 'params': {'teams': [a, b], 'goal': g}, 'expect': ex, 'render': {'contains': cs, 'not_contains': [' 0.0%', ' 100.0%', 'undefined']}})
pinv = [{'id': 'PC-INV-one', 'params': {'teams': ['utah'], 'goal': 'bye'}, 'reason': 'bad_param'}, {'id': 'PC-INV-same', 'params': {'teams': ['utah', 'utah'], 'goal': 'bye'}, 'reason': 'bad_param'},
        {'id': 'PC-INV-nogoal', 'params': {'teams': ['utah', 'byu']}, 'reason': 'bad_param'}, {'id': 'PC-INV-badgoal', 'params': {'teams': ['utah', 'byu'], 'goal': 'conference'}, 'reason': 'bad_param'}, {'id': 'PC-INV-three', 'params': {'teams': ['utah', 'byu', 'arizona'], 'goal': 'bye'}, 'reason': 'bad_param'},
        {'id': 'PC-INV-fcs', 'params': {'teams': ['utah', 'montana-state'], 'goal': 'bye'}, 'reason': 'bad_param'}]
pm = [
 M('PC-M-br12', "Compare Utah's and Arizona's path to a bye.", 'path_compare', {'teams': ['utah', 'arizona'], 'goal': 'bye'}),
 M('PC-M-easier', 'Who has the easier path to the conference championship game, BYU or Utah?', 'path_compare', {'teams': ['byu', 'utah'], 'goal': 'championship_game'}),
 M('PC-M-playoff', 'Compare Indiana and Ohio State on the path to the playoff field.', 'path_compare', {'teams': ['indiana', 'ohio-state'], 'goal': 'playoff'}),
 M('PC-M-vs', 'Utah vs BYU path to the conference championship game', 'path_compare', {'teams': ['utah', 'byu'], 'goal': 'championship_game'}),
 M('PC-M-nogoal', "Compare Utah's and BYU's path", 'path_compare', {'teams': ['utah', 'byu']}),
 M('PC-M-usu', "Compare Utah State's and Utah's path to the playoff", 'path_compare', {'teams': ['utah-state', 'utah'], 'goal': 'playoff'}),
 NM('PC-M-near-need', 'What do BYU and Utah need to make the playoff?'), NM('PC-M-near-one', "What is Utah's path to a bye?"), NM('PC-M-near-whatif', 'What if Utah beats BYU, compare their path to the playoff'),
 NM('PC-M-near-three', 'Compare the paths of Utah, BYU and Arizona to the playoff'), NM('PC-M-near-chances', 'Compare Utah and BYU chances to make the playoff'), NM('PC-M-near-sport', "Compare Utah's and BYU's path to the basketball tournament"),
 NM('PC-M-near-title', "Compare Utah's and BYU's path to win the Big 12"), NM('PC-M-near-bet', 'Compare Utah and BYU, who is the safer bet for the playoff'),
]
json.dump({'tool': 'path_compare', 'schema': 1, 'frozen': '2026-10-24', 'run': prun, 'invalid': pinv, 'match': pm}, open(os.path.join(HERE, 'path_compare.test.json'), 'w'), indent=1)
print('path_compare: run %d invalid %d match %d' % (len(prun), len(pinv), len(pm)))
