// prints {code, picks} for a random fill (seeded) whose result is "tie not resolvable by this tool": node tests/ccg_find_tie.js <code> [minOutcomes]
const fs = require("fs"), K = require("../src/assets/ccgsim.js"), root = __dirname + "/..";
const code = process.argv[2] || "big12", min = +(process.argv[3] || 2);
const D = JSON.parse(fs.readFileSync(root + "/data/ccg-sim.json")).confs[code], R = JSON.parse(fs.readFileSync(root + "/data/ccg-rules.json")).rules[code];
let s = 99; const rnd = () => { s = (s * 1664525 + 1013904223) % 4294967296; return s / 4294967296; };
for (let i = 0; i < 20000; i++) { const p = K.randomFill(D, {}, rnd), r = K.solve(R, D, p); if (r.ready && !r.pairKnown && r.outcomes.length >= min) { console.log(JSON.stringify({ code, picks: p, outcomes: r.outcomes.map(o => o.teams.map(t => r.names[t])) })); process.exit(0); } }
console.log("none"); process.exit(1);
