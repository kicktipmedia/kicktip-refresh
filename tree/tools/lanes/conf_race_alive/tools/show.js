#!/usr/bin/env node
/* show.js: print the rendered card text for params, through TB.render (the page path).  usage: node show.js --root out-tb '{"conference":"big10","team":"michigan-state"}' */
"use strict";
const fs = require("fs"), path = require("path");
const a = process.argv.slice(2), root = path.resolve(a[a.indexOf("--root") + 1] || "out-tb"), p = JSON.parse(a.filter(x => x[0] === "{")[0] || "{}");
const { TB } = require(path.join(__dirname, "../../../core/tools/tbnode.js"))(root);
const rd = n => JSON.parse(fs.readFileSync(path.join(root, "data", n + ".json"), "utf8"));
const r = TB.tool("conf_race_alive").run(p, { "tb/ccg-alive": rd("tb/ccg-alive"), "pred-teams": rd("pred-teams") }, {});
if (!r.ok) { console.log("not ok:", r.reason); process.exit(0); }
const b = TB.render("conf_race_alive", r);
console.log(b.errors && b.errors.length ? "ERRORS " + JSON.stringify(b.errors) : b.text);
