#!/usr/bin/env node
/* lane_extra_test.js: the paths the shared harness cannot reach because the built data is neutral: gated wording (verified), the analyst guard, record-based "why" sentences, singular forms, fail-closed.
   usage: node lane_extra_test.js --root <built tree> */
"use strict";
const fs = require("fs"), path = require("path");
const a = process.argv.slice(2), root = path.resolve(a[a.indexOf("--root") + 1] || "");
if (!fs.existsSync(root)) { console.error("usage: lane_extra_test.js --root <tree>"); process.exit(2); }
const { TB } = require(path.join(__dirname, "../../../core/tools/tbnode.js"))(root);
const tool = TB.tool("conf_race_alive"), COPY = tool.copy, base = JSON.parse(fs.readFileSync(path.join(root, "data/tb/ccg-alive.json"), "utf8")), pt = JSON.parse(fs.readFileSync(path.join(root, "data/pred-teams.json"), "utf8"));
let pass = 0, fail = 0; const ok = (c, m) => { if (c) pass++; else { fail++; console.log("FAIL", m); } };
const clone = o => JSON.parse(JSON.stringify(o)), txt = e => (e && typeof e === "object" && e.t !== undefined) ? e.t : e;
function all(x, out) { out = out || []; if (typeof x === "string") out.push(x); else if (x && typeof x === "object") Object.keys(x).forEach(k => { if (k !== "src" && k !== "vals") all(x[k], out); }); return out; }
const prm = (conf, team, status) => { const p = {}; if (status) p.status = status; if (conf) p.conference = conf; if (team) p.team = team; return p; };
function go(A, p) {   /* every scenario also goes through TB.render (the page path: shared card builder, copy table, gate check, provenance), not only tool.render */
  const r = tool.run(p, { "tb/ccg-alive": A, "pred-teams": pt }, {}); if (!r.ok) return { r };
  const cd = tool.render(r), b = TB.render("conf_race_alive", r);
  ok(b && b.html && !/tbox-miss/.test(b.html) && !(b.errors && b.errors.length), "TB.render builds the card for " + JSON.stringify(p) + (b && b.errors ? ": " + b.errors.join("; ") : ""));
  return { r, cd, text: b && b.text };
}
const strings = c => all(c).join(" | ");

