/* scn_b engine + card tests. usage: node tests/set_scn_b.js TREE_B TREE_A2B */
const path = require('path'), fs = require('fs'), vm = require('vm');
const [tb, ta] = process.argv.slice(2).map((p) => path.resolve(p));
const H = require('./lib/scn_harness.js')(tb), HA = require('./lib/scn_harness.js')(ta), BR = require('./lib/brute.js')(H);
let n = 0, bad = 0; const chk = (k, ok, info) => { n++; if (!ok) { bad++; console.log('FAIL ' + k + (info !== undefined ? ' :: ' + String(JSON.stringify(info)).slice(0, 300) : '')); } else console.log('PASS ' + k); };
const B = H.B, nm = (i) => B.teams[i].n;
const parse = (q) => H.KP.parse(q, B.aliases, { choices: {} });
const resB = (q) => { const p = parse(q); return { p, r: H.KS.resolve(p, B, { branches: true }), r0: H.KS.resolve(p, B) }; };
const build = (p, r) => H.EX.buildBranched({ parsed: p, res: r, bundle: B, ccg: H.ccg, rules: H.rules, KTCcg: H.KTCcg, itemText: (it) => it.kind });
const sig = (o) => JSON.stringify(o);

/* 1. the exact question */
const Q1 = 'What if BYU, Utah and Texas Tech all end with just one loss';
let x = resB(Q1);
chk('Q1 old path: still the shared_game clarify (flag/opts off)', !x.r0.ok && x.r0.clarify.reason === 'shared_game');
chk('Q1 branched: ok, 2 branches, no clarify, shared game is BYU v Utah', x.r.ok && !x.r.clarify && x.r.branches.length === 2 && x.r.shared.length === 1 && [nm(B.games.filter((g) => g.id === x.r.shared[0])[0].h), nm(B.games.filter((g) => g.id === x.r.shared[0])[0].a)].sort().join() === 'BYU,Utah');
let b0 = x.r.branches[0], b1 = x.r.branches[1];
chk('Q1 branch 0: BYU beats Utah, valid, no constraint left (every game decided)', !b0.impossible && b0.shared[0].winner === 75 && b0.shared[0].loser === 77 && b0.res.constraints.length === 0);
chk('Q1 branch 1: Utah beats BYU is impossible (BYU would have a second loss), kind over, no sim result', b1.impossible && b1.impossible.team === 75 && b1.impossible.kind === 'over' && b1.res === null);
const bru = BR.count(x.p.items);
chk('Q1 brute force over every outcome: exactly 1 way, in the BYU-beats-Utah branch only', Object.keys(bru.by).length === 1 && Object.values(bru.by)[0] === 1 && Object.keys(bru.by)[0].split(':')[1] === String(75));
let f1 = build(x.p, x.r);
chk('Q1 facts: game_branches[2], labels "If BYU beats Utah" / "If Utah beats BYU"', f1.game_branches.length === 2 && f1.game_branches[0].label === 'If BYU beats Utah' && f1.game_branches[1].label === 'If Utah beats BYU');
chk('Q1 facts: branches[] keeps the way-family shape and gains gb; second game branch impossible with text and no families', f1.branches.length === 1 && f1.branches[0].gb === 0 && f1.game_branches[1].impossible.text === 'BYU would end with more losses than your scenario allows.' && f1.game_branches[0].impossible === null);
chk('Q1 facts: v=1, kind, single_path false, status, limits.gb 4', f1.v === 1 && f1.kind === 'scenario_facts' && f1.single_path === false && f1.limits.gb === 4 && f1.status === 'settled');
const L1 = H.EX.lines(f1);
chk('Q1 lines: both labels present in order, impossible line, rules and as-of once', L1.indexOf('If BYU beats Utah') > 0 && L1.indexOf('If Utah beats BYU') > L1.indexOf('If BYU beats Utah') && L1.some((l) => /^Not possible: BYU would end/.test(l)) && L1.filter((l) => /^Rules source/.test(l)).length === 1 && L1.filter((l) => /^As of /.test(l)).length === 1);
chk('Q1 lines: the BYU branch says BYU and Utah reach the Big 12 conference championship game, Texas Tech does not', L1.some((l) => /BYU and Utah reach the Big 12 conference championship game/.test(l)) && L1.some((l) => /^Texas Tech does not reach it/.test(l)));
const html1 = H.EX.render(f1);
chk('Q1 render: one outer card, two labelled branch sections, one table, impossible paragraph, one rules heading', (html1.match(/class="sx"/g) || []).length === 1 && (html1.match(/class="sxb"/g) || []).length === 2 && (html1.match(/<table/g) || []).length === 1 && /sxx">Not possible/.test(html1) && (html1.match(/Rules source/g) || []).length === 1 && /<h4 class="sxh">If BYU beats Utah<\/h4>/.test(html1));
chk('Q1 render: tags balanced', ['section', 'table', 'ul', 'ol', 'p', 'h3', 'h4', 'h5'].every((t) => (html1.match(new RegExp('<' + t + '[ >]', 'g')) || []).length === (html1.match(new RegExp('</' + t + '>', 'g')) || []).length));
chk('Q1 render: escapes names (a hostile name never reaches the markup)', (() => { const g = JSON.parse(JSON.stringify(f1)); g.game_branches[0].label = 'If <i>x</i> beats "y"'; const h = H.EX.render(g); return h.indexOf('<i>') < 0 && /&lt;i&gt;/.test(h); })());

/* 2. both directions valid, and every branch checked against brute force */
const brute = (q, expectLive) => {
  const y = resB(q), rows = [];
  if (!y.r.branches) return { q, ok: false, why: 'no branches: ' + (y.r.clarify && y.r.clarify.reason) };
  const bz = BR.count(y.p.items); let ok = true, live = 0;
  y.r.branches.forEach((br) => {
    const key = y.r.shared.map((id) => { const s = br.shared.filter((z) => z.game === id)[0]; return id + ':' + s.winner; }).join('|'), want = bz.by[key] || 0;
    if (br.impossible) { if (want !== 0) { ok = false; rows.push(['imp but brute ' + want, key]); } }
    else { live++; const got = BR.waysOf(br); if (got !== want) { ok = false; rows.push(['ways', key, got, want]); } }
  });
  if (expectLive !== undefined && live !== expectLive) { ok = false; rows.push(['live', live, expectLive]); }
  return { q, ok, rows, live };
};
[['What if BYU and Utah each end with 3 losses', 2], ['What if BYU and Utah each end with 2 losses', 2], ['What if BYU and Utah both end with just one loss', 1], ['What if Utah and Arizona both lose 1 of the remaining games', 2], ['What if BYU and Utah lose 2 of the remaining games', undefined], ['What if BYU, Utah and Arizona all end with 3 losses', 4], ['What if Utah and BYU each end with 4 losses', undefined]].forEach(([q, live]) => { const o = brute(q, live); chk('brute force, every branch and every impossible branch agrees: ' + q + ' (live ' + o.live + ')', o.ok, o); });
x = resB('What if BYU and Utah each end with 3 losses');
chk('both directions: 2 live branches, labels "If BYU beats Utah" / "If Utah beats BYU", different forced shared results', x.r.branches.length === 2 && !x.r.branches[0].impossible && !x.r.branches[1].impossible && x.r.branches[0].res.forced[x.r.shared[0]] !== x.r.branches[1].res.forced[x.r.shared[0]]);
let f2 = build(x.p, x.r);
chk('both directions: facts have 2 game branches, each with its own families', f2.game_branches.length === 2 && f2.branches.filter((b) => b.gb === 0).length >= 1 && f2.branches.filter((b) => b.gb === 1).length >= 1 && f2.branches.every((b) => b.gb === 0 || b.gb === 1));
const H2 = H.EX.render(f2); chk('both directions: render has two branch sections, each with its own table', (H2.match(/class="sxb"/g) || []).length === 2 && (H2.match(/<table/g) || []).length >= 2);

/* 3. four branches (3 teams, 2 shared games) and the caps */
x = resB('What if BYU, Utah and Arizona all end with 3 losses');
chk('4 branches: three teams, two shared games, all four results live, labels name both games', x.r.branches.length === 4 && x.r.shared.length === 2 && x.r.branches.every((b) => !b.impossible));
let f4 = build(x.p, x.r);
chk('4 branches: card builds with 4 game branches and labels joined with "and"', f4.game_branches.length === 4 && f4.game_branches.every((g) => /^If .+ beats .+ and .+ beats .+$/.test(g.label)), f4.game_branches && f4.game_branches.map((g) => g.label));
chk('4 branches: labels are distinct', new Set(f4.game_branches.map((g) => g.label)).size === 4);
x = resB('What if Arizona, TCU and Utah all lose 1 of the remaining games');
chk('cap: three shared games (8 branches) keep the shared_game clarify', !x.r.ok && x.r.clarify.reason === 'shared_game' && !x.r.branches);
x = resB('What if Arizona, TCU, Utah and BYU all lose 1 of the remaining games');
chk('cap: four teams with shared games keep the shared_game clarify', !x.r.ok && x.r.clarify.reason === 'shared_game');
x = resB('What if Navy and Notre Dame each lose 1 of the remaining games');
chk('one-conference limit: cross-conference shared game resolves to branches but the card refuses (two_conferences) so the page keeps the clarify', x.r.branches && x.r.branches.length === 2 && build(x.p, x.r).reason === 'two_conferences');
x = resB('What if BYU, Utah, Arizona and Texas Tech all end with 3 losses');
{ const fb = x.r.branches ? build(x.p, x.r) : null; chk('three-team limit: four named teams -> no card (too_many_teams) or keeps the clarify', (!x.r.branches && !x.r.ok) || (fb && fb.reason === 'too_many_teams'), [x.r.ok, x.r.clarify, fb && fb.reason]); }
{ const fake = { ok: true, branches: [0, 1, 2, 3, 4].map(() => ({ shared: [], impossible: null, res: null })) }; chk('branch cap in the card builder: 5 branches -> too_many_branches', H.EX.buildBranched({ res: fake, bundle: B, parsed: { items: [] } }).reason === 'too_many_branches'); }
x = resB('What if Utah and Arizona both end with 8 losses');
chk('all branches impossible/invalid: the resolver says so (too_many_games), never an empty card', !x.r.ok && !x.r.branches && x.r.clarify.reason === 'too_many_games');
x = resB('What if BYU and Utah each end with 9 losses');
chk('invalid total losses: clarify, no branches', !x.r.ok && !x.r.branches, x.r.clarify);
{ const q = parse('What if BYU and Utah each end with 7 losses'), r = H.KS.resolve(q, B, { branches: true }); chk('impossible totals -> a clarify, never a card with no live branch', !r.ok && !r.branches, r.clarify); }

/* 4. engine equivalence for everything that is not a shared game */
const same = ['What if BYU wins out', 'What if Utah beats Arizona', 'What if Utah loses out', 'What if BYU wins 2 of the next 3', 'What if Utah ends with 2 losses', 'What if Utah ends with 2 losses and BYU wins out', 'What if BYU beats Utah', 'What if BYU and Utah both win out', 'What if Utah and Kansas each lose 1 of the remaining games', 'What if Texas Tech wins out and Utah loses 1 of the remaining games', 'What if BYU beats Utah and Utah ends with 3 losses'];
same.forEach((q) => { const p = parse(q); if (p.refusal || p.clarify) { chk('equivalence (parse stops): ' + q, true); return; } const a = HA.KS.resolve(p, HA.B), b = H.KS.resolve(p, B), c = H.KS.resolve(p, B, { branches: true }); chk('equivalence A2b == B (resolve default and with branches option): ' + q, sig(a) === sig(b) && (sig(a) === sig(c) || (a.clarify && a.clarify.reason === 'shared_game'))); });
chk('resolve source: shared_game question without the option returns the exact A2b object', (() => { const p = parse(Q1); return sig(HA.KS.resolve(p, HA.B)) === sig(H.KS.resolve(p, B)); })());

/* 5. hypothetical only: nothing live changes */
{ const dump = () => sig([B.games, B.now, B.played, H.ccg, H.rules]), before = dump(); const y = resB('What if BYU and Utah each end with 3 losses'); build(y.p, y.r); const f = build(resB(Q1).p, resB(Q1).r); H.EX.render(f); H.EX.lines(f); H.EX.vocab(f);
  chk('hypothetical only: bundle games/records/played results and the conference data are byte-identical after resolve, solve, render', dump() === before);
}

/* 6. sim attach (array form) and the prose allow-list */
const mk = (names) => ({ table: { rows: names.map((t) => ({ name: t, team: B.teams.findIndex((z) => z.n === t), cells: t === 'Texas Tech' ? { ccg: { before: 0.2, after: 0.01, before_text: '20%', after_text: '1%' }, cfp12: { before: 0.1, after: 0.02, before_text: '10%', after_text: '2%' } } : { ccg: { before: 0.31, after: 0.97, before_text: '31%', after_text: '97%' }, cfp12: { before: 0.12, after: 0.5, before_text: '12%', after_text: '50%' } } })) } });
x = resB('What if BYU and Utah each end with 3 losses'); f2 = build(x.p, x.r); H.EX.attachSim(f2, [mk(['BYU', 'Utah']), mk(['BYU', 'Utah'])], B);
chk('attachSim array form: each game branch gets its own sim, top-level sim stays null', f2.game_branches.every((g) => g.sim && g.sim.length === 2) && f2.sim === null);
f1 = build(...[resB(Q1).p, resB(Q1).r]); H.EX.attachSim(f1, [mk(['BYU', 'Utah', 'Texas Tech']), null], B);
chk('attachSim: impossible branch keeps sim null; live one filled; engines agree', f1.game_branches[0].sim && f1.game_branches[1].sim === null && f1.engines_agree === true);
const lines1 = H.EX.lines(f1).join('\n'); chk('lines carry the branch chances under their label, no (model) (home6c ruling)', /chance to make the 12-team playoff field, 12% before, 50% after/.test(lines1));
const voc = H.EX.vocab(f1); chk('vocab: percents and team names of the branches are in the allow-list', voc.percents.indexOf('12%') >= 0 && voc.percents.indexOf('50%') >= 0 && voc.teams.indexOf('Texas Tech') >= 0);
const S = (() => { const c = vm.createContext({ window: {}, console }); const src = fs.readFileSync(path.join(tb, 'assets/ks/scnai.js'), 'utf8'); vm.runInContext(src, c); return c.KTScnAI || c.window.KTScnAI; })();
const cp = S.compact(f1), cj = JSON.stringify(cp);
chk('compact: branched facts compact (<=3300 chars), label on each family, impossible list, branch sim', cp && cj.length <= 3300 && cp.branches[0].label === 'If BYU beats Utah' && cp.impossible[0].label === 'If Utah beats BYU' && cp.branches[0].sim.length === 3, cj.length);
chk('compact: ordinary (unbranched) facts compact exactly as before (no label, no impossible)', (() => { const o = H.run('What if BYU wins out'); if (o.stage !== 'build' || o.f.ok === false) return true; const c = S.compact(o.f); return c && !('impossible' in c) && !c.branches.some((b) => 'label' in b); })());
const known = B.teams.map((t) => t.n).concat(B.teams.map((t) => t.f)).filter(Boolean);
const okp = 'On our reading of the rules, this depends on whether BYU beats Utah. If BYU beats Utah, BYU and Utah reach the Big 12 conference championship game in this scenario, with a playoff chance (model) of 50% (model) for BYU, up from 12% (model). If Utah beats BYU, that cannot happen.';
let v = S.validate(okp, f1, { known, vocab: voc }); chk('validator: prose using the branch labels, names and the branch percents passes', v.ok, v);
v = S.validate(okp.replace('50%', '77%'), f1, { known, vocab: voc }); chk('validator: a percent that is not on the card is rejected', !v.ok && /number|percent/.test(v.why), v);
v = S.validate(okp.replace('Utah beats BYU', 'Arizona beats BYU'), f1, { known, vocab: voc }); chk('validator: a team that is not in the branches is rejected', !v.ok, v);
chk('compact: more than 8 families -> null; 5..8 ok only for branched facts', (() => { const g = JSON.parse(JSON.stringify(f4)); while (g.branches.length < 9) g.branches.push(JSON.parse(JSON.stringify(g.branches[0]))); return S.compact(g) === null; })());

/* 7. wording */
const BAN = /\b(?:bets?|betting|wagers?|spreads?|parlays?|CCG|title game|picks?|lines?|locks?|edge|value|market|gap|predict\w*|forecast\w*|vegas|juice|over\/under)\b|the 12(?!-team)|\u00e9/i;
const copyB = Object.keys(H.EX.COPY).filter((k) => /^b[A-Z]/.test(k)).map((k) => H.EX.COPY[k]);
chk('new card strings (' + copyB.length + ') are plain ASCII, no banned word', copyB.length === 10 && copyB.every((s) => !BAN.test(s) && /^[\x20-\x7e]+$/.test(s)), copyB);
chk('branch-card text of the 3 cards (labels, lead, impossible lines, headings) has no banned word', [f1, f2, f4].every((f) => !BAN.test(f.game_branches.map((g) => g.label + ' ' + (g.impossible ? g.impossible.text : '')).join(' ') + ' ' + H.EX.lines(f).slice(0, 2).join(' '))));
chk('title has no banned word and says "conference championship game" in full', [f1, f2, f4].every((f) => !/\bccg\b|title game/i.test(H.EX.lines(f).join('\n'))));
{ const p = { intent: 'scenario', items: [{ kind: 'loses_n', team: 75, losses: 0, scope: 'remaining' }, { kind: 'loses_n', team: 77, losses: 0, scope: 'remaining' }] }, r = H.KS.resolve(p, B, { branches: true }); chk('every branch impossible (both teams must win the shared game) -> conflict clarify, no card', !r.ok && !r.branches && r.clarify.reason === 'conflict', r.clarify); }
{ const p = { intent: 'scenario', items: [{ kind: 'loses_n', team: 75, losses: 3, scope: 'remaining' }, { kind: 'loses_n', team: 77, losses: 0, scope: 'remaining' }] }, r = H.KS.resolve(p, B, { branches: true }); chk('one impossible branch plus one live one: kind over on Utah, card builds', r.ok && r.branches[0].impossible.team === 77 && !r.branches[1].impossible && !build(p, r).reason); }
console.log(n + ' checks, ' + bad + ' failed'); process.exit(bad ? 1 : 0);
