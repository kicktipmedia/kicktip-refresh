#!/usr/bin/env node
/* alive_gate.js --root <tree>: the publish gates for data/tb/ccg-alive.json. Exit 0 = pass.
   exit 4: card asof differs from data/ccg-sim.json asof (the page stamp, ccg-sim and ccg-alive must be one moment)
   exit 5: any conference has a team whose status the search could not prove (counts.unknown > 0): refuse to publish a guess
   exit 6: card missing or not valid JSON
   exit 7: banned word in the card ("CCG", "title game") */
"use strict";
const fs = require("fs"), path = require("path");
const i = process.argv.indexOf("--root"); if (i < 0) { console.error("usage: alive_gate.js --root <tree>"); process.exit(2); }
const r = path.resolve(process.argv[i + 1]);
let a, s;
try { a = JSON.parse(fs.readFileSync(path.join(r, "data/tb/ccg-alive.json"), "utf8")); s = JSON.parse(fs.readFileSync(path.join(r, "data/ccg-sim.json"), "utf8")); } catch (e) { console.error("alive_gate: cannot read card or ccg-sim: " + e.message); process.exit(6); }
if (a.asof !== s.asof) { console.error("alive_gate: asof mismatch, alive " + a.asof + " vs ccg-sim " + s.asof); process.exit(4); }
const bad = Object.entries(a.confs).filter(([k, c]) => c.counts.unknown > 0).map(([k]) => k);
if (bad.length) { console.error("alive_gate: unfinished search (unknown team status) in: " + bad.join(",") + ". Refusing to publish a status we could not prove."); process.exit(5); }
const m = /\bCCG\b|title game/i.exec(JSON.stringify(a)); if (m) { console.error("alive_gate: banned word in card: " + m[0]); process.exit(7); }
console.log("alive_gate ok: asof " + a.asof + " equals ccg-sim; no unknown statuses; " + Object.keys(a.confs).length + " conferences");
