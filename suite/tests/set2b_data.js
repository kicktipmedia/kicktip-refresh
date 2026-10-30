/* Data-wide checks for schedule_strength, quality_wins and team_compare on a built tree (Node, no network). usage: node tests/set2b_data.js <tree>
 * Every number is recomputed here from the raw data files by independent code and compared with the tool's facts and its rendered card text. */
"use strict";
const path = require("path"), fs = require("fs");
const tree = path.resolve(process.argv[2]);
const T = require("./lib/tbq.js")(tree), TB = T.TB, C = TB.core;
const NEW = ["schedule_strength", "quality_wins", "team_compare"];
let pass = 0, fail = 0; const fails = [];
function ok(c, m, x) { if (c) pass++; else { fail++; if (fails.length < 60) fails.push(m + (x !== undefined ? "  " + String(typeof x === "string" ? x : JSON.stringify(x)).slice(0, 300) : "")); } }
const BANNED = new RegExp(C.BANNED.source + "|\\b(sp\\+|fpi|massey|sagarin|connelly|sos)\\b|:\\/\\/|\\b(clinched|eliminated|locked|guaranteed|favou?rite|difference|differ|agree|better|worse)\\b", "i");
function cardOk(label, a) {
  if (!a.card) return ok(false, label + ": no card", a.r);
  const c = a.card, t = c.text || "";
  ok(!(c.errors && c.errors.length), label + ": card errors", c.errors);
  ok(/estimate/i.test(t), label + ": has 'estimate'"); ok(/As of /.test(t), label + ": has as-of label");
  ok(!BANNED.test(t), label + ": banned wording", (t.match(BANNED) || [])[0]);
  ok(!/Resum\u00e9/i.test(t), label + ": accent on Resume");
  ok(!/\bundefined\b|\bNaN\b|\bnull\b|\[object/.test(t), label + ": undefined/NaN/null in text", t.match(/\bundefined\b|\bNaN\b|\bnull\b|\[object/));
  ok(!/under 0\.0[0-4]|0\.0[0-4]%|100\.0%/.test(t), label + ": raw edge percent", t.match(/under 0\.0[0-4]|0\.0[0-4]%|100\.0%/));
  const dp = TB.card.digitProblems(c, ""); ok(!dp.length, label + ": digit provenance", dp);
  ok(!/\{[a-z0-9_]+\}/i.test(t), label + ": unfilled slot", t.match(/\{[a-z0-9_]+\}/));
}
const sl = (a, b) => (a < b ? -1 : a > b ? 1 : 0);
(async () => {
  const B = T.raw("sim-bundle"), P = T.raw("pred-teams"), S = T.raw("ccg-sim"), POL = T.raw("polls").polls;
  TB.setLive(NEW);
  const F = B.fcs, rt = B.model.rating, nT = B.teams.length;
  const fbs = []; for (let i = 0; i < nT; i++) if (i !== F && B.teams[i].g) fbs.push(i);
  ok(fbs.length === 138, "138 FBS teams", fbs.length);
  /* independent KickTip rank, schedule means, records */
  const order = fbs.slice().sort((a, b) => rt[b] - rt[a] || a - b), kr = {}; order.forEach((t, k) => kr[t] = k + 1);
  const sch = {}; fbs.forEach(i => sch[i] = { played: { s: 0, n: 0, f: 0, o: [] }, remaining: { s: 0, n: 0, f: 0, o: [] } });
  const addS = (t, v, o) => { if (!sch[t]) return; if (o === F || !sch[o]) sch[t][v].f++; else { sch[t][v].s += rt[o]; sch[t][v].n++; sch[t][v].o.push(o); } };
  B.played.forEach(g => { addS(g[0], "played", g[1]); addS(g[1], "played", g[0]); });
  B.games.forEach(g => { addS(g.h, "remaining", g.a); addS(g.a, "remaining", g.h); });
  const rk = { played: {}, remaining: {} };
  ["played", "remaining"].forEach(v => { const l = fbs.filter(t => sch[t][v].n > 0).sort((a, b) => sch[b][v].s / sch[b][v].n - sch[a][v].s / sch[a][v].n || sl(B.teams[a].g, B.teams[b].g)); l.forEach((t, k) => rk[v][t] = k + 1); rk[v].of = l.length; });
  const idx = {}; fbs.forEach(t => idx[B.teams[t].g] = t);
  const fm = (x) => x.toFixed(1);

  /* ---------- schedule_strength: every team x 3 views ---------- */
  let nSS = 0;
  for (const t of fbs) {
    const slug = B.teams[t].g;
    for (const view of ["remaining", "played", "both"]) {
      const a = await T.answer("schedule_strength", { team: slug, view }); nSS++;
      if (!a.r.ok) { ok(false, "schedule_strength " + slug + "/" + view + " refused", a.r); continue; }
      cardOk("schedule_strength " + slug + "/" + view, a);
      const f = a.r.facts;
      for (const v of ["remaining", "played"]) {
        const s = sch[t][v];
        ok(f[v].games === s.n && f[v].fcs === s.f, "ss " + slug + " " + v + " counts", [f[v].games, s.n, f[v].fcs, s.f]);
        if (s.n > 0) { ok(Math.abs(f[v].mean - s.s / s.n) < 1e-9, "ss " + slug + " " + v + " mean"); ok(f[v].rank === rk[v][t] && f[v].of === rk[v].of, "ss " + slug + " " + v + " rank", [f[v].rank, rk[v][t]]); }
        else ok(f[v].mean === null && f[v].rank === null, "ss " + slug + " " + v + " no FBS games -> null mean and rank");
        ok(f.opps[v].length === s.n, "ss " + slug + " " + v + " opponent rows", f.opps[v].length);
        ok(f.opps[v].every((o, i, l) => (i === 0 || l[i - 1].rank <= o.rank) && o.rank === kr[idx[o.slug]] && o.rating === rt[idx[o.slug]]), "ss " + slug + " " + v + " opponent rows sorted by KickTip rank, ranks and ratings from the data");
      }
      const txt = a.card.text;
      if (sch[t].remaining.n > 0 && view !== "played") ok(txt.indexOf(fm(sch[t].remaining.s / sch[t].remaining.n)) >= 0, "ss " + slug + " card prints the remaining mean " + fm(sch[t].remaining.s / sch[t].remaining.n));
      if (sch[t].played.n > 0 && view !== "remaining") ok(txt.indexOf(fm(sch[t].played.s / sch[t].played.n)) >= 0, "ss " + slug + " card prints the played mean");
      ok(/FCS opponents are not counted/.test(txt), "ss " + slug + " FCS note");
      if (sch[t].remaining.f > 0) ok(/FCS games left, not counted/.test(txt), "ss " + slug + " FCS-left note");
      if (sch[t].remaining.n + sch[t].remaining.f === 0 && view !== "played") ok(/No games left\./.test(txt), "ss " + slug + " empty remaining note");
    }
  }
  console.log("schedule_strength team cards:", nSS);
  const noLeft = fbs.filter(t => sch[t].remaining.n + sch[t].remaining.f === 0).length, fcsRem = fbs.filter(t => sch[t].remaining.f > 0).length, fcsPl = fbs.filter(t => sch[t].played.f > 0).length;
  console.log("  teams with no games left:", noLeft, "| with an FCS game left:", fcsRem, "| with an FCS game played:", fcsPl);
  ok(fcsPl > 0, "data has FCS games played (so the FCS path is exercised)");
  /* conferences incl. independents, both views */
  const confs = {}; fbs.forEach(t => { (confs[B.teams[t].c] = confs[B.teams[t].c] || []).push(t); });
  const confIds = Object.keys(confs); console.log("conference ids in data:", confIds.join(","));
  for (const c of confIds) for (const view of ["remaining", "played"]) {
    const a = await T.answer("schedule_strength", { conference: c, view });
    if (!a.r.ok) { ok(false, "ss conf " + c + " refused", a.r); continue; }
    cardOk("schedule_strength conf " + c + "/" + view, a);
    const f = a.r.facts;
    ok(f.rows.length === confs[c].length, "ss conf " + c + " " + view + " row count = members", [f.rows.length, confs[c].length]);
    ok(f.rows.every((r, i, l) => (r.rank === null ? 1e9 : r.rank) >= (i ? (l[i - 1].rank === null ? 1e9 : l[i - 1].rank) : 0)), "ss conf " + c + " sorted toughest first");
    ok(f.rows.every(r => { const t = idx[r.slug]; return r.games === sch[t][view].n && (r.rank === null ? sch[t][view].n === 0 : r.rank === rk[view][t] && Math.abs(r.mean - sch[t][view].s / sch[t][view].n) < 1e-9); }), "ss conf " + c + " " + view + " rows equal recomputation");
    ok(a.card.text.indexOf(fm(f.rows.filter(r => r.mean !== null)[0].mean)) >= 0, "ss conf " + c + " card prints the toughest mean");
    if (c === "ind") ok(/Independent teams are listed together/.test(a.card.text), "ss independents note");
  }
  /* national lists */
  for (const view of ["remaining", "played"]) for (const ord of ["toughest", "easiest"]) for (let n = 1; n <= 10; n++) {
    const a = await T.answer("schedule_strength", { view, order: ord, n }); if (!a.r.ok) { ok(false, "ss national refused", a.r); continue; }
    const l = fbs.filter(t => sch[t][view].n > 0).sort((x, y) => ord === "toughest" ? rk[view][x] - rk[view][y] : rk[view][y] - rk[view][x]).slice(0, n);
    ok(JSON.stringify(a.r.facts.rows.map(r => r.slug)) === JSON.stringify(l.map(t => B.teams[t].g)), "ss national " + view + "/" + ord + "/" + n + " order equals recomputation", a.r.facts.rows.map(r => r.slug));
    if (n === 1 || n === 10) cardOk("schedule_strength national " + view + "/" + ord + "/" + n, a);
  }
  /* bad params */
  ok((await T.run("schedule_strength", { team: "utah", conference: "big12" })).reason === "bad_param", "ss team + conference -> bad_param");
  ok((await T.run("schedule_strength", { conference: "big12", view: "both" })).reason === "not_applicable", "ss list + view both -> not_applicable");
  ok(!(await T.run("schedule_strength", { team: "not-a-team" })).ok, "ss unknown team refused");
  ok(!(await T.run("schedule_strength", { n: 11 })).ok, "ss n=11 refused");

  /* ---------- quality_wins ---------- */
  const rec = {}; fbs.forEach(t => rec[t] = { wins: [], losses: [], fcsw: 0 });
  B.played.forEach((g, n) => {
    [[g[0], g[1], g[2], g[3]], [g[1], g[0], g[3], g[2]]].forEach(([t, o, ms, os]) => { if (!rec[t]) return; const won = ms > os; if (o === F || !rec[o]) { if (won) rec[t].fcsw++; else rec[t].losses.push({ rank: null, wk: g[4], n, score: Math.max(ms, os) + "-" + Math.min(ms, os) }); } else (won ? rec[t].wins : rec[t].losses).push({ opp: o, rank: kr[o], wk: g[4], n, score: Math.max(ms, os) + "-" + Math.min(ms, os) }); });
  });
  let nQW = 0, teamsWithNoCut = 0, teamsWithFcsLoss = 0;
  for (const t of fbs) {
    const slug = B.teams[t].g, R = rec[t];
    for (const view of ["wins", "losses", "both"]) for (const top of [1, 5, 10, 25]) {
      const a = await T.answer("quality_wins", { team: slug, view, top }); nQW++;
      if (!a.r.ok) { ok(false, "quality_wins " + slug + "/" + view + "/" + top + " refused", a.r); continue; }
      if (top === 25 || top === 5) cardOk("quality_wins " + slug + "/" + view + "/" + top, a);
      const f = a.r.facts, w = R.wins.slice().sort((x, y) => x.rank - y.rank || x.wk - y.wk || x.n - y.n), cut = w.filter(x => x.rank <= top);
      ok(JSON.stringify(f.wins.map(x => [x.opp, x.rank, x.score, x.week])) === JSON.stringify(cut.map(x => [B.teams[x.opp].g, x.rank, x.score, x.wk])), "qw " + slug + " wins in the top " + top, f.wins);
      ok(f.fbs_wins === w.length && f.fcs_wins === R.fcsw, "qw " + slug + " win counts", [f.fbs_wins, w.length, f.fcs_wins, R.fcsw]);
      const ls = R.losses.slice().sort((x, y) => (y.rank === null ? 1e9 : y.rank) - (x.rank === null ? 1e9 : x.rank) || x.wk - y.wk || x.n - y.n).slice(0, 3);
      ok(JSON.stringify(f.losses.map(x => [x.rank, x.score, x.week])) === JSON.stringify(ls.map(x => [x.rank, x.score, x.wk])), "qw " + slug + " worst losses", f.losses);
      ok(f.losses_total === R.losses.length, "qw " + slug + " loss count");
      ok(f.wins.every(x => x.rank <= top), "qw " + slug + " every listed win is inside the cut " + top);
      if (view !== "losses" && top === 25) { const txt = a.card.text; if (cut.length) ok(txt.indexOf("KickTip rank #" + cut[0].rank) >= 0 && txt.indexOf(cut[0].score) >= 0, "qw " + slug + " best win printed with rank and score"); else if (w.length) ok(/No wins over teams in the KickTip top 25 yet \(best win: /.test(txt) && txt.indexOf("#" + w[0].rank) >= 0, "qw " + slug + " empty-cut text names the best win with its rank"); else ok(/No wins over FBS teams yet\./.test(txt), "qw " + slug + " no FBS win text"); }
      if (view !== "wins" && top === 25) { if (R.losses.length) ok(a.card.text.indexOf(ls[0].score) >= 0, "qw " + slug + " worst loss printed"); else ok(/No losses yet\./.test(a.card.text), "qw " + slug + " no-loss text"); }
      if (view !== "losses" && top === 25 && R.fcsw) ok(/Wins over FCS opponents are not listed \(\d+\)\./.test(a.card.text), "qw " + slug + " FCS wins counted not listed");
    }
    const b1 = await T.answer("quality_wins", { team: slug, view: "wins", show: "best" }); cardOk("quality_wins best " + slug, b1);
    if (R.wins.length) { const bw = R.wins.slice().sort((x, y) => x.rank - y.rank || x.wk - y.wk)[0]; ok(b1.r.facts.best_win.opp === B.teams[bw.opp].g, "qw " + slug + " best win = lowest rank number", [b1.r.facts.best_win.opp, B.teams[bw.opp].g]); }
    if (!R.wins.some(x => x.rank <= 25)) teamsWithNoCut++; if (R.losses.some(x => x.rank === null)) teamsWithFcsLoss++;
  }
  console.log("quality_wins team runs:", nQW, "| teams with no top-25 win:", teamsWithNoCut, "| teams with an FCS loss:", teamsWithFcsLoss);
  ok(teamsWithNoCut > 0 && teamsWithFcsLoss > 0, "data exercises the empty-cut and FCS-loss paths");
  for (let top = 1; top <= 25; top++) {
    const a = await T.answer("quality_wins", { view: "wins", top }); if (!a.r.ok) { ok(false, "qw league top " + top + " refused", a.r); continue; }
    const by = {}; fbs.forEach(t => { const c = rec[t].wins.filter(x => x.rank <= top); if (c.length) by[t] = { n: c.length, best: c.slice().sort((x, y) => x.rank - y.rank)[0] }; });
    const L = Object.keys(by).map(Number).sort((x, y) => by[y].n - by[x].n || by[x].best.rank - by[y].best.rank || sl(B.teams[x].g, B.teams[y].g));
    ok(a.r.facts.total === L.length && a.r.facts.rows.length === Math.min(8, L.length), "qw league top " + top + " counts", [a.r.facts.total, L.length]);
    ok(JSON.stringify(a.r.facts.rows.map(r => [r.slug, r.count, r.rank])) === JSON.stringify(L.slice(0, 8).map(t => [B.teams[t].g, by[t].n, by[t].best.rank])), "qw league top " + top + " rows equal recomputation", a.r.facts.rows.map(r => r.slug));
    if (top === 1 || top === 10 || top === 25) cardOk("quality_wins league top " + top, a);
    if (!L.length) ok(/No team has a win over the KickTip top/.test(a.card.text), "qw league empty text");
  }
  ok((await T.run("quality_wins", { view: "losses" })).reason === "not_applicable", "qw league + losses -> not_applicable");
  ok(!(await T.run("quality_wins", { team: "utah", top: 26 })).ok && !(await T.run("quality_wins", { team: "utah", top: 0 })).ok, "qw top outside 1-25 refused");

  /* ---------- team_compare ---------- */
  const rec2 = {}; fbs.forEach(t => rec2[t] = { w: 0, l: 0, left: 0 });
  B.played.forEach(g => { if (rec2[g[0]]) { g[2] > g[3] ? rec2[g[0]].w++ : rec2[g[0]].l++; } if (rec2[g[1]]) { g[3] > g[2] ? rec2[g[1]].w++ : rec2[g[1]].l++; } });
  B.games.forEach(g => { if (rec2[g.h]) rec2[g.h].left++; if (rec2[g.a]) rec2[g.a].left++; });
  const pollRank = (k, slug) => { const r = POL[k] && POL[k].ranks.filter(x => x[1] === slug)[0]; return r ? r[0] : null; };
  const confRec = (slug, conf) => { const c = S.confs[conf]; if (!c) return null; const ti = c.teams.filter(t => t.slug === slug)[0]; if (!ti) return null; const r = { w: 0, l: 0 }; c.games.forEach(g => { if (g.w === null || g.w === undefined || (g.h !== ti.i && g.a !== ti.i)) return; ((g.w === 1) === (g.h === ti.i)) ? r.w++ : r.l++; }); return r; };
  const slugs = fbs.map(t => B.teams[t].g); let nTC = 0, nSamp = 0, indepPairs = 0, meetPlayed = 0, meetUp = 0, nTba = 0;
  /* the schedule rows of every team, via team_compare against a fixed partner, must equal schedule_strength's remaining facts */
  let schedEq = 0;
  for (let x = 0; x < slugs.length; x++) for (let y = x + 1; y < slugs.length; y++) {
    const sa = slugs[x], sb = slugs[y], a = await T.answer("team_compare", { teams: [sa, sb], aspect: "all" }); nTC++;
    if (!a.r.ok) { ok(false, "team_compare " + sa + "/" + sb + " refused", a.r); continue; }
    const f = a.r.facts, ta = idx[sa], tb = idx[sb], txt = a.card.text;
    if (nTC % 5 === 1) { cardOk("team_compare " + sa + "/" + sb, a); nSamp++; }
    else { ok(!a.card.errors.length, "team_compare " + sa + "/" + sb + ": card errors", a.card.errors); ok(!BANNED.test(txt), "team_compare " + sa + "/" + sb + ": banned wording", (txt.match(BANNED) || [])[0]); }
    [[ta, 0, sa], [tb, 1, sb]].forEach(([t, k, sg]) => {
      const e = f.teams[k], p = P.teams[sg], cr = confRec(sg, B.teams[t].c), ind = p.c === null || p.w === null;
      ok(e.record.w === rec2[t].w && e.record.l === rec2[t].l && e.games_left === rec2[t].left, "tc " + sg + " record and games left");
      ok(e.kt_rank === kr[t] && e.ap === pollRank("ap", sg) && e.coaches === pollRank("coaches", sg), "tc " + sg + " ranks");
      ok(e.chances.playoff === p.p && e.chances.bye === p.b && e.chances.game === (ind ? null : p.c) && e.chances.title === (ind ? null : p.w), "tc " + sg + " chances = pred-teams");
      ok(JSON.stringify(e.conf_record) === JSON.stringify(ind ? null : cr), "tc " + sg + " conference record = ccg-sim games", [e.conf_record, cr]);
      ok(e.sched.games === sch[t].remaining.n && (e.sched.mean === null ? sch[t].remaining.n === 0 : Math.abs(e.sched.mean - sch[t].remaining.s / sch[t].remaining.n) < 1e-9), "tc " + sg + " schedule mean = independent recomputation");
      if (ind) indepPairs++;
    });
    const mp = B.played.filter(g => (g[0] === ta && g[1] === tb) || (g[0] === tb && g[1] === ta)), mu = B.games.filter(g => (g.h === ta && g.a === tb) || (g.h === tb && g.a === ta));
    ok((f.meeting.result !== null) === (mp.length > 0) && (f.meeting.upcoming !== null) === (mu.length > 0), "tc " + sa + "/" + sb + " meeting facts present iff the data has the game");
    if (mp.length) { meetPlayed++; const g = mp[0], aw = g[0] === ta ? g[2] : g[3], bw = g[0] === ta ? g[3] : g[2]; ok(f.meeting.result.score === Math.max(aw, bw) + "-" + Math.min(aw, bw) && f.meeting.result.winner === B.teams[aw > bw ? ta : tb].s && f.meeting.result.week === g[4] && txt.indexOf(f.meeting.result.score) >= 0, "tc " + sa + "/" + sb + " played meeting"); }
    if (mu.length) { meetUp++; ok(!!f.meeting.upcoming.when && /\b(Mon|Tue|Wed|Thu|Fri|Sat|Sun) [A-Z][a-z]{2} \d+/.test(f.meeting.upcoming.when) && txt.indexOf(f.meeting.upcoming.when) >= 0, "tc " + sa + "/" + sb + " upcoming meeting date", f.meeting.upcoming); if (f.meeting.upcoming.tba) nTba++; }
    if (!mp.length && !mu.length) ok(/No meeting this season\./.test(txt), "tc " + sa + "/" + sb + " no-meeting text");
    ok(f.teams[0].name !== f.teams[1].name, "tc " + sa + "/" + sb + " two distinct display names", [f.teams[0].name, f.teams[1].name]);
  }
  console.log("team_compare: all", nTC, "pairs; fully linted", nSamp, "| independent team-cells", indepPairs, "| pairs with a played meeting", meetPlayed, "| with an upcoming meeting", meetUp, "(time TBA:", nTba + ")");
  ok(nTC === 138 * 137 / 2, "team_compare ran every unordered pair", nTC); ok(meetPlayed > 0 && meetUp > 0 && indepPairs > 0, "data exercises played, upcoming and independent paths");
  /* aspects on a sample of pairs */
  const ASP = { chances: [/Chance to reach/, /Chance of a first-round bye/], record: [/Record/, /Conference record/], rank: [/KickTip rank/], schedule: [/Games left/, /Remaining opponents' average/] };
  let nA = 0;
  for (let x = 0; x < slugs.length; x += 7) for (let y = x + 3; y < slugs.length; y += 11) for (const asp of Object.keys(ASP)) {
    const a = await T.answer("team_compare", { teams: [slugs[x], slugs[y]], aspect: asp }); nA++; cardOk("team_compare " + slugs[x] + "/" + slugs[y] + "/" + asp, a);
    const t = a.card.text; ok(ASP[asp].every(r => r.test(t)), "tc aspect " + asp + " shows its rows");
    const others = Object.keys(ASP).filter(k => k !== asp); others.forEach(k => { if (k === "record" && asp === "all") return; ok(!ASP[k].some(r => r.test(t) && !(asp === "record" && k === "chances" && false) && !(k === "rank" && false)) || (asp === "record" && k === "rank" && false), "tc aspect " + asp + " hides the " + k + " rows", ASP[k].filter(r => r.test(t)).map(String)); });
    ok((asp === "chances") === /Estimate from 10,000 simulated seasons/.test(t), "tc aspect " + asp + ": model footer only when a chance row shows");
  }
  console.log("team_compare aspect runs:", nA);
  /* bad params */
  ok((await T.run("team_compare", { teams: ["utah", "utah"] })).reason === "bad_param", "tc same team twice -> bad_param");
  ok(!(await T.run("team_compare", { teams: ["utah", "byu", "arizona"] })).ok && !(await T.run("team_compare", { teams: ["utah"] })).ok && !(await T.run("team_compare", {})).ok, "tc 1 team, 3 teams, none refused");
  ok(!(await T.run("team_compare", { teams: ["utah", "not-a-team"] })).ok, "tc unknown team refused");
  ok(!(await T.run("team_compare", { teams: ["utah", "byu"], aspect: "nonsense" })).ok, "tc unknown aspect refused");
  /* ---------- the schedule function: text and results equal in schedule_strength.js and team_compare.js ---------- */
  const blk = f => { const s = fs.readFileSync(path.join(tree, "assets/tb", f), "utf8"), i = s.indexOf("/* SCHEDULE (this block"), j = s.indexOf("/* END SCHEDULE */"); return s.slice(i, j); };
  ok(blk("schedule_strength.js").length > 500 && blk("schedule_strength.js") === blk("team_compare.js"), "schedule block text identical in schedule_strength.js and team_compare.js");
  for (const t of fbs) {
    const slug = B.teams[t].g, other = slugs[(slugs.indexOf(slug) + 1) % slugs.length];
    const c = await T.run("team_compare", { teams: [slug, other] }), s = await T.run("schedule_strength", { team: slug, view: "remaining" });
    if (!c.ok || !s.ok) { ok(false, "schedule equality run " + slug); continue; }
    const x = c.facts.teams[0].sched, y = s.facts.remaining;
    ok(x.games === y.games && x.fcs === y.fcs && x.mean === y.mean && x.rank === y.rank && x.of === y.of, "schedule equality " + slug, [x, y]); schedEq++;
  }
  console.log("schedule function equality (team_compare vs schedule_strength) on", schedEq, "teams");
  /* ---------- fixtures (a modified copy of the data, in memory): stale as-of, no games left, FCS-only games left, no games played ---------- */
  function mk(mut) {
    TB.clearData(); TB.setLive(NEW);
    TB.setLoader(name => { const d = JSON.parse(fs.readFileSync(path.join(tree, "data", name + ".json"), "utf8")); mut(name, d); return d; });
    return T;
  }
  let X = mk((n, d) => { if (n === "ccg-sim") d.asof = "2026-10-17 23:58 MT"; });
  ok((await X.run("team_compare", { teams: ["utah", "byu"] })).reason === "no_data", "tc stale ccg-sim as-of -> no_data");
  X = mk((n, d) => { if (n === "pred-teams") d.model_asof = "Sat, Oct 17, 2026, 11:58 PM MT"; });
  ok((await X.run("team_compare", { teams: ["utah", "byu"] })).reason === "no_data", "tc stale pred-teams as-of -> no_data");
  const U = idx.utah;
  X = mk((n, d) => { if (n === "sim-bundle") d.games = d.games.filter(g => g.h !== U && g.a !== U); });
  let a = await X.answer("schedule_strength", { team: "utah", view: "both" }); cardOk("fixture no games left: ss utah", a);
  ok(a.r.facts.remaining.games === 0 && a.r.facts.remaining.mean === null && a.r.facts.remaining.rank === null && /No games left\./.test(a.card.text) && /Opponents left \(0 FBS games\) None None/.test(a.card.text), "fixture no games left: ss utah card text", a.card && a.card.text.slice(0, 400));
  a = await X.answer("schedule_strength", { conference: "big12", view: "remaining" }); cardOk("fixture no games left: ss big12", a); ok(/Utah 0 None None/.test(a.card.text) && a.r.facts.rows[a.r.facts.rows.length - 1].slug === "utah", "fixture no games left: the Utah row is last with None", a.card && a.card.text.slice(0, 300));
  a = await X.answer("team_compare", { teams: ["utah", "byu"] }); cardOk("fixture no games left: tc utah/byu", a); ok(/Games left 0 \d/.test(a.card.text) && /Remaining opponents' average KickTip rating None \d+\.\d/.test(a.card.text), "fixture no games left: tc games-left row", a.card && a.card.text.slice(500, 900));
  const FC = B.fcs, bbyu = idx.byu;
  X = mk((n, d) => { if (n === "sim-bundle") { d.games.forEach(g => { if (g.h === U) g.a = FC; else if (g.a === U) g.h = FC; }); } });
  a = await X.answer("schedule_strength", { team: "utah", view: "remaining" }); cardOk("fixture FCS-only games left: ss utah", a);
  ok(a.r.facts.remaining.games === 0 && a.r.facts.remaining.fcs === 5 && /No FBS games left\./.test(a.card.text) && /FCS games left, not counted \(5\)\./.test(a.card.text), "fixture FCS-only games left: notes", a.card && a.card.text.slice(0, 500));
  X = mk((n, d) => { if (n === "sim-bundle") d.played = d.played.filter(g => g[0] !== U && g[1] !== U); });
  a = await X.answer("schedule_strength", { team: "utah", view: "played" }); cardOk("fixture no games played: ss utah", a); ok(/No games played\./.test(a.card.text), "fixture no games played: note", a.card && a.card.text.slice(0, 400));
  a = await X.answer("quality_wins", { team: "utah", view: "both" }); cardOk("fixture no games played: qw utah", a); ok(/No wins over FBS teams yet\./.test(a.card.text) && /No losses yet\./.test(a.card.text), "fixture no games played: qw empty texts", a.card && a.card.text.slice(0, 500));
  X = mk((n, d) => { if (n === "sim-bundle") { const ws = []; d.played = d.played.filter(g => { const w = g[2] > g[3] ? g[0] : g[1]; return !(kr[w] !== undefined && kr[w === g[0] ? g[1] : g[0]] <= 25 && kr[w === g[0] ? g[1] : g[0]] !== undefined); }); } });
  a = await X.answer("quality_wins", { view: "wins", top: 10 }); cardOk("fixture no wins over the cut: qw league", a); ok(a.r.facts.total === 0 && /No team has a win over the KickTip top 10 yet\./.test(a.card.text), "fixture no wins over the cut: league empty text", a.card && a.card.text.slice(0, 400));
  console.log("\n" + (pass + fail) + " checks, " + fail + " failed");
  fails.forEach(f => console.log("FAIL " + f));
  process.exit(fail ? 1 : 0);
})().catch(e => { console.log("CRASH", e.stack); process.exit(2); });
