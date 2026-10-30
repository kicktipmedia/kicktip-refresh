/* Matcher rules for team_path (Lane P4). Params: {team, goal[, focus]}. Spec R1: any need word (need, needs, has to happen, how many wins, ...) belongs to team_needs, even when "path" is present.
 * Otherwise "path to" / "road to" / "how can X make|reach|get|earn" / "how many games can X lose" with goal championship_game, playoff or bye is team_path. "Win the conference" is not ours
 * (team_needs keeps it). goalOf is the same function team_needs uses, with "conference" returning null here, so the two tools never claim the same words. conf 0.97 (clear of every older rule at 0.92 or lower, which would otherwise tie and return nothing); the two tools stay disjoint by the NEED test, not by confidence. */
(function (root) {
  "use strict";
  var TB = root.KTTB || (typeof require !== "undefined" ? require("../registry.js") : null);
  var NOT_ME = /\b(what if|beats?|beating|loses? to|if .{1,40} (wins|loses)|schedule|standings?|tiebreak\w*|compare|vs|versus|spread|bet|bets|wagers?|top \d+|poll|20\d\d|last season|last year|all time|mathematical\w*|clinch\w*|eliminat\w*|still alive|alive)\b/;
  var OTHER_SPORT = /\b(basketball|hoops|baseball|softball|hockey|soccer|volleyball|wrestling|lacrosse|nba|wnba|nfl|mlb|nhl|mls|march madness|nascar|tennis|golf)\b/;
  var NEED = /\b(need|needs|needed|has to happen|have to happen|what has to happen|must happen|help to get|needs help|need help)\b|\bhow many wins\b/;
  var PATH = /\b(path|paths|road)\b|\bhow (can|could|would|does|do) .{1,40} (make|reach|get|earn)\b|\bhow many (games|losses) can .{1,40} lose\b|\bminimum record\b|\bfewest wins\b|\b(can|could) .{1,30} afford to lose\b|\bgames? .{1,30} (cant|cannot|can not) lose\b/;
  function goalOf(n) {
    if (/\bbyes?\b/.test(n)) return "bye";
    if (/\b(championship game|ccg)\b/.test(n)) return /\bwin\b.*\bchampionship game\b/.test(n) ? null : "championship_game";
    if (/\bwin (the |their )?(conference|league|big 12|big ten|sec|acc|mac|american|sun belt|mountain west|pac 12|conference usa|c usa)\b|\bconference (title|championship)\b/.test(n)) return "conference";
    if (/\b(playoff|12 team|the field|make the 12|get in|make it in|get into|make it|in the playoff)\b/.test(n)) return "playoff";
    return null;
  }
  function focusOf(n) {
    if (/\bhow many (games|losses) can\b|\bafford to lose\b|\bgames? .{1,30} (cant|cannot|can not) lose\b|\bhow many (games|losses) .{1,20}lose\b/.test(n)) return /\b(cant|cannot|can not) lose\b/.test(n) && !/\bhow many\b/.test(n) ? "key_games" : "losses_allowed";
    if (/\b(minimum record|fewest wins|least wins|how few wins|minimum wins)\b/.test(n)) return "min_record";
    if (/\b(outside results|other results|results (need )?to go|root for|one way)\b/.test(n)) return "help";
    return null;
  }
  function team1(mc) { var t = TB.oneTeam(mc); return t.clarify ? { clarify: t.clarify } : t.team ? { team: t.team } : {}; }
  function build(n, mc) {
    if (mc.nonFbs || mc.teams.length > 1 || OTHER_SPORT.test(n)) return null;
    var g = goalOf(n); if (g === "conference") return null;
    var f = focusOf(n), p;
    if (!g && !PATH.test(n)) return null;
    var t = team1(mc);
    if (!t.team && !t.clarify && mc.page && mc.page.mode === "team" && mc.page.team && mc.teams.length === 0) t = { team: mc.page.team };
    if (t.clarify) { p = {}; if (g) p.goal = g; if (f) p.focus = f; return { params: p, clarify: t.clarify }; }
    if (!t.team) return null;
    p = { team: t.team }; if (g) p.goal = g; if (f) p.focus = f;     /* no goal stated: core asks which goal (which_goal chooser, no model) */
    return p;
  }
  TB.rules("team_path", [
    { id: "tp-path", conf: 0.97, test: function (n, mc) { return PATH.test(n) && !NEED.test(n) && !NOT_ME.test(n) && !focusOf(n) ? build(n, mc) : null; } },
    /* a stated focus ("minimum record", "fewest wins", "how many games can X lose") is a stronger signal; 0.98 keeps it clear of team_snapshot's "record" rule (0.90) and conf_race_alive's team rule (0.92), because the matcher returns nothing when two tools are within 0.05 */
    { id: "tp-focus", conf: 0.98, test: function (n, mc) { return PATH.test(n) && !NEED.test(n) && !NOT_ME.test(n) && focusOf(n) ? build(n, mc) : null; } }
  ]);
})(typeof self !== "undefined" ? self : globalThis);
