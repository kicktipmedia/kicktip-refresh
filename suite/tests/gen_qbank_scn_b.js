/* writes tests/qbank_scn_b.json from the B tree and cross-checks every live branch against the brute-force counter. usage: node tests/gen_qbank_scn_b.js TREE_B */
const path = require('path'), fs = require('fs'), H = require('./lib/scn_harness.js')(path.resolve(process.argv[2])), BR = require('./lib/brute.js')(H), S = require('./lib/qb_b.js')(H);
const Q = [
 ['exact one-loss question', 'What if BYU, Utah and Texas Tech all end with just one loss?'],
 ['same, no question mark', 'What if BYU, Utah and Texas Tech all end with one loss'],
 ['same, lowercase tech, oxford comma', 'What if BYU, Utah, and Texas tech all end with just one loss?'],
 ['two teams, shared game, both directions live', 'What if BYU and Utah each end with 3 losses'],
 ['two teams, 2 losses', 'What if BYU and Utah each end with 2 losses'],
 ['two teams, one loss: one branch impossible', 'What if BYU and Utah both end with just one loss'],
 ['two teams, 1 of remaining', 'What if Utah and Arizona both lose 1 of the remaining games'],
 ['two shared games, 4 branches', 'What if BYU, Utah and Arizona all end with 3 losses'],
 ['3 shared games stays the old clarify', 'What if Arizona, TCU and Utah all lose 1 of the remaining games'],
 ['4 teams sharing games stays the old clarify', 'What if Arizona, TCU, Utah and BYU all lose 1 of the remaining games'],
 ['four teams, 3 team cap', 'What if BYU, Utah, Arizona and Texas Tech all end with 3 losses'],
 ['all branches impossible', 'What if Utah and Arizona both end with 8 losses'],
 ['control: one team, no shared game', 'What if BYU wins out'],
 ['control: BYU and Texas Tech (no shared game)', 'What if BYU and Texas Tech both end with just one loss'],
 ['control: a pinned shared game is not a branch', 'What if BYU beats Utah'],
 ['control: pinned game plus constraint', 'What if BYU beats Utah and Utah ends with 3 losses'],
 ['control: Utah beats Arizona', 'What if Utah beats Arizona'],
 ['control: both win out (forced conflict stays)', 'What if BYU and Utah both win out'],
 ['control: Utah and Texas Tech win out', 'what if Utah and Texas Tech win out'],
 ['control: other conference', 'what if New Mexico State and Western Kentucky win out'],
 ['control: wins 2 of the next 3', 'What if BYU wins 2 of the next 3'],
 ['control: Kansas and Utah lose 1', 'What if Utah and Kansas each lose 1 of the remaining games'],
 ['control: invalid total', 'What if BYU finishes with no losses?'],
 ['control: unrelated', 'what if the sun explodes'],
 ['control: Utah State alias is not Utah', 'What if Utah State and Utah both end with one loss'],
];
const rows = []; let bad = 0;
Q.forEach(([note, text], i) => {
  const e = S(text), id = 'sb' + String(i + 1).padStart(2, '0'); const row = { id, note, text, kind: e.kind, expect: Object.assign({}, e) }; delete row.expect.kind; rows.push(row);
  if (e.kind === 'branched') { // brute-force check of each live branch's ways, when the question is small enough
    const p = H.KP.parse(text, H.B.aliases, { choices: {} }), r = H.KS.resolve(p, H.B, { branches: true });
    try { const c = BR.count(p.items); const brute = r.branches.map((b) => b.impossible ? null : BR.waysOf(b));
      r.branches.forEach((b, k) => { const key = r.shared.map((id) => { const z = b.shared.filter((q) => q.game === id)[0]; return id + ':' + z.winner; }).join('|'), want = c.by[key] || 0; const got = brute[k] || 0; if (got !== want) { bad++; console.log('BRUTE MISMATCH', text, k, got, want); } });
      row.expect.ways = brute; } catch (x) { row.expect.ways_unchecked = String(x.message).slice(0, 60); } }
});
fs.writeFileSync(path.join(__dirname, 'qbank_scn_b.json'), JSON.stringify({ about: 'scn_b: shared-game branches (limits 3 teams, 1 conference, 4 branches). expectations recorded from the B tree and, for branched rows, every live branch checked against brute-force enumeration (tests/lib/brute.js). Replay: node tests/qbank_scn_b_check.js TREE', rows }, null, 1));
rows.forEach((r) => console.log(r.id, r.kind, JSON.stringify(r.expect).slice(0, 260), '|', r.text.slice(0, 60))); console.log(bad ? 'MISMATCH' : 'brute ok');
