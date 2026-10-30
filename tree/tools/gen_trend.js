#!/usr/bin/env node
/* Reference exporter for data/tb/trend.json (toolbox10, tool team_trend). Run from the weekly refresh step (Monday), after pred-teams.json and sim-bundle.json are written.
 *   node gen_trend.js --pred <pred-teams.json> --bundle <sim-bundle.json> --out <data/tb/trend.json> [--prev <archive/<date>/trend-snap.json>] [--snap-out <archive/<date>/trend-snap.json>]
 * --snap-out writes this week's snapshot ({asof, seasons, model, t:{slug:{p,b,c,w,rk}}}) for the non-public weekly archive; the archive file is never edited by hand.
 * Without --prev the output is the "not yet" file: prev_asof null and an empty t. With --prev (last week's snapshot) t[slug] = {p,b,c,w,rk} each as [now, prev] and prev_asof set;
 * a previous snapshot from another model or season count is refused (exit 3), so a card can never compare unlike numbers. Nothing here is shipped to visitors. */
"use strict";
const fs = require("fs");
const arg = (k, d) => { const i = process.argv.indexOf("--" + k); return i > 0 ? process.argv[i + 1] : d; };
const predP = arg("pred"), bunP = arg("bundle"), outP = arg("out"), prevP = arg("prev"), snapP = arg("snap-out");
if (!predP || !bunP || !outP) { console.error("usage: see header"); process.exit(2); }
const P = JSON.parse(fs.readFileSync(predP, "utf8")), B = JSON.parse(fs.readFileSync(bunP, "utf8"));
const rating = B.model.rating.slice(0, B.fcs), rank = {};
B.teams.forEach((t, i) => { if (!t.g || i >= B.fcs) return; let r = 1; for (let k = 0; k < rating.length; k++) if (rating[k] > rating[i] || (rating[k] === rating[i] && k < i)) r++; rank[t.g] = r; });
const now = { v: 1, asof: B.as_of, seasons: P.seasons, model: B.model_id, t: {} };
Object.keys(P.teams).sort().forEach(g => { const x = P.teams[g]; if (rank[g] === undefined) return; now.t[g] = { p: x.p, b: x.b, c: x.c, w: x.w, rk: rank[g] }; });
if (snapP) fs.writeFileSync(snapP, JSON.stringify(now));
const out = { v: 1, asof: B.as_of, prev_asof: null, seasons: P.seasons, prev_seasons: null, model: B.model_id, prev_model: null, doc: "toolbox10 trend. Weekly movement for team_trend: t[slug] = {p, b, c, w, rk} each as [now, prev] = playoff field, first-round bye, conference championship game, conference title, KickTip rank. prev_asof null means fewer than two weekly snapshots exist yet (t is then empty and the tool shows its not-yet card).", t: {} };
if (prevP) {
  const V = JSON.parse(fs.readFileSync(prevP, "utf8"));
  if (V.model !== now.model || V.seasons !== now.seasons) { console.error("previous snapshot is from another model or season count: refused"); process.exit(3); }
  if (!(V.asof < now.asof)) { console.error("previous snapshot is not older than this one: refused"); process.exit(3); }
  out.prev_asof = V.asof; out.prev_seasons = V.seasons; out.prev_model = V.model;
  Object.keys(now.t).forEach(g => { const a = now.t[g], b = V.t[g]; if (!b) return; out.t[g] = { p: [a.p, b.p], b: [a.b, b.b], c: [a.c, b.c], w: [a.w, b.w], rk: [a.rk, b.rk] }; });
}
fs.writeFileSync(outP, JSON.stringify(out));
console.log("wrote " + outP + " bytes " + fs.statSync(outP).size + " prev_asof " + out.prev_asof + " teams " + Object.keys(out.t).length);
