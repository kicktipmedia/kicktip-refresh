#!/usr/bin/env node
/* scn_a2 neuron cost re-derivation from the REAL prompt and the 25 real fixtures (no network). usage: node tests/cost_scn.js TREE [measured.json]
   Worker model: neurons = (input_tokens x inn + output_tokens x out) / 1e6, rates from AI_MODELS. Input tokens = system prompt chars / 3.9 + facts JSON chars / 3.2 + JSON envelope (40, only if JSON mode) + framing (20) -- the same constants the Worker uses.
   Output tokens: REALISTIC 130 (70b worst case, as for the ask), or 90 (typical: ~60 words plus the JSON wrapper). 8b has no JSON mode and no calibration, so its worst case uses the full max_tokens (220).
   If a Preview eval log (tests/eval_models.js --out) is given, its measured diag.neurons averages are printed beside the estimates. Asserts the write-up cost never exceeds one ask worst case. */
"use strict";
const path = require("path"), fs = require("fs"); const TREE = path.resolve(process.argv[2] || "work/outb3"); let n = 0, bad = 0;
const ck = (ok, w, x) => { n++; if (!ok) { bad++; console.log("FAIL " + w + (x !== undefined ? " :: " + JSON.stringify(x) : "")); } else console.log("PASS " + w); };
(async () => {
  const { loadWorker } = await import(path.join(__dirname, "browser", "mock.mjs")), W = await loadWorker(TREE), T = W._ask, FX = require("./eval_facts.json").items, SCN = T.SCN, ASK = T.ASK, M = T.AI_MODELS;
  const id = { "70b": "@cf/meta/llama-3.3-70b-instruct-fp8-fast", "8b": "@cf/meta/llama-3.1-8b-instruct-fp8" }, cost = (m, inTok, outTok) => (inTok * M[id[m]].inn + outTok * M[id[m]].out) / 1e6;
  const json = (m) => !M[id[m]].nojson, sys = T.SCN_SYS.length, chars = FX.map((x) => JSON.stringify(x.compact).length), mean = chars.reduce((a, b) => a + b, 0) / chars.length, max = Math.max(...chars);
  const tokIn = (fc, m) => Math.ceil(sys / SCN.PROMPT_CHARS_PER_TOKEN + fc / SCN.FACTS_CHARS_PER_TOKEN + (json(m) ? ASK.JSON_ENVELOPE_TOKENS : 0) + ASK.FRAME_TOKENS);
  console.log("system prompt " + sys + " chars; facts JSON over 25 fixtures: mean " + Math.round(mean) + ", max " + max + " chars (Worker limit " + SCN.MAX_FACTS_JSON + ")");
  const meas = process.argv[3] && fs.existsSync(process.argv[3]) ? JSON.parse(fs.readFileSync(process.argv[3], "utf8")) : null, R = {};
  for (const m of ["70b", "8b"]) {
    const typ = cost(m, tokIn(mean, m), 90), real = cost(m, tokIn(max, m), M[id[m]].calibrated ? SCN.REALISTIC_OUT_TOKENS : SCN.MAX_OUT_TOKENS), worker = T.scnWorstNeurons(id[m]);
    R[m] = { typical: typ, realistic_worst: real, worker_worst: worker, in_typ: tokIn(mean, m), in_max: tokIn(max, m) };
    console.log(m + ": input ~" + tokIn(mean, m) + " tokens typical (" + tokIn(max, m) + " largest fixture, " + tokIn(SCN.MAX_FACTS_JSON, m) + " at the Worker's size limit); typical write-up " + typ.toFixed(1) + " neurons; largest fixture with a long reply " + real.toFixed(1) + "; Worker's conservative worst case (limit-size facts) " + worker.toFixed(1) + (meas ? "; measured on Preview " + ((meas.summary[m] || {}).neurons_avg ?? "n/a") : ""));
  }
  const askW = (m) => { const r = M[id[m]], inTok = Math.ceil(T.ASK_SYS.length / ASK.PROMPT_CHARS_PER_TOKEN + (json(m) ? ASK.JSON_ENVELOPE_TOKENS : 0) + ASK.MAX_CHARS / ASK.TEXT_CHARS_PER_TOKEN + ASK.FRAME_TOKENS); return (inTok * r.inn + (r.calibrated ? ASK.REALISTIC_OUT_TOKENS : 256) * r.out) / 1e6; };
  const a70 = askW("70b"); console.log("one home ask worst case on 70b: " + a70.toFixed(2) + " neurons (the caps1 figure, 74.899)");
  ck(Math.abs(a70 - 74.899) < 0.05, "re-derived ask worst case matches the caps1 figure 74.899", a70);
  ck(R["70b"].worker_worst <= a70 + 1e-9, "a write-up's conservative worst case on 70b (" + R["70b"].worker_worst.toFixed(1) + ") is <= one ask's worst case (" + a70.toFixed(1) + ")", R["70b"]);
  ck(R["8b"].worker_worst < R["70b"].worker_worst / 2, "8b write-up costs under half of 70b", R);
  ck(R["70b"].typical <= 72 && R["70b"].worker_worst <= 72, "70b: typical (" + R["70b"].typical.toFixed(1) + ") and conservative worst case (" + R["70b"].worker_worst.toFixed(1) + ") are both at or under the planning figure 72", R["70b"]);
  ck(R["8b"].typical <= 19, "8b: typical (" + R["8b"].typical.toFixed(1) + ") is at or under the planning figure 19 (its conservative worst case is " + R["8b"].worker_worst.toFixed(1) + ", from the full max_tokens)", R["8b"]);
  // daily budget: the 150/day ask cap is sized so 150 x 74.9 = 11,235 (caps1). A ticketed write-up is NOT counted in that 150, so it is extra spend.
  const FREE = 10000, CAP = ASK.DAY_CAP, SUB = SCN.DAY_CAP; console.log("\nDAILY BUDGET (free allowance " + FREE + " neurons/day, ask cap " + CAP + ", scenario sub-cap " + SUB + ")");
  for (const m of ["70b", "8b"]) { const w = R[m].worker_worst, t = R[m].typical;
    console.log("  write-ups on " + m + ": " + SUB + " x " + t.toFixed(1) + " typical = " + Math.round(SUB * t) + " neurons; " + SUB + " x " + w.toFixed(1) + " worst = " + Math.round(SUB * w) + "; if every one is extra to a full " + CAP + " asks at " + a70.toFixed(1) + " worst = " + Math.round(CAP * a70 + SUB * w) + " (" + (CAP * a70 + SUB * w <= FREE ? "within" : "OVER") + " " + FREE + "); typical asks (~55) + typical write-ups = " + Math.round(CAP * 55 + SUB * t) + " (" + (CAP * 55 + SUB * t <= FREE ? "within" : "OVER") + ")");
    console.log("    largest sub-cap that keeps " + CAP + " worst-case asks + write-ups inside " + FREE + ": " + Math.max(0, Math.floor((FREE - CAP * a70) / w)) + " (worst-case asks alone already use " + Math.round(CAP * a70) + "); with typical asks (~55 each): " + Math.max(0, Math.floor((FREE - CAP * 55) / t)));
  }
  console.log("\n" + n + " checks, " + bad + " failed"); process.exit(bad ? 1 : 0);
})();
