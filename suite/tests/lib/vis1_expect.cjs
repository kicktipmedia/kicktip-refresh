/* vis1 expected values (Set 2b live: 21 ids; SCN_SYS rule 3/4 wording). Exact, fail-closed reversals so the older identity suites keep proving everything else unchanged. */
"use strict";
const fs = require("fs");
const F3W = "/workspace/kicktip-final3/work/out/_worker.js";
const ALL19 = ['conf_race_alive', 'conf_standings', 'explain_site', 'games_that_matter', 'head_to_head', 'path_compare', 'playoff_field', 'quality_wins', 'rankings_list', 'schedule_strength', 'slate_this_week', 'status_check', 'team_compare', 'team_needs', 'team_path', 'team_projection', 'team_schedule', 'team_snapshot', 'tiebreak_explain'];
const NEW2 = ['conf_vs_conf', 'strength_of_record'];
const ALL21 = ALL19.concat(NEW2).sort();
/* set3m3: TB_SET3_VISIBLE is now true (Jared approved): the 5 Set 3 ids are on every host. Was set3m: game_win_chance (#28) live = 22 ids; #23-#27 = TB_SET3_IDS, added to the ask-config tb list in Preview only (KT_ENV=preview, not the live host) while TB_SET3_VISIBLE is false */
const NEW3 = ['game_win_chance'], ALL22 = ALL21.concat(NEW3).sort(), SET3 = ['cfp_committee_rankings', 'my_teams_digest', 'team_history', 'team_stats', 'whatif_conference_outcome'];
const S3_BLOCK = "const TB_SET3_IDS = [" + SET3.map((i) => "'" + i + "'").join(", ") + "];   /* set3m: Set 3 tools #23-#27, dark: on in Preview only (KT_ENV=preview, not the live host); Production lists unchanged. Matcher-only (not in ROUTER_TOOLS). */\n" +
  "const TB_SET3_VISIBLE = true;    /* the one switch: true = TB_SET3_IDS go live on every host (Production too) */\n" +
  "const tbSet3 = (env, url) => TB_SET3_VISIBLE || askPreviewOnly(env, url) ? TB_SET3_IDS : [];\n";