// 1 neutral data (as built): no gated words anywhere, in any conference, in any view
Object.keys(base.confs).forEach(c => ["", "in", "out"].forEach(s => { const g = go(base, prm(c, null, s)); ok(g.r.ok, c + " runs"); const t = strings(g.cd); ok(!/clinch|eliminated|locked/i.test(t), c + " " + s + " neutral view has no gated word"); ok(!/\ball teams\b|\bevery team\b|\beveryone\b/i.test(t), c + " never says everyone is alive"); ok(!/%|chance of/i.test(t.replace(/not a model chance/, "")), c + " shows no percentage"); }));
// 2 copy never ties a model number to the race status
Object.keys(COPY).forEach(k => { const t = txt(COPY[k]); ok(!/\d/.test(t.replace(/\{[a-z_]+\}/g, "")), "copy " + k + " has no literal digits"); ok(!/percent|%|\bchance\b/i.test(t) || k === "nBasis" || k === "nNeutral", "copy " + k + " mentions no chance except the basis note"); });
ok(COPY.nNeutral === "Race status is our reading of the conference's published tiebreaker rules, not a chance estimate.", "nNeutral is exactly the Creative-approved sentence");
ok(/not a chance estimate/.test(COPY.nBasis) && /how likely/.test(COPY.nBasis), "the basis note says in the race is not a chance estimate"); ok(!/model/i.test(JSON.stringify(COPY)), "no copy string says model");
// 3 analyst guard: the card flag alone never switches the wording
function synth(analyst, verified) {
  const A = clone(base), X = A.confs.big12; X.analyst = analyst; X.verified = verified; X.remaining = 1;
  X.teams[0].cl = true; X.teams[0].st = "in"; X.teams[0].sure = true;
  const o = X.teams[X.teams.length - 1]; o.st = "out"; o.why = "record"; o.by = [X.teams[0].n, X.teams[1].n]; o.left = 1; X.teams[X.teams.length - 2].left = 0; X.teams[2].left = 1;
  X.out_race = [o.n]; X.counts.out = 1; X.counts.in_race = X.teams.length - 1; X.counts.clinched = 1;
  return { A, X, o };
}
["none", "partial", "not_verified"].forEach(an => {
  const S = synth(an, true), g = go(S.A, prm("big12")), t = strings(g.cd);
  ok(g.r.facts.verified === false && g.r.facts.wording === "neutral", an + ": card verified flag alone is not enough");
  ok(!/clinch|eliminated/i.test(t), an + ": no gated word shown"); ok(g.r.facts.counts.clinched === 0, an + ": no clinched rows");
  ok(t.indexOf(COPY.nNeutral) >= 0, an + ": neutral note"); ok(an === "none" ? t.indexOf(COPY.nUnchecked) >= 0 && t.indexOf(COPY.nPartial) < 0 : t.indexOf(COPY.nPartial) >= 0 && t.indexOf(COPY.nUnchecked) < 0, an + ": the right check note");
});
{ const S = synth("verified", false), g = go(S.A, prm("big12")); ok(g.r.facts.verified === false && !/clinch|eliminated/i.test(strings(g.cd)), "analyst verified but no CEO flag: neutral wording"); ok(strings(g.cd).indexOf(COPY.nPartial) < 0 && strings(g.cd).indexOf(COPY.nUnchecked) < 0, "verified, unflipped: no 'not matched' note"); }
// 4 verified on both keys: gated wording appears, and only then
{ const S = synth("verified", true), g = go(S.A, prm("big12")), t = strings(g.cd);
  ok(g.r.facts.verified === true && g.r.facts.wording === "verified", "both keys: verified");
  ok(t.indexOf(COPY.hClinch.t.replace(/\{[a-z_]+\}/g, "")) >= 0 || /Clinched/.test(t), "clinched group shown"); ok(t.indexOf("Out of the race (") >= 0 && !/Eliminated \(/.test(t), "out heading is the plain one in verified mode too");
  ok(t.indexOf(COPY.nVerified) >= 0 && t.indexOf(COPY.nNeutral) < 0, "verified note replaces the neutral note");
  const tv = go(S.A, prm("big12", S.o.s)), tt = strings(tv.cd);
  ok(tt.indexOf(COPY.sOutV.t.slice(0, 8)) >= 0 || /eliminated/.test(tt), "team view: eliminated sentence"); ok(tt.indexOf(COPY.wRecord2.replace(/\{[a-z]+\}/g, "")) >= 0 || /both finish ahead/.test(tt), "team view: two rivals ahead on record");
  const S1 = synth("verified", true); S1.o.by = [S1.X.teams[0].n]; const t1 = strings(go(S1.A, prm(null, S1.o.s)).cd); ok(/finishes ahead of/.test(t1), "one rival ahead on record sentence");
  const tc = strings(go(S.A, prm(null, S.X.teams[0].s)).cd); ok(/clinched a place/.test(tc), "team view: clinched sentence");
}
// 5 singular / zero forms
{ const S = synth("none", false), g = go(S.A, prm("big12")), t = strings(g.cd); ok(/One conference game is still to be played/.test(t), "one game left note"); ok(/one game left/.test(t), "one game left row"); ok(/no games left/.test(t), "no games left row");
  S.X.remaining = 0; ok(/All conference games have been played/.test(strings(go(S.A, prm("big12")).cd)), "no games left note"); }
// 6 fail closed
{ const S = synth("none", false); S.X.counts.unknown = 1; ok(go(S.A, prm("big12")).r.reason === "no_data", "unknown status refuses (no_data)"); ok(go(S.A, prm(null, S.X.teams[0].s)).r.reason === "no_data", "unknown status refuses team view"); }
ok(tool.run(prm("big12"), {}, {}).reason === "no_data", "missing data: no_data");
// 7 independents: the group line is the approved sentence for exactly two; other counts fall back to one approved line per team; none is no_data
{ const mk = names => { const q = clone(pt); Object.keys(q.teams).forEach(k => { if (q.teams[k].cs === "independents") q.teams[k].cs = "x"; }); names.forEach((n, i) => { q.teams["ind-t" + i] = { n: n, cs: "independents" }; }); return q; };
  const run = (q, p) => { const r = tool.run(p, { "tb/ccg-alive": base, "pred-teams": q }, {}); if (!r.ok) return { r }; const b = TB.render("conf_race_alive", r); ok(b && b.html && !/tbox-miss/.test(b.html) && !(b.errors && b.errors.length), "independents render via TB.render " + JSON.stringify(p)); return { r, text: b.text }; };
  const two = run(mk(["UConn", "Notre Dame"]), { conference: "ind" }); ok(two.text.indexOf("Notre Dame and UConn play as independents, so they are not in a conference race.") >= 0, "two independents: approved group line (sorted by name)");
  const one = run(mk(["Notre Dame", "UConn"]), { team: "ind-t0" }); ok(one.text.indexOf("Notre Dame plays as an independent, so it is not in a conference race.") >= 0 && one.text.indexOf("play as independents") < 0, "single independent: single-team line");
  const three = run(mk(["Army", "Notre Dame", "UConn"]), { conference: "ind" }); ok(/Army plays as an independent/.test(three.text) && /UConn plays as an independent/.test(three.text), "three independents: one approved line each");
  ok(run(mk([]), { conference: "ind" }).r.reason === "no_data", "no independents in the data: no_data"); }
console.log((fail ? "FAILED" : "PASSED") + ": lane extra test " + pass + " checks, " + fail + " failures"); process.exit(fail ? 1 : 0);
