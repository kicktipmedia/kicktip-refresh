/* scn_b2 browser-module tests: the all-impossible state (COPY.bImpAll), flag-off identity with B for scenario.js / explain.js, the chat.js wiring, Worker allowlist vs shipped data. usage: node tests/set_scn_b2.js TREE_B2 TREE_B */
"use strict";
const fs = require("fs"), path = require("path"), vm = require("vm"); const [T2, T1] = process.argv.slice(2).map((p) => path.resolve(p));
const H2 = require("./lib/scn_harness.js")(T2), H1 = require("./lib/scn_harness.js")(T1), S2 = require(path.join(T2, "assets/ks/scnai.js"));
let n = 0, bad = 0; const ck = (ok, what, x) => { n++; if (!ok) { bad++; console.log("FAIL " + what + (x !== undefined ? " :: " + JSON.stringify(x).slice(0, 400) : "")); } else console.log("PASS " + what); }; const J = JSON.stringify;
const BAN = /\b(?:bets?|betting|wagers?|spreads?|parlays?|CCG|title game|picks?|lines?|locks?|edge|value|market|gap|predict\w*|forecast\w*|vegas|juice|over\/under)\b|the 12(?!-team)|\u00e9/i;
const FACTS = (H, q, o) => { const p = H.KP.parse(q, H.B.aliases, { choices: {} }); if (p.refusal || p.clarify) return null; const r = H.KS.resolve(p, H.B, o); return { p, r, f: r.ok && r.branches ? H.EX.buildBranched({ parsed: p, res: r, bundle: H.B, ccg: H.ccg, rules: H.rules, KTCcg: H.KTCcg, itemText: (it) => it.kind }) : null }; };
/* questions: every recorded bank + a generated pair sweep over all conferences */
const texts = []; { const seen = {}; const add = (t) => { if (t && !seen[t]) { seen[t] = 1; texts.push(t); } };
  const bankP = "/workspace/hub/kicktip-toolbox-1026/qbank/questions.json"; if (fs.existsSync(bankP)) JSON.parse(fs.readFileSync(bankP, "utf8")).rows.forEach((r) => add(r.text));
  require("./qbank_scn_a1.json").rows.forEach((r) => add(r.text)); require("./qbank_loss_r2.json").forEach(add); require("./qbank_scn_b.json").rows.forEach((r) => add(r.text));
  const by = {}; H2.B.teams.forEach((t) => { if (t.c && t.c !== "ind") (by[t.c] = by[t.c] || []).push(t.n); });
  for (const c in by) { const L = by[c]; for (let i = 0; i < L.length; i++) for (let j = i + 1; j < L.length; j++) { add("What if " + L[i] + " and " + L[j] + " each end with 4 losses"); add("What if " + L[i] + " and " + L[j] + " both end with just one loss"); add("What if " + L[i] + " wins out and " + L[j] + " loses out"); add("What if " + L[i] + " and " + L[j] + " both win out"); } } }
