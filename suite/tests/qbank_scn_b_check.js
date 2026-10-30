/* replays tests/qbank_scn_b.json on a tree: recorded summary equal, branched rows' ways re-checked by brute force, text ASCII + no banned word. usage: node tests/qbank_scn_b_check.js TREE_B */
const path = require('path'), H = require('./lib/scn_harness.js')(path.resolve(process.argv[2])), S = require('./lib/qb_b.js')(H), BR = require('./lib/brute.js')(H), rows = require('./qbank_scn_b.json').rows;
let n = 0, bad = 0; const ck = (ok, w, x) => { n++; if (!ok) { bad++; console.log('FAIL ' + w + (x ? ' :: ' + JSON.stringify(x).slice(0, 400) : '')); } else console.log('PASS ' + w); };
for (const r of rows) {
  const e = S(r.text), want = Object.assign({ kind: r.kind }, r.expect); delete want.ways; delete want.ways_unchecked;
  const sd = (x) => JSON.stringify(x, (k, v) => (k === 'status' || k === 'branches') ? undefined : v), sts = [].concat(e).filter(z => z && typeof z === 'object' && 'status' in z);
  ck(sts.every(z => ['settled', 'partial', 'impossible', 'open'].includes(z.status) && (z.branches === undefined || z.branches >= 1)), r.id + ' data fields consistent (status/branches follow live results)', e);
  ck(sd(e) === sd(want), r.id + ' ' + r.kind + ': ' + r.text, [e, want]);
  if (r.kind === 'branched') {
    const p = H.KP.parse(r.text, H.B.aliases, { choices: {} }), res = H.KS.resolve(p, H.B, { branches: true }), f = H.EX.buildBranched({ parsed: p, res, bundle: H.B, ccg: H.ccg, rules: H.rules, KTCcg: H.KTCcg, itemText: (it) => it.kind });
    const t = H.EX.lines(f).join('\n'); ck(!/\bCCG\b|title game|\bbets?\b|wager|spread|parlay|the 12(?!-)\b|\bclinch|eliminated/i.test(t), r.id + ' text has no banned word');
    if (r.expect.ways) { const c = BR.count(p.items); ck(res.branches.every((b, k) => { const key = res.shared.map((id) => id + ':' + b.shared.filter((z) => z.game === id)[0].winner).join('|'); return (b.impossible ? 0 : BR.waysOf(b)) === (c.by[key] || 0) && (r.expect.ways[k] || 0) === (c.by[key] || 0); }), r.id + ' every branch matches brute-force enumeration'); }
  }
}
console.log(n + ' checks, ' + bad + ' failed'); process.exit(bad ? 1 : 0);
