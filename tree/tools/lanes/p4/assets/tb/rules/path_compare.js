/* Matcher rules for path_compare (Lane P4). Params: {teams:[a,b][, goal]}. Two teams named, path/road wording, no need word. conf 0.96: "compare" is what-if wording to the core matcher, which only lets a
 * rule through at 0.95 or more, and "Compare Utah's and Arizona's path to a bye" must reach this tool. A missing goal is asked for (which_goal). */
(function (root) {
  "use strict";
  var TB = root.KTTB || (typeof require !== "undefined" ? require("../registry.js") : null);
  var NOT_ME = /\b(what if|beats?|beating|loses? to|if .{1,40} (wins|loses)|schedule|standings?|tiebreak\w*|spread|bet|bets|wagers?|top \d+|poll|20\d\d|last season|last year|all time|mathematical\w*|clinch\w*|eliminat\w*|still alive|alive)\b/;
  var OTHER_SPORT = /\b(basketball|hoops|baseball|softball|hockey|soccer|volleyball|wrestling|lacrosse|nba|wnba|nfl|mlb|nhl|mls|march madness|nascar|tennis|golf)\b/;
  var NEED = /\b(need|needs|needed|has to happen|have to happen|what has to happen|must happen|help to get|needs help|need help)\b|\bhow many wins\b/;
  var PATHW = /\b(path|paths|road)\b/, TWO = /\b(compare|compared|vs|versus|or|and|than|between|against)\b/;
  function goalOf(n) {
    if (/\bbyes?\b/.test(n)) return "bye";
    if (/\b(championship game|ccg)\b/.test(n)) return "championship_game";
    if (/\b(playoff|12 team|the field|make the 12|get in|make it in|get into|in the playoff)\b/.test(n)) return "playoff";
    return null;
  }
  function slug1(t) { if (t.ask || t.ids.length !== 1) return { clarify: { param: "team", options: t.ids.slice(), alias: t.alias, bare: !!t.bare } }; return { team: t.ids[0] }; }
  TB.rules("path_compare", [
    { id: "pc-path", conf: 0.96, test: function (n, mc) {
      if (!PATHW.test(n) || !TWO.test(n) || NEED.test(n) || NOT_ME.test(n) || OTHER_SPORT.test(n) || mc.nonFbs || mc.teams.length !== 2) return null;
      if (/\bwin (the |their )?(conference|league|big 12|big ten|sec|acc|mac|american|sun belt|mountain west|pac 12|conference usa|c usa)\b|\bconference (title|championship)\b(?! game)/.test(n)) return null;
      var a = slug1(mc.teams[0]), b = slug1(mc.teams[1]), g = goalOf(n), p = {};
      if (a.clarify) return { params: g ? { goal: g } : {}, clarify: a.clarify };
      if (b.clarify) return { params: { teams: [a.team] }, clarify: { param: "teams", options: b.clarify.options, alias: b.clarify.alias, bare: !!b.clarify.bare } };
      if (a.team === b.team) return null;
      p.teams = [a.team, b.team]; if (g) p.goal = g; return p;
    } }
  ]);
})(typeof self !== "undefined" ? self : globalThis);
