/* Matcher rules for conf_race_alive (Lane B). A rule fires only on wording we can prove: a status word (alive, in the mix, out of it, eliminated, can still reach) tied to the conference championship game
 * or race, with exactly one conference (typed, or the conference page) or exactly one team. Everything else returns null (the router decides).
 * Left to other tools or to the router on purpose: chances/odds/percent (team_snapshot), "what does X need" (team_needs), playoff or bye wording (playoff_field), national title, what-if wording,
 * single-game wording, compare/versus, and "clinched" (a gated word: answered only through the router with the neutral card until the rules are verified).
 * KTTB.core.norm() drops the possessive 's: "Utah's" -> "utah". */
(function (root) {
  "use strict";
  var TB = root.KTTB || (typeof require !== "undefined" ? require("../registry.js") : null), C = TB.core;

  var CHAMP = /\b(championship game|conference championship|champ game|conference title|conf title|title game|title race|championship race|championship)\b/;
  var RACE = /\b(race|hunt)\b/;
  var IN_RE = /\b(alive|in the (mix|race|hunt|running)|in contention|can still (make|reach|get to|get into|play in)|still (make|reach|get to|get into|have a shot|have a path|in position))\b/;
  var OUT_RE = /\b(eliminated|ruled out|knocked out|mathematically (out|eliminated)|out of (it|contention|the ([a-z0-9]+ ){0,4}(race|running|mix|hunt|championship game|conference championship)))\b/;
  var NOT_ME = /\b(national|playoffs?|cfp|bye|bowls?|seeds?|chances?|odds|probabilit\w*|percent|percentage|likely|likelihood|need|needs|must|have to|has to|scenarios?|what if|beats?|loses?|wins out|clinch\w*|compare|vs|versus|top \d+|rank\w*|schedule|tiebreak\w*|tie breakers?|predict\w*|who will|who wins|will win)\b/;

  var ALIASES = { acc: ["acc"], big10: ["big 10", "big ten", "b1g"], big12: ["big 12", "big twelve"], sec: ["sec"], American: ["american", "aac", "american athletic"], usa: ["conference usa", "cusa", "c usa"],
    midam: ["mac", "mid american", "midamerican", "mid american conference", "mac conference"], mwest: ["mountain west", "mwc"], pac12: ["pac 12", "pac12"], belt: ["sun belt", "sunbelt"], ind: ["independents", "independent"] };
  function confsIn(n) {   /* distinct conference codes named in the text (every conference counts, so "Big 12 or SEC" is two). The LONGER name wins, as in core (CONTRACT 4.2.1): "American" inside "Mid-American" is not the American. */
    var t = " " + n + " ", hits = [];
    Object.keys(ALIASES).forEach(function (k) { ALIASES[k].forEach(function (a) { var at = " " + a + " ", i = t.indexOf(at); while (i >= 0) { hits.push({ k: k, s: i, e: i + at.length, len: a.length }); i = t.indexOf(at, i + 1); } }); });
    var out = [];
    hits.forEach(function (h) { if (hits.some(function (o) { return o !== h && o.s <= h.s && o.e >= h.e && o.len > h.len; })) return; if (out.indexOf(h.k) < 0) out.push(h.k); });
    return out;
  }
  function status(n) { var i = IN_RE.test(n), o = OUT_RE.test(n); return i && o ? "" : o ? "out" : i ? "in" : null; }   /* null: no status word; "": both kinds of word, no filter */
  function build(conf, team, st) { var p = {}; if (conf) p.conference = conf; if (team) p.team = team; if (st) p.status = st; return p; }

  TB.rules("conf_race_alive", [
    { id: "alive-conf", conf: 0.92, test: function (n, mc) {
      var st = status(n), cs = confsIn(n);
      if (st === null || NOT_ME.test(n) || mc.nonFbs || mc.teams.length) return null;
      if (cs.length > 1 || (cs.length === 1 && cs[0] === "ind")) return null;
      if (!CHAMP.test(n)) return null;
      var conf = cs[0] || (mc.page && mc.page.mode === "conference" && mc.page.conf) || null;
      return conf ? build(conf, null, st) : null;
    } },
    { id: "alive-conf-race", conf: 0.9, test: function (n, mc) {   /* no "championship" word: the conference named in the text with "race"/"hunt", or the conference page itself */
      var st = status(n), cs = confsIn(n), onPage = mc.page && mc.page.mode === "conference" && mc.page.conf;
      if (st === null || NOT_ME.test(n) || mc.nonFbs || mc.teams.length || CHAMP.test(n)) return null;
      if (cs.length > 1 || (cs.length === 1 && cs[0] === "ind")) return null;
      if (cs.length === 1) return RACE.test(n) ? build(cs[0], null, st) : null;
      return onPage ? build(onPage, null, st) : null;
    } },
    { id: "out-conf-bare", conf: 0.88, test: function (n, mc) {   /* "Who's eliminated in the SEC?": a plain out word, one conference (typed, or the conference page), no team, no other topic */
      if (!/\b(eliminated|ruled out|knocked out)\b/.test(n) || NOT_ME.test(n) || mc.nonFbs || mc.teams.length) return null;
      var cs = confsIn(n), onPage = mc.page && mc.page.mode === "conference" && mc.page.conf;
      if (cs.length > 1 || (cs.length === 1 && cs[0] === "ind")) return null;
      var conf = cs[0] || onPage || null;
      return conf ? build(conf, null, "out") : null;
    } },
    { id: "alive-team", conf: 0.92, test: function (n, mc) {
      var st = status(n), cs = confsIn(n);
      if (st === null || NOT_ME.test(n) || mc.nonFbs || mc.teams.length !== 1 || cs.length > 1) return null;
      if (!(CHAMP.test(n) || (RACE.test(n) && !/\bplayoff\b/.test(n)))) return null;
      var t = TB.oneTeam(mc), conf = cs.length === 1 && cs[0] !== "ind" ? cs[0] : null;
      if (cs.length === 1 && cs[0] === "ind") return null;
      if (t.team) return build(conf, t.team, null);
      if (t.clarify) return { params: build(conf, null, null), clarify: t.clarify };
      return null;
    } }
  ]);
})(typeof self !== "undefined" ? self : globalThis);
