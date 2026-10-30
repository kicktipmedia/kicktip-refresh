#!/usr/bin/env node
/* scn_a2 model comparison (70b vs ~8b) for the scenario write-up.
   It sends the 25 fixed fact objects in tests/eval_facts.json to a PREVIEW deployment's /api/ask (mode "scn", Preview-only body._model) and scores every reply with the SAME validator the browser uses (assets/ks/scnai.js).
   NEVER run against Production: the script refuses any host that is not *.pages.dev, refuses unless /api/ask-config answers x-kt-env: preview, and refuses a Worker that does not honor _model (diag.model must echo the model asked for).
   Preview uses Turnstile TEST keys, so a scripted POST with the Turnstile test token works (default token XXXX.DUMMY.TOKEN.XXXX, override with KT_TS_TOKEN). No secret is read or printed.
   Plan: default = the first 20 fixtures x 2 models = 40 calls (fits the Preview scenario sub-cap of 60/day with room to spare); --full = all 25 x 2 = 50 calls; --models 8b (or 70b) = one model only; --limit N = first N fixtures.
   usage:  node tests/eval_models.js --base https://<preview>.pages.dev [--full] [--models both|70b|8b] [--limit N] [--pause-ms 1500] [--out logs/eval_models.json] [--tree work/outb3]
           node tests/eval_models.js --dry [--tree work/outb3]     (offline: a local copy of the Worker with a stub AI binding; proves the plumbing and the scoring, spends nothing)
   Decision rule printed at the end: switch SCN.MODEL to the 8b id only if its pass rate is >= 90% AND no more than 5 points below the 70b rate (and the same hold-up: no worse than 1 hallucinated number/name per 25). */
