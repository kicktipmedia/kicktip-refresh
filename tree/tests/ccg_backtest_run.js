// reads JSON [{label, conf (engine data), rules, actual:[names]}] from stdin, prints one line per case
const K = require("../src/assets/ccgsim.js"); const cases = JSON.parse(require("fs").readFileSync(0, "utf8")); const out = [];
for (const c of cases) {
  const r = K.solve(c.rules, c.conf, {}); const nm = i => r.names[i];
  let verdict, got = "";
  if (r.pairKnown) { got = r.pair.map(nm).sort().join(" + "); verdict = got === c.actual.slice().sort().join(" + ") ? "MATCH" : "MISMATCH"; }
  else { const sets = (r.outcomes || []).map(o => o.teams.map(nm).sort().join(" + ")); got = sets.join(" | "); verdict = sets.includes(c.actual.slice().sort().join(" + ")) ? "NOT-RESOLVABLE (actual pair is one of the outcomes)" : "NOT-RESOLVABLE (actual pair NOT among outcomes)"; }
  out.push({ label: c.label, verdict, got, actual: c.actual.slice().sort().join(" + "), orderKnown: r.orderKnown, why: r.why.slice(0, 6) });
}
console.log(JSON.stringify(out));
