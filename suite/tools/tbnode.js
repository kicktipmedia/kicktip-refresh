/* Load the toolbox from a built tree in Node (tests, manifest generator). Returns the KTTB global with every module and rules file registered (dark tools included). */
"use strict";
const fs = require("fs"), path = require("path");
const CORE = ["registry.js", "core.js", "card.js", "matcher.js", "plan.js"];
module.exports = function loadTree(tree, opts) {
  opts = opts || {}; tree = path.resolve(tree);
  delete globalThis.KTTB;
  const dir = path.join(tree, "assets", "tb");
  const kp = path.join(tree, "assets", "ks", "parse.js"); if (fs.existsSync(kp)) globalThis.KTParse = require(kp);
  CORE.forEach(f => require(path.resolve(dir, f)));
  const skip = new Set(CORE.concat(["manifest.js"]));
  const mods = fs.readdirSync(dir).filter(f => f.endsWith(".js") && !skip.has(f)).sort();
  mods.forEach(f => require(path.resolve(dir, f)));
  const rd = path.join(dir, "rules");
  if (fs.existsSync(rd)) fs.readdirSync(rd).filter(f => f.endsWith(".js")).sort().forEach(f => require(path.resolve(rd, f)));
  return { TB: globalThis.KTTB, coreFiles: CORE, modules: mods, dir };
};