"use strict";
const fs = require("fs"), path = require("path");
const A = process.argv.slice(2), opt = (k, d) => { const i = A.indexOf("--" + k); return i < 0 ? d : (A[i + 1] && !A[i + 1].startsWith("--") ? A[i + 1] : true); };
const TREE = path.resolve(opt("tree", path.join(__dirname, "..", "work", "outb3"))), DRY = !!opt("dry", false), FULL = !!opt("full", false);
const MODELS = { "70b": "@cf/meta/llama-3.3-70b-instruct-fp8-fast", "8b": "@cf/meta/llama-3.1-8b-instruct-fp8" };
const which = opt("models", "both"), PLAN = which === "both" ? ["70b", "8b"] : [which]; if (PLAN.some((m) => !MODELS[m])) { console.error("--models must be both, 70b or 8b"); process.exit(2); }
const FX = require("./eval_facts.json").items, LIMIT = Number(opt("limit", FULL ? 25 : 20)) || 20, ITEMS = FX.slice(0, Math.min(LIMIT, FX.length));
const PAUSE = Number(opt("pause-ms", 1500)), TOKEN = process.env.KT_TS_TOKEN || "XXXX.DUMMY.TOKEN.XXXX", BASE = String(opt("base", ""));
const H = require("./lib/scn_harness.js")(TREE), K = require(path.join(TREE, "assets/ks/scnai.js")), known = []; H.B.teams.forEach((t) => { if (t.n) known.push(t.n); if (t.f && t.f !== t.n) known.push(t.f); if (t.s) known.push(t.s); });
const score = (prose, f) => K.validate(prose, f, { known, vocab: H.EX.vocab(f) });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms)), pctl = (a, p) => { if (!a.length) return null; const s = a.slice().sort((x, y) => x - y); return s[Math.min(s.length - 1, Math.ceil(p * s.length) - 1)]; }, avg = (a) => a.length ? Math.round(a.reduce((x, y) => x + y, 0) / a.length * 1000) / 1000 : null;
function plan() { const p = []; for (const it of ITEMS) for (const m of PLAN) p.push({ it, m }); return p; }
async function main() {
  const calls = plan(); console.log((DRY ? "[dry-run, offline] " : "Preview run: " + BASE + " ") + "plan: " + ITEMS.length + " fixtures x " + PLAN.length + " model(s) = " + calls.length + " calls" + (calls.length > 55 ? "  (TOO MANY: the Preview scenario sub-cap is 60/day)" : ""));
  let send, rows = [];
  if (DRY) {
    const { loadWorker, makeEnv, installFetch } = await import(path.join(__dirname, "browser", "mock.mjs")), W = await loadWorker(TREE), E = makeEnv(W, { AI_SCN: "on" }); installFetch(E.st); let k = 0;
    E.env.AI = { run: async (model, input) => { const sys = input.messages[0].content; if (!/KickTip writer/.test(sys)) return { response: "{}" }; k++; const f = ITEMS.find((x) => input.messages[1].content.indexOf(JSON.stringify(x.compact)) >= 0) || ITEMS[0], t = f.compact.scenario && f.compact.scenario.teams || [];
      const good = "In this scenario, " + (t[0] || "the team") + " is in the scenario you asked about, and KickTip's numbers show the records on the card. The result depends on games the scenario does not set.", bad = "KickTip's numbers show a 99% chance, so it is a lock. It depends on games the scenario does not set.";
      return { response: JSON.stringify({ v: 1, prose: model === MODELS["8b"] && k % 4 === 0 ? bad : good }), usage: { prompt_tokens: 900, completion_tokens: 70 } }; } };
    send = async (f, model) => { const t0 = Date.now(), r = await W.fetch(new Request("https://preview.kicktip.pages.dev/api/ask", { method: "POST", headers: { Origin: "https://preview.kicktip.pages.dev", "Content-Type": "application/json", "Sec-Fetch-Site": "same-origin", "CF-Connecting-IP": "203.0.113." + (1 + (k % 200)) }, body: JSON.stringify({ mode: "scn", facts: f.compact, cf_turnstile: "good", _model: model }) }), E.env); return { status: r.status, j: await r.json().catch(() => null), ms: Date.now() - t0 }; };
  } else {
    let u; try { u = new URL(BASE); } catch (e) { console.error("--base https://<preview>.pages.dev is required (or use --dry)"); process.exit(2); }
    if (u.protocol !== "https:" || !/\.pages\.dev$/.test(u.hostname)) { console.error("REFUSED: " + u.hostname + " is not a *.pages.dev Preview host. This script never runs against Production."); process.exit(2); }
    const c = await fetch(u.origin + "/api/ask-config"); const env = c.headers.get("x-kt-env"), cj = await c.json().catch(() => ({}));
    if (env !== "preview") { console.error("REFUSED: x-kt-env is " + JSON.stringify(env) + ", not preview."); process.exit(2); }
    if (cj.enabled !== true || cj.scn !== true) { console.error("STOP: ask-config says enabled=" + cj.enabled + " scn=" + cj.scn + ". The Preview needs AI_SCN=on (and the AI binding + Turnstile test keys) first; see FLIP.md."); process.exit(3); }
    send = async (f, model) => { const t0 = Date.now(); const r = await fetch(u.origin + "/api/ask", { method: "POST", headers: { "Content-Type": "application/json", Origin: u.origin }, body: JSON.stringify({ mode: "scn", facts: f.compact, [cj.tokenField || "cf_turnstile"]: TOKEN, _model: model }) }); return { status: r.status, j: await r.json().catch(() => null), ms: Date.now() - t0 }; };
  }
  for (const { it, m } of calls) {
    const model = MODELS[m]; let r; try { r = await send(it, model); } catch (e) { r = { status: 0, j: null, ms: 0, err: String(e && e.message || e).slice(0, 100) }; }
    const j = r.j || {}, row = { id: it.id, model: m, status: r.status, ms: r.ms, worker_ms: j.diag && j.diag.ms, neurons: j.diag && j.diag.neurons, echo_model: j.diag && j.diag.model, usage: j.diag && j.diag.usage, finish: j.diag && j.diag.finish, rawLen: j.diag && j.diag.rawLen, raw: j.diag && j.diag.raw, reason: j.reason };
    if (!DRY && j.diag && j.diag.model && j.diag.model !== model) { console.error("STOP: the Worker used " + j.diag.model + " not " + model + " (is this really a Preview build?)"); process.exit(3); }
    if (r.status === 200 && j.ok === true && j.source === "scn") { const v = score(j.prose, it.facts); row.worker = "ok"; row.valid = v.ok; row.why = v.ok ? null : v.why; row.prose = j.prose; }
    else { row.worker = "fallback"; row.valid = false; row.why = "worker:" + (j.reason || j.error || r.err || r.status); }
    rows.push(row); console.log(it.id + " " + m + " " + (row.valid ? "PASS" : "FAIL " + row.why) + " " + r.ms + "ms" + (row.neurons != null ? " " + row.neurons + "n" : "")); if (!DRY && PAUSE) await sleep(PAUSE);
    if (!DRY && (r.status === 429 || j.reason === "cap" || j.error === "cap")) { console.error("STOP: a cap answered. Not retrying."); break; }
  }
  const sum = {}; for (const m of PLAN) { const r = rows.filter((x) => x.model === m), ok = r.filter((x) => x.valid), why = {}; r.filter((x) => !x.valid).forEach((x) => { const k = String(x.why).split(":")[0]; why[k] = (why[k] || 0) + 1; });
    sum[m] = { calls: r.length, pass: ok.length, pass_rate: r.length ? Math.round(ok.length / r.length * 1000) / 1000 : null, fail_reasons: why, hallucinated: r.filter((x) => /^(number|name|rule|unknown)/.test(String(x.why))).length, latency_ms_avg: avg(r.map((x) => x.ms)), latency_ms_p95: pctl(r.map((x) => x.ms), 0.95), neurons_avg: avg(r.filter((x) => x.neurons != null).map((x) => x.neurons)) }; }
  console.log("\nSUMMARY " + JSON.stringify(sum, null, 1));
  if (sum["70b"] && sum["8b"]) { const a = sum["70b"], b = sum["8b"], go = b.pass_rate >= 0.9 && b.pass_rate >= a.pass_rate - 0.05 && b.hallucinated <= Math.max(a.hallucinated, Math.ceil(b.calls / 25)); console.log("DECISION: " + (go ? "8b holds (pass " + b.pass_rate + " vs 70b " + a.pass_rate + "): set SCN.MODEL to the 8b id in _worker.js (one line) and rebuild/redeploy" : "keep 70b (8b pass " + b.pass_rate + " vs 70b " + a.pass_rate + ")")); }
  const out = opt("out", DRY ? null : path.join("logs", "eval_models." + new Date().toISOString().replace(/[:.]/g, "-") + ".json")); if (out && out !== true) { fs.mkdirSync(path.dirname(out), { recursive: true }); fs.writeFileSync(out, JSON.stringify({ base: DRY ? "dry" : BASE, plan: PLAN, fixtures: ITEMS.map((x) => x.id), summary: sum, rows }, null, 1)); console.log("wrote " + out); }
  if (DRY) { const bad = rows.filter((x) => x.model === "70b" && !x.valid).length; if (calls.length !== ITEMS.length * PLAN.length || bad || !rows.some((x) => !x.valid)) { console.log("DRY CHECK FAILED"); process.exit(1); } console.log("DRY CHECK: " + calls.length + " calls, plumbing and scoring work (" + rows.filter((x) => !x.valid).length + " stubbed bad replies caught)"); }
}
main().catch((e) => { console.error(e); process.exit(1); });
