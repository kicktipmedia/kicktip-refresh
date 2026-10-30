/* router2: the standard what-if parser (KTParse.parse) base vs router2 over the whole QA bank + the loss-count variants. Only loss-count wordings (and "A, B, and C" lists) may differ. usage: node tests/equiv_parse_r2.js BASE TREE questions.json */
"use strict";
const fs = require("fs"), vm = require("vm"), path = require("path"); const [t0, t1, qf] = process.argv.slice(2);
const load = t => { const c = vm.createContext({ window: {} }); vm.runInContext(fs.readFileSync(path.join(t, "assets/ks/parse.js"), "utf8"), c); return { P: c.KTParse || c.window.KTParse, B: JSON.parse(fs.readFileSync(path.join(t, "data/sim-bundle.json"), "utf8")) }; };
const A = load(t0), B = load(t1), rows = JSON.parse(fs.readFileSync(qf, "utf8")).rows, seen = {}, texts = [];
rows.map(r => r.text).concat(require("./qbank_loss_r2.json")).forEach(t => { if (!seen[t]) { seen[t] = 1; texts.push(t); } });
const sig = (X, t) => JSON.stringify((r => ({ i: r.intent, it: r.items, cl: r.clarify_reason, rf: r.refusal }))(X.P.parse(t, X.B.aliases, { choices: {} })));
const diffs = []; texts.forEach(t => { const a = sig(A, t), b = sig(B, t); if (a !== b) diffs.push({ q: t, before: a.slice(0, 160), after: b.slice(0, 200) }); });
console.log("parser equivalence vs router1b: " + texts.length + " questions; identical " + (texts.length - diffs.length) + ", differing " + diffs.length);
diffs.forEach(d => console.log("DIFF " + JSON.stringify(d.q) + "\n   1b: " + d.before + "\n   r2: " + d.after));
const ok = diffs.every(d => /\bloss(?:es)?\b|\bno loss|undefeated|\bloses? only|\bdrops?\b/i.test(d.q) || /,.*\band\b/.test(d.q) || /\bloses?\b.*\b(?:one|two|three|\d)\b/i.test(d.q));
console.log(ok ? "ALL DIFFS ARE LOSS-COUNT WORDINGS OR 'A, B, and C' LISTS" : "UNEXPECTED DIFFS"); process.exit(ok ? 0 : 1);
