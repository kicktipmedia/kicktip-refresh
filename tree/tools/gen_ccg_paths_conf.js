#!/usr/bin/env node
/* Phase 4 export (WP 4.1 shape): data/tb/ccg-paths/<conf>.json, one file per race conference, in the SPEC section 5 shape.
 * Built ONLY from existing pipeline data in the tree: data/tb/ccg-paths.json (path search output) + data/tb/ccg-alive.json (verified, rules hash, as-of).
 * Deterministic (sorted keys, no clock). Fails closed on as-of mismatch, rules-hash mismatch, unknown letters, or a must/N claim without an exhausted search.
 * Letter map: A,H,T,N kept; P ("a path exists, help not worked out") and U -> U (SPEC's closed list is A/H/T/N/U).
 * usage: node gen_ccg_paths_conf.js <tree root> */
"use strict";
const fs = require("fs"), path = require("path");
const tree = path.resolve(process.argv[2]); const D = path.join(tree, "data", "tb");
const P = JSON.parse(fs.readFileSync(path.join(D, "ccg-paths.json"), "utf8")), A = JSON.parse(fs.readFileSync(path.join(D, "ccg-alive.json"), "utf8"));
function die(m) { console.error("gen_ccg_paths_conf: " + m); process.exit(1); }
if (P.asof !== A.asof) die("as-of mismatch " + P.asof + " vs " + A.asof);
const out = path.join(D, "ccg-paths"); fs.mkdirSync(out, { recursive: true });
const sizes = {};
for (const c of Object.keys(P.confs).sort()) {
  const X = A.confs[c]; if (!X) die("conference " + c + " not in ccg-alive");
  if (P.rules[c] !== X.rules.hash) die("rules hash mismatch " + c);
  const teams = {};
  for (const s of Object.keys(P.confs[c]).sort()) {
    const t = P.confs[c][s];
    if (!/^[AHTNPU]*$/.test(t.t) || t.t.length !== t.o.length + 1) die("bad letters " + c + "/" + s);
    const tab = t.t.replace(/P/g, "U"), exh = t.e === 1;
    /* must games on a non-exhausted conference come from the pipeline counting proof (SPEC section 5 allows exhausted search OR counting proof) */
    const first = t.t.search(/[^NU]/), minw = (t.m === null || t.m === undefined) ? null : t.m;   /* minw = the pipeline's m (fewest own wins with a proven path); it must be the first A/H/T/P letter */
    if (minw !== null && minw !== first) die("minw disagrees " + c + "/" + s);
    const help = t.h ? t.h.map(g => ({ game: g[0], winner: g[1], suff: true })) : null;
    const key = Array.from(new Set(t.k.concat(t.h ? t.h.map(g => g[0]) : []))).sort();
    teams[s] = { own: t.o.slice(), tab: tab, minw: minw, must: t.k.slice(), help: help, key: key, exh: exh, nodes: null };
  }
  const doc = { v: 1, conf: c, asof: P.asof, rules: { hash: X.rules.hash }, verified: X.verified === true,
    doc: "Phase 4 path export. own = remaining own conference game ids; tab = one letter per own-win total 0..len(own): A reaches under every outside result we can compute, H only with help, T only if a tie goes its way on a step KickTip cannot see, N not possible, U not computed; minw = fewest own wins that is not N (null if not proven); must = own games it cannot lose (exhausted search or counting proof only); help = one set of outside results that gets it in if it wins out; key = must + help games; exh = no U letter; nodes = search size (not recorded by the current pipeline: null).",
    teams: teams };
  const body = JSON.stringify(doc); fs.writeFileSync(path.join(out, c + ".json"), body); sizes[c] = body.length;
}
console.log(JSON.stringify(sizes));
