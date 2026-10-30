/* Ask KickTip simulation worker. Runs the season simulation in the visitor's browser (classic worker, same-origin script, no network).
   Messages in:  {op:'bundle', model, bundle}                                   store one model's bundle (sent once per model)
                 {op:'run', id, model, forced, constraints, per, chunks, minChunks, budget, seedBase, baseOnly}
   Messages out: {id, type:'progress', done, total} ... {id, type:'done', N, before, after, ms} | {id, type:'error'}
   The run is split into chunks of `per` seasons. The baseline ("before") of each chunk is cached per model and seed, so a follow-up question only pays for the scenario side.
   Adaptive size: after the first chunk, if the projected total exceeds `budget` ms the run is cut to fewer chunks (never fewer than minChunks); the answer always reports the N actually used. */
importScripts('/assets/ks/sim.js');
var bundles = {}, baseCache = {}, KEYS = ['ccg', 'title', 'cfp12', 'bye', 'top4', 'exp_wins'];
function blank(n) { var o = {}; KEYS.forEach(function (k) { o[k] = new Float64Array(n); }); return o; }
function add(acc, r, w) { KEYS.forEach(function (k) { var a = acc[k], b = r[k]; for (var i = 0; i < a.length; i++) a[i] += b[i] * w; }); }
self.onmessage = function (e) {
  var m = e.data;
  if (m.op === 'bundle') { bundles[m.model] = m.bundle; Object.keys(baseCache).forEach(function (k) { if (k.indexOf(m.model + '|') === 0) delete baseCache[k]; }); return; }
  if (m.op !== 'run') return;
  try {
    var bundle = bundles[m.model]; if (!bundle) throw new Error('no bundle');
    var n = bundle.n, per = m.per, chunks = m.chunks, parts = [], t0 = Date.now(), c, seed, b, a;
    for (c = 0; c < chunks; c++) {
      seed = (m.seedBase || 20261) + c;
      var key = m.model + '|' + seed;
      b = baseCache[key] || (baseCache[key] = KTSim.simulate(bundle, { seasons: per, seed: seed }));
      a = m.baseOnly ? null : KTSim.simulate(bundle, { seasons: per, seed: seed, forced: m.forced, constraints: m.constraints });
      parts.push([b, a]);
      if (c === 0 && m.budget) { var per1 = Date.now() - t0, proj = per1 * chunks; if (proj > m.budget) chunks = Math.max(m.minChunks || 3, Math.min(chunks, Math.floor(m.budget / per1))); }
      self.postMessage({ id: m.id, type: 'progress', done: (c + 1) * per, total: chunks * per });
    }
    var before = blank(n), after = m.baseOnly ? null : blank(n), w = 1 / parts.length;
    parts.forEach(function (p) { add(before, p[0], w); if (after) add(after, p[1], w); });
    self.postMessage({ id: m.id, type: 'done', N: parts.length * per, before: before, after: after, ms: Date.now() - t0 });
  } catch (err) { self.postMessage({ id: m.id, type: 'error' }); }
};
