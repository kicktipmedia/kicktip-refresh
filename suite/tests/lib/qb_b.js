/* shared by the generator and the checker of qbank_scn_b: the observable summary of one question on the B tree (page path: resolve with {branches:true}, then buildBranched / build) */
module.exports = function (H) {
  const EX = H.EX, B = H.B;
  return function summarize(q) {
    const p = H.KP.parse(q, B.aliases, { choices: {} });
    if (p.refusal) return { kind: 'refusal' };
    if (p.clarify) return { kind: 'parse_clarify', reason: p.clarify_reason };
    const res = H.KS.resolve(p, B, { branches: true });
    if (!res.ok) return { kind: 'clarify', reason: res.clarify.reason };
    const o = { parsed: p, res, bundle: B, ccg: H.ccg, rules: H.rules, KTCcg: H.KTCcg, itemText: (it) => it.kind };
    if (res.branches) {
      const f = EX.buildBranched(o);
      if (f.ok === false) return { kind: 'nocard', reason: f.reason };
      const txt = EX.lines(f).join('\n');
      return { kind: 'branched', title: EX.title(f), conference: f.conference.name, teams: f.scenario.teams, status: f.status,
        gb: f.game_branches.map((g, i) => ({ label: g.label, imp: g.impossible ? g.impossible.text : null, fam: f.branches.filter((x) => x.gb === i).length })),
        ascii: !/[^\x00-\x7f]/.test(txt) };
    }
    const f = EX.build(o);
    if (f.ok === false) return { kind: 'nocard', reason: f.reason };
    return { kind: 'card', title: EX.title(f), status: f.status, branches: f.branches.length, game_branches: f.game_branches === undefined };
  };
};