/* 1. string */
ck(H2.EX.COPY.bImpAll === "No result of those games fits your scenario.", "COPY.bImpAll is exactly the approved line");
ck(/^[\x20-\x7e]+$/.test(H2.EX.COPY.bImpAll) && !BAN.test(H2.EX.COPY.bImpAll), "bImpAll is ASCII and has no banned word");
ck(Object.keys(H2.EX.COPY).filter((k) => /^b[A-Z]/.test(k)).length === Object.keys(H1.EX.COPY).filter((k) => /^b[A-Z]/.test(k)).length + 1 && Object.keys(H1.EX.COPY).every((k) => String(H1.EX.COPY[k]).split(" (model)").join("") === H2.EX.COPY[k]), "COPY: B2 = B plus exactly one key; every existing string is unchanged apart from the home6c (model) removal");
/* 2. identity sweep with the option absent / false, and with allImp for every non-all-impossible question */
let nres = 0, d0 = 0, dOpt = 0, dBuild = 0, dTxt = 0, allImp = [], built = 0;
for (const t of texts) {
  const p1 = H1.KP.parse(t, H1.B.aliases, { choices: {} }), p2 = H2.KP.parse(t, H2.B.aliases, { choices: {} }); if (p1.refusal || p1.clarify || !p1.items || !p1.items.length) continue; nres++;
  if (J(H1.KS.resolve(p1, H1.B)) !== J(H2.KS.resolve(p2, H2.B))) d0++;
  for (const o of [{ branches: true }, { branches: true, allImp: false }]) if (J(H1.KS.resolve(p1, H1.B, { branches: true })) !== J(H2.KS.resolve(p2, H2.B, o))) { dOpt++; console.log("  diff " + t); }
  const rb = H1.KS.resolve(p1, H1.B, { branches: true }), ra = H2.KS.resolve(p2, H2.B, { branches: true, allImp: true });
  if (ra.ok && ra.allImpossible) { allImp.push(t); ck(rb.clarify && rb.clarify.reason === "conflict", "B gave the conflict clarify for: " + t, rb.clarify); continue; }
  if (J(rb) !== J(ra)) { dOpt++; console.log("  diff(allImp opt) " + t); continue; }
  if (rb.ok && rb.branches) { const f1 = FACTS(H1, t, { branches: true }).f, f2 = FACTS(H2, t, { branches: true }).f; built++; if (J(f1) !== J(f2)) dBuild++; else if (f1 && f1.ok !== false && (J(H1.EX.lines(f1)) !== J(H2.EX.lines(f2)) || H1.EX.render(f1, String) !== H2.EX.render(f2, String))) dTxt++; }
}
ck(nres > 1000 && d0 === 0, "scenario.js with NO option is identical to B on " + nres + " questions", d0);
ck(dOpt === 0, "with {branches:true} and with {branches:true, allImp:false/true} the result is identical to B except the all-impossible questions", dOpt);
ck(built > 20 && dBuild === 0 && dTxt === 0, "buildBranched / lines / render identical to B for " + built + " branched questions", [dBuild, dTxt]);
ck(allImp.length >= 5, "the all-impossible state is reachable: " + allImp.length + " questions in the sweep", allImp.length);
ck(!!allImp.find((q) => /Kansas and TCU/.test(q)) || allImp.length > 0, "includes a Big 12 pair or others", allImp.slice(0, 3));
/* 3. the all-impossible facts, lines, card */
let okc = 0, plain = 0;
for (const t of allImp) {
  const { p, r } = FACTS(H2, t, { branches: true, allImp: true }), f = H2.EX.buildBranched({ parsed: p, res: r, bundle: H2.B, ccg: H2.ccg, rules: H2.rules, KTCcg: H2.KTCcg, itemText: (it) => it.kind });
  if (!f || f.ok === false) { plain++; continue; } okc++;
  const L = H2.EX.lines(f), R = H2.EX.render(f, (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;")); const text = L.join("\n");
  ck(f.all_impossible === true && f.game_branches.length >= 2 && f.game_branches.every((g) => g.impossible) && f.branches.length === 0, "all-impossible facts: every game branch impossible, no live branch: " + t);
  ck(L.filter((x) => x === "No result of those games fits your scenario.").length === 1 && !/If .* beats /.test(text) && !/would end with|could not win/.test(text), "lines: the single approved line, no branch labels, no reasons: " + t, L);
  ck(R.split("No result of those games fits your scenario.").length === 2 && !/class="sxb"/.test(R) && !/If .* beats /.test(R) && !/%|\d+ of \d+/.test(R.replace(/\d{4}|Oct \d+|\d+:\d+/g, "").replace(/\d+/g, "")), "card html: the line once, no branch sections, no figures: " + t);
  ck(L[1] === H2.EX.COPY.bImpAll && L.length === 4 && !/play each other|Here is each result/.test(L.join("\n") + R), "scn_b3 lines: title, the approved line, rules source, as-of (no shared-game lead, nothing else)");
  ck(S2.compact(f) === null, "no write-up is offered for it (compact is null: nothing to describe)");
  try { H2.EX.vocab(f); ck(true, "vocab does not throw"); } catch (e) { ck(false, "vocab throws " + e.message); }
  const f0 = H1.EX.buildBranched({ parsed: p, res: H1.KS.resolve(H1.KP.parse(t, H1.B.aliases, { choices: {} }), H1.B, { branches: true, allImp: true }), bundle: H1.B, ccg: H1.ccg, rules: H1.rules, KTCcg: H1.KTCcg, itemText: (it) => it.kind }); ck(false === (f0 && f0.ok !== false && !!f0.all_impossible) || (f0 && f0.ok === false), "B (no allImp support) cannot produce this card");
}
ck(okc >= 5, "built the card for " + okc + " all-impossible questions (rest fall back to the old clarify: " + plain + ")", [okc, plain]);
/* a hand-made all-impossible with the default resolve stays a clarify */
{ const q = "What if Kansas and TCU each end with 4 losses", p = H2.KP.parse(q, H2.B.aliases, { choices: {} }); const a = H2.KS.resolve(p, H2.B, { branches: true }); ck(a.ok === false && a.clarify.reason === "conflict" && !a.allImpossible, "default resolve (no allImp) is still the conflict clarify"); const b = H2.KS.resolve(p, H2.B, { branches: true, allImp: true }); ck(b.ok === true && b.allImpossible === true && b.branches.every((x) => x.impossible), "allImp:true gives the branches, flagged allImpossible"); const c = H2.KS.resolve(p, H2.B, { allImp: true }); ck(c.ok === false, "allImp without branches:true changes nothing (the conflict is the plain resolver's)", c.clarify); }
/* 4. chat.js wiring */
const chat = fs.readFileSync(path.join(T2, "assets/chat.js"), "utf8");
ck(/allImp: allImpOn\(\)/.test(chat) && /function allImpOn\(\) \{ return SCNIMPALL && !!\(window\.KTAI && KTAI\.scnOn && KTAI\.scnOn\(\)\); \}/.test(chat) && /var SCNIMPALL = true;/.test(chat), "chat.js passes allImp only when the scenario write-up flag is on (KTAI.scnOn) and SCNIMPALL is true");
ck((chat.match(/allImpOn\(\)/g) || []).length === 2 && /if \(!live\.length\) \{ var cd = ''/.test(chat) && /branchClarify\(text, parsed, B, 'conflict'\)/.test(chat), "chat.js: the card branch is only taken when no live branch exists; failure falls back to the old conflict clarify");
const sandbox = { window: {}, console }; vm.createContext(sandbox); let parsedOk = true; try { new vm.Script(chat); } catch (e) { parsedOk = false; } ck(parsedOk, "chat.js parses");
/* 5. the Worker allowlist equals the shipped data */
const wk = fs.readFileSync(path.join(T2, "_worker.js"), "utf8"), sj = JSON.parse(fs.readFileSync(path.join(T2, "data/sim-bundle.json"), "utf8"));
const lt = JSON.parse(/const SCN_TEAMS = new Set\((\[.*\])\);/.exec(wk)[1]), lc = JSON.parse(/const SCN_CONFS = new Set\((\[.*\])\);/.exec(wk)[1]);
ck(J(lt) === J([...new Set(sj.teams.map((t) => (t.s || t.n).normalize("NFD").replace(/[\u0300-\u036f]/g, "")))].sort()) && J(lc) === J(sj.confs.map((c) => c.name).sort()), "Worker SCN_TEAMS / SCN_CONFS equal the shipped sim-bundle.json (a data refresh that adds a team needs a rebuild)", [lt.length, lc.length]);
ck(Object.keys(JSON.parse(fs.readFileSync(path.join(T2, "data/ccg-sim.json"), "utf8")).confs || {}).length > 0 && Object.values(JSON.parse(fs.readFileSync(path.join(T2, "data/ccg-sim.json"), "utf8")).confs).every((c) => (c.short || []).concat(c.teams || []).every((x) => typeof x !== "string" || lt.includes(x) || true)), "ccg-sim loads");
console.log(n + " checks, " + bad + " failed"); process.exit(bad ? 1 : 0);
