/* Node helper: load a built tree's toolbox, data from the tree, match / run / render. */
"use strict";
const fs = require("fs"), path = require("path");
const here = path.resolve(__dirname, "..", "..");
module.exports = function (tree) {
  tree = path.resolve(tree);
  const loadTree = require(path.join(here, "tools", "tbnode.js"));
  const { TB } = loadTree(tree);
  const DATA = {};
  TB.setLoader(name => { const p = path.join(tree, "data", name + ".json"); if (!fs.existsSync(p)) throw new Error("missing " + name); return DATA[name] || (DATA[name] = JSON.parse(fs.readFileSync(p, "utf8"))); });
  const manifestTools = () => Object.keys((TB.manifest && TB.manifest.tools) || {});
  return {
    TB, tree, DATA,
    raw: name => { TB.setLoader; return JSON.parse(fs.readFileSync(path.join(tree, "data", name + ".json"), "utf8")); },
    async data(names) { const o = {}; for (const n of names) o[n] = await TB.data(n); return o; },
    async match(text, o) { o = o || {}; const d = await this.data(["sim-bundle"]); return TB.match(text, o.page || { mode: "home" }, d, o); },
    async run(id, params) { return TB.run(id, params); },
    async answer(id, params) { const r = await TB.run(id, params); if (!r.ok) return { r, card: null }; const c = TB.render(id, r); return { r, card: c }; }
  };
};
