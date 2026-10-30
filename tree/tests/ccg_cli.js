// Node smoke run of the official-rules title-game engine on the real data.
// usage: node tests/ccg_cli.js <confcode> [random|allhome|allaway|favorites|none] [seed]
const fs = require("fs"), path = require("path"); const K = require("../src/assets/ccgsim.js");
const root = path.join(__dirname, ".."); const code = process.argv[2] || "big12", mode = process.argv[3] || "random", seed = +(process.argv[4] || 1);
const data = JSON.parse(fs.readFileSync(root + "/data/ccg-sim.json")).confs[code];
const rules = JSON.parse(fs.readFileSync(root + "/data/ccg-rules.json")).rules[code];
if (!data || !rules) { console.log("no data/rules for", code); process.exit(2); }
let s = seed; const rnd = () => { s = (s * 1664525 + 1013904223) % 4294967296; return s / 4294967296; };
let picks = {};
if (mode === "allhome") data.games.forEach(g => { if (g.w === null) picks[g.id] = 1; });
if (mode === "allaway") data.games.forEach(g => { if (g.w === null) picks[g.id] = 0; });
if (mode === "random") picks = K.randomFill(data, {}, rnd);
if (mode === "favorites") { const f = K.favorites(data, JSON.parse(fs.readFileSync(root + "/build/site/data/pred-lines.json")), Date.now() / 1000); picks = f.picks; console.log("favorites:", f.status, f.withLine, "with line;", f.noLine, "without;", f.note); }
const r = K.solve(rules, data, picks);
console.log(code, mode, "left", r.left, "of", r.total);
r.table.forEach(t => console.log(String(t.rank).padStart(2), t.name.padEnd(18), t.w + "-" + t.l, t.left + " left", t.clinch));
if (r.pair) console.log("PAIR:", r.pair.map(i => r.names[i]).join(" vs "), r.orderKnown ? "" : "(order open)");
else console.log("PAIR: not decided or not resolvable");
r.why.forEach(l => console.log(" -", l));
(r.outcomes || []).forEach(o => { console.log(" OUTCOME", o.teams.map(i => r.names[i]).join(" vs ")); o.conds.slice(0, 4).forEach(c => console.log("    if", c)); o.why.forEach(w => console.log("      ", w)); });
