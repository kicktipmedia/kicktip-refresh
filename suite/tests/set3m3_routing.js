/* set3m3 routing (Set 3 visible everywhere; supersedes set3m2_routing). Was set3m2: (1) "Did Indiana move up in the committee's rankings?" (and kin) answer exactly as vis1c wherever cfp_committee_rankings is not visible
 * (Production list, and dark analysis), and go to cfp only where cfp is visible (Preview list = 22 + TB_SET3_IDS). (2) Production state (the 22 live ids, Set 3 dark):
 * every bank row (QA bank + set3a/b/c banks + BR rows) is identical to vis1c or a no-answer -> game_win_chance change; no row loses its answer. usage: node tests/set3m2_routing.js <tree> <vis1c tree> <bank.json> */
"use strict";
const fs = require("fs"), path = require("path"), cp = require("child_process");
const [tree, base, bankPath] = process.argv.slice(2).map(p => path.resolve(p));
let n = 0, bad = 0; const chk = (k, c, x) => { n++; if (c) console.log("PASS " + k); else { bad++; console.log("FAIL " + k + (x !== undefined ? " :: " + JSON.stringify(x).slice(0, 400) : "")); } };
const lists = t => { const W = fs.readFileSync(path.join(t, "_worker.js"), "utf8"), g = k => { const m = new RegExp("const " + k + " = (\\[[^\\]]*\\]);").exec(W); return m ? JSON.parse(m[1].replace(/'/g, '"')) : []; }; return { live: g("TB_LIVE_TOOLS"), set3: g("TB_SET3_IDS") }; };
const LN = lists(tree), LB = lists(base);
/* questions: QA bank + the three lane banks + extras */
const qs = new Set(JSON.parse(fs.readFileSync(bankPath, "utf8")).rows.map(r => r.text));
JSON.parse(fs.readFileSync(path.join(__dirname, "set3a", "bank_set3a.json"), "utf8")).rows.forEach(r => (r.text || r.q) && qs.add(r.text || r.q));
const BRm = /const BR = (\[[^\]]*\]);/.exec(fs.readFileSync(path.join(__dirname, "lib", "routes.js"), "utf8")); JSON.parse(BRm[1]).forEach(t => qs.add(t));
const MOVEQ = ["Did Indiana move up in the committee's rankings?", "Did Utah drop in the committee rankings?", "Did Ohio State fall in the CFP rankings?", "Has BYU moved in the committee rankings?", "Did Oregon climb in the college football playoff rankings?"];
MOVEQ.forEach(q => qs.add(q));
["Will Utah beat BYU?", "Will Indiana beat Ohio State?", "When did Utah last make the playoff?", "Utah record by season", "BYU all-time vs Utah", "Pac-12 champions", "Committee top 12", "Where is Indiana in the committee rankings?", "My teams", "How are my teams doing?", "if Utah wins the Big 12", "How many points per game does BYU score?"].forEach(q => qs.add(q));   /* the smoke / charter questions */
const tmp = path.join(require("os").tmpdir(), "set3m3-q-" + process.pid + ".json"); fs.writeFileSync(tmp, JSON.stringify({ rows: [...qs].map(t => ({ text: t })) }));
const script = `const T=require("/workspace/kicktip-scn-b3/tests/lib/tbq.js")(process.argv[1]);const rows=JSON.parse(require("fs").readFileSync(process.argv[2],"utf8")).rows;const live=JSON.parse(process.argv[3]),dark=process.argv[4]==="1";
(async()=>{T.TB.setLive(live);const o={};for(const r of rows){const m=await T.match(r.text,dark?{dark:true}:undefined);o[r.text]=m?{tool:m.tool,params:m.params,clarify:m.clarify||null}:null}process.stdout.write(JSON.stringify(o))})();`;
const RT = (t, live, dark) => JSON.parse(cp.execFileSync("node", ["-e", script, t, tmp, JSON.stringify(live), dark ? "1" : "0"], { maxBuffer: 64 << 20 }).toString());
const vProd = RT(base, LB.live), vDark = RT(base, LB.live, true);
const W = fs.readFileSync(path.join(tree, "_worker.js"), "utf8"), VIS = /^const TB_SET3_VISIBLE = true;/m.test(W);
const PROD = VIS ? LN.live.concat(LN.set3) : LN.live;
const nProd = RT(tree, PROD);
const S = JSON.stringify, all = [...qs];
chk("TB_SET3_VISIBLE = true (Set 3 live on every host)", VIS);
chk("lists: vis1c 21 live; Production now 27 (21 + game_win_chance + 5 Set 3)", LB.live.length === 21 && PROD.length === 27 && S(LN.live.filter(x => !LB.live.includes(x))) === S(["game_win_chance"]) && LN.set3.length === 5, [LB.live.length, PROD.length]);
for (const q of MOVEQ) chk("[production, cfp visible] " + q + " -> cfp_committee_rankings", !!(nProd[q] && nProd[q].tool === "cfp_committee_rankings"), nProd[q]);
const ch = all.filter(q => S(vProd[q]) !== S(nProd[q])).map(q => ({ q, was: vProd[q], now: nProd[q] }));
console.log("PRODUCTION-STATE ROUTING CHANGES vs vis1c (" + all.length + " questions): " + ch.length); ch.forEach(d => console.log("  CHANGE \"" + d.q + "\": " + S(d.was) + " -> " + S(d.now)));
const lost = ch.filter(d => d.was && !d.now); chk("production state: no row goes from an answer to no answer (" + lost.length + ")", !lost.length, lost);
const EXP = path.join(__dirname, "set3m3_expected_changes.json");
if (process.env.WRITE_EXPECTED) fs.writeFileSync(EXP, JSON.stringify(ch, null, 1) + "\n");
const exp = JSON.parse(fs.readFileSync(EXP, "utf8"));
chk("production-state change list equals the reviewed list exactly (" + exp.length + " rows)", S(exp) === S(ch), { extra: ch.filter(d => !exp.some(e => S(e) === S(d))).map(d => d.q), missing: exp.filter(e => !ch.some(d => S(e) === S(d))).map(e => e.q) });
fs.unlinkSync(tmp); console.log(n + " checks, " + bad + " failed"); process.exit(bad ? 1 : 0);
