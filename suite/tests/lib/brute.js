/* independent check of the branch engine: enumerate every outcome of the games of the named teams and count, per result of the shared games, the outcomes where each team ends with exactly its remaining-loss count */
module.exports = function (H) {
  const B = H.B;
  const tg = (t) => B.games.filter((g) => g.h === t || g.a === t);
  function remLosses(it) { // single-team resolve gives the same number the branch engine starts from
    if (it.scope !== 'total') return it.losses;
    const r = H.KS.resolve({ intent: 'scenario', items: [it] }, B); return r.echo[0].rem_losses;
  }
  function count(items) {
    const teams = items.map((it) => it.team), need = items.map(remLosses), gm = {}; teams.forEach((t) => tg(t).forEach((g) => { gm[g.id] = g; }));
    const ids = Object.keys(gm), n = ids.length, idx = {}; ids.forEach((id, i) => { idx[id] = i; });
    if (n > 24) throw new Error('too many games to enumerate: ' + n);
    const shared = ids.filter((id) => teams.indexOf(gm[id].h) >= 0 && teams.indexOf(gm[id].a) >= 0);
    const mine = teams.map((t) => tg(t).map((g) => ({ i: idx[g.id], home: g.h === t })));
    const out = {};
    for (let m = 0; m < (1 << n); m++) {
      let ok = true;
      for (let k = 0; k < teams.length && ok; k++) { let l = 0; mine[k].forEach((x) => { const hw = (m >> x.i) & 1; if (x.home ? !hw : hw) l++; }); if (l !== need[k]) ok = false; }
      if (!ok) continue;
      const key = shared.map((id) => id + ':' + (((m >> idx[id]) & 1) ? gm[id].h : gm[id].a)).join('|'); out[key] = (out[key] || 0) + 1;
    }
    return { by: out, shared, need };
  }
  const nCk = (n, k) => { let r = 1; for (let i = 1; i <= k; i++) r = r * (n - k + i) / i; return Math.round(r); };
  const waysOf = (br) => br.res.constraints.reduce((a, c) => a * nCk(c.games.length, c.wins), 1);
  return { count, waysOf, remLosses, tg };
};