const S3_SUBS = [["if (TB_ON.length) cfg.tb = TB_ON.concat(tbSet3(env, url));", "if (TB_ON.length) cfg.tb = TB_ON.slice();"], ["!TB_ON.concat(tbSet3(env, url)).includes(x[1])", "!TB_ON.includes(x[1])"]];
const previewOnly = (env, url) => !!(env && env.KT_ENV === 'preview') && url.hostname !== 'kicktipmedia.com' && url.hostname !== 'www.kicktipmedia.com';
const SYS = [
  ['3. Use one of these phrases at least once, exactly, inside a complete sentence: ', '3. Use one of these phrases at least once, exactly: '],
  [' "at least 99.95%". If the facts have no playoff chance, do not mention a chance at all.', ' "at least 99.95%".'],
];
const SYSJ = SYS.map(([a, b]) => [a.replace(/"/g, '\\"'), b.replace(/"/g, '\\"')]);
function once(t, a, b, what) { const n = t.split(a).length - 1; if (n !== 1) throw new Error("vis1: expected exactly one " + what + ", found " + n); return t.replace(a, b); }
function unSys(s) { SYS.forEach(([a, b], i) => { s = once(s, a, b, "SCN_SYS tweak " + (i + 1)); }); return s; }
const lineRe = (name) => new RegExp("^const " + name + " = .*$", "m");
function unset3m(text) {   /* set3m Worker source -> vis1c Worker source, asserting the set3m delta is exactly the expected one */
  for (const name of ["TB_LIVE_TOOLS", "TB_TOOL_IDS"]) {
    const exp = "const " + name + " = [" + ALL22.map((i) => "'" + i + "'").join(", ") + "];", got = text.match(lineRe(name))[0];
    if (got !== exp) throw new Error("set3m: " + name + " is not the 22 ids"); text = text.replace(got, "const " + name + " = [" + ALL21.map((i) => "'" + i + "'").join(", ") + "];");
  }
  text = once(text, S3_BLOCK, "", "set3m TB_SET3 block");
  S3_SUBS.forEach(([a, b], i) => { text = once(text, a, b, "set3m tbSet3 use " + (i + 1)); });
  if (/game_win_chance|TB_SET3|tbSet3/.test(text)) throw new Error("set3m: leftover set3m reference");
  return text;
}
function unvis1(text) {   /* set3m/vis1 Worker source -> final3 Worker source, asserting the set3m and vis1 deltas are exactly the expected ones */
  const f3 = fs.readFileSync(F3W, "utf8"); text = unset3m(text);
  for (const name of ["TB_LIVE_TOOLS", "TB_TOOL_IDS"]) {
    const exp = "const " + name + " = [" + ALL21.map((i) => "'" + i + "'").join(", ") + "];", got = text.match(lineRe(name))[0];
    if (got !== exp) throw new Error("vis1: " + name + " is not the 21 ids"); text = text.replace(got, f3.match(lineRe(name))[0]);
  }
  const rl = text.match(lineRe("ROUTER_TOOLS"))[0], fl = f3.match(lineRe("ROUTER_TOOLS"))[0];
  const rt = JSON.parse(rl.slice("const ROUTER_TOOLS = ".length, -1)), ft = JSON.parse(fl.slice("const ROUTER_TOOLS = ".length, -1));
  if (JSON.stringify(Object.keys(rt)) !== JSON.stringify(Object.keys(ft).concat(NEW2).sort())) throw new Error("vis1: ROUTER_TOOLS ids");
  for (const k of Object.keys(ft)) if (JSON.stringify(rt[k]) !== JSON.stringify(ft[k])) throw new Error("vis1: ROUTER_TOOLS entry changed: " + k);
  for (const k of NEW2) { const s = rt[k]; if (!s || !Array.isArray(s.m) || typeof s.d !== "string" || typeof s.p !== "object" || s.g !== 0 || !Array.isArray(s.e) || s.e.length !== 2) throw new Error("vis1: ROUTER_TOOLS new entry shape: " + k); }
  text = text.replace(rl, fl);
  SYSJ.forEach(([a, b], i) => { text = once(text, a, b, "Worker SCN_SYS tweak " + (i + 1)); });
  if (text !== f3 && text.split("\n").length !== f3.split("\n").length) throw new Error("vis1: line count");
  return text;
}
const J19 = '"tb":' + JSON.stringify(ALL19), J21 = '"tb":' + JSON.stringify(ALL21);
function cfg21(t, pv) { if (t.indexOf('"tb":') < 0) return t; return once(t, J19, '"tb":' + JSON.stringify(ALL22.concat(SET3)), "19-id tb list"); }   /* set3m3: TB_SET3_VISIBLE = true -> the 27 ids on every host (Production too) */   /* set3m: 22 ids (+ the 5 Set 3 ids in Preview only) */
function wrapOld(OW) {   /* the base Worker, with its ask-config tb list mapped to the vis1 21 ids (exact string swap); everything else untouched */
  const o = Object.create(OW);
  o.fetch = async function (req, env, ctx) {
    const r = await OW.fetch.call(OW, req, env, ctx); let p = ""; try { p = new URL(req.url).pathname; } catch (e) {}
    if (!/^\/api\/ask-config\/?$/.test(p)) return r;
    const t = await r.text(), h = new Headers(r.headers), t2 = cfg21(t, previewOnly(env, new URL(req.url))); if (h.has("content-length")) h.set("content-length", String(Buffer.byteLength(t2)));
    return new Response(t2, { status: r.status, statusText: r.statusText, headers: h });
  };
  return o;
}
module.exports = { ALL19, NEW2, ALL21, NEW3, ALL22, SET3, previewOnly, unSys, unvis1, unset3m, cfg21, wrapOld, F3W };
