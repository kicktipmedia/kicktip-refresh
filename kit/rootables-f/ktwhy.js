/* Rootables rev c: ONE why source for team page, home and share card. '<data fact>, so <what the result does for the viewing team>'.
   Inputs (all from the build): pred-teams.json (teams[slug].n/cs/cn/p, field), sim-bundle.json (teams[i].g/cs, played [h,a,hs,as,wk]),
   and the compute() row (race, root, other, h, a, pP/pC per-mille [ifHomeWins, ifAwayWins] for the viewing team). Returns {text, src}. */
(function (root) {
  function an(nm) { nm = String(nm || ''); var v = /^[A-Z]{2,}\b/.test(nm) ? /^[AEFHILMNORSX]/.test(nm) : /^[AEIO]/.test(nm); return (v ? 'an ' : 'a ') + nm; }
  function poss(nm) { return /s$/.test(nm) ? nm + '\u2019' : nm + '\u2019s'; }
  function NUM(n) { return ['no', 'one', 'two', 'three', 'four', 'five'][n] || String(n); }
  function pct(pm) { return Math.round(pm / 10) + '%'; }
  function pair(a, b) { if (Math.round(a / 10) === Math.round(b / 10)) return [(a / 10).toFixed(1) + '%', (b / 10).toFixed(1) + '%']; return [pct(a), pct(b)]; }
  function records(B) {   /* overall and conference W-L from sim-bundle.played (conference = both teams share cs) */
    var R = {}; (B.played || []).forEach(function (g) { var h = B.teams[g[0]], a = B.teams[g[1]], hw = g[2] > g[3];
      [[h, a, hw], [a, h, !hw]].forEach(function (x) { var t = x[0], o = x[1]; if (!t || !t.g) return; var r = R[t.g] = R[t.g] || { w: 0, l: 0, cw: 0, cl: 0, vs: {} };
        if (x[2]) r.w++; else r.l++; if (o && o.cs && o.cs === t.cs) { if (x[2]) r.cw++; else r.cl++; } if (o && o.g) r.vs[o.g] = x[2] ? 'W' : 'L'; }); });
    return R; }
  function why(o) {   /* o: {s: viewing slug, sn, row, rootSlug, otherSlug, rootName, otherName, T, F, B, R (records, optional)} */
    var T = o.T || {}, F = o.F || [], R = o.R || records(o.B), r = o.row, S = T[o.s] || {}, sn = o.sn || S.n, xn = o.otherName, x = o.otherSlug, a = o.rootSlug;
    var rs = R[o.s] || { w: 0, l: 0, cw: 0, cl: 0, vs: {} }, rx = R[x] || { w: 0, l: 0, cw: 0, cl: 0, vs: {} }, X = T[x] || {}, src = {};
    var rootHome = r.root === r.h, iRoot = rootHome ? 0 : 1, iOther = 1 - iRoot;
    var P = r.race === 'ccg' ? r.pC : r.pP, pr = pair(P[iOther], P[iRoot]);   /* viewing team's chance if the other side wins -> if the root side wins */
    src.chance = (r.race === 'ccg' ? 'whatif pC' : 'whatif pP') + ' [' + P.join(',') + '] per-mille; other wins ' + P[iOther] + ', root wins ' + P[iRoot];
    var move = pr[0] + ' to ' + pr[1];
    function pos(sl) { for (var i = 0; i < F.length; i++) if (F[i][0] === sl) return i + 1; return 0; }
    function rankP(sl) { var p = T[sl] && T[sl].p, k = 1; if (p == null) return 0; for (var q in T) if (T[q].p > p) k++; return k; }
    var text;
    if (r.race === 'ccg') {
      var conf = S.cn || 'conference', same = X.cs && X.cs === S.cs;
      if (same) {
        src.records = xn + ' ' + rx.cw + '-' + rx.cl + ' conf, ' + sn + ' ' + rs.cw + '-' + rs.cl + ' conf (sim-bundle.played, same cs)';
        var d = rx.cl - rs.cl, rel = d < 0 ? (-d === 1 ? 'one loss fewer than ' : (-d) + ' losses fewer than ') + sn + ' (' + rs.cw + '-' + rs.cl + ')' : d === 0 ? 'with the same ' + (rs.cl === 0 ? 'unbeaten ' + conf + ' record' : NUM(rs.cl) + ' ' + conf + ' loss' + (rs.cl === 1 ? '' : 'es')) + ' as ' + sn + ' (' + rs.cw + '-' + rs.cl + ')' : (d === 1 ? 'one loss behind ' : d + ' losses behind ') + sn + ' (' + rs.cw + '-' + rs.cl + ')';
        var fact = xn + ' is ' + rx.cw + '-' + rx.cl + ' in the ' + conf + ', ' + rel;
        var so = d <= 0 ? 'so ' + an(xn) + ' loss clears ' + poss(sn) + ' path to the championship game (' + move + ')'
               : d === 1 ? 'so a loss keeps ' + xn + ' from closing on ' + sn + ' (championship\u2011game chance ' + move + ')'
                         : 'so ' + an(xn) + ' loss still moves ' + poss(sn) + ' championship\u2011game chance from ' + move;
        text = fact + ', ' + so + '.';
      } else { src.records = xn + ' ' + rx.w + '-' + rx.l + ' overall'; text = xn + ' is ' + rx.w + '-' + rx.l + ', so ' + an(xn) + ' loss moves ' + poss(sn) + ' chance to reach the ' + conf + ' championship game from ' + move + '.'; }
    } else {
      var px = pos(x), rk = px ? 0 : rankP(x);
      src.records = xn + ' ' + rx.w + '-' + rx.l + ' overall (sim-bundle.played)';
      if (px) { src.field = 'pred-teams.field position ' + px; text = rx.w + '-' + rx.l + ' ' + xn + ' is No. ' + px + ' in KickTip\u2019s projected 12-team field, so ' + an(xn) + ' loss can open a spot and moves ' + poss(sn) + ' playoff chance from ' + move + '.'; }
      else if (rk && rk <= 16) { src.field = 'not in pred-teams.field; playoff-chance rank ' + rk + ' (pred-teams.p ' + X.p + ') <= 16'; text = rx.w + '-' + rx.l + ' ' + xn + ' is just outside KickTip\u2019s projected 12-team field, so ' + an(xn) + ' loss keeps ' + xn + ' out of a spot (' + poss(sn) + ' playoff chance ' + move + ').'; }
      else if (rs.vs[a]) { var res = rs.vs[a] === 'W' ? 'beat ' : 'lost to '; var rr = R[a] || { w: 0, l: 0 }; src.played = sn + ' ' + rs.vs[a] + ' vs ' + o.rootName + ' (sim-bundle.played); ' + o.rootName + ' ' + rr.w + '-' + rr.l;
        text = sn + ' ' + res + rr.w + '-' + rr.l + ' ' + o.rootName + ' this season, so ' + an(o.rootName) + ' win moves ' + poss(sn) + ' playoff chance from ' + move + '.';   /* rev d: data-only */ }
      else { text = xn + ' is ' + rx.w + '-' + rx.l + ', so ' + an(xn) + ' loss moves ' + poss(sn) + ' playoff chance from ' + move + '.'; }
    }
    return { text: text, src: src };
  }
  var api = { why: why, records: records };
  if (typeof module !== 'undefined' && module.exports) module.exports = api; else root.KTWhyC = api;
})(this);
