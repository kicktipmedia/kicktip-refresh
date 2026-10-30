/* KickTip question parser (browser + Node). Rule-based, deterministic, no network, no eval. Output is strict JSON of forced outcomes plus flags.
 * It NEVER produces numbers about chances and NEVER produces prose: the UI turns the structure into text (src/web/answer.js).
 *   KTParse.parse(text, aliases[, {choices:{alias: teamIndex}}]) -> {
 *     refusal: bool, refusal_reason: null|"betting_advice", clarify: bool, clarify_reason: null|"ambiguous_team"|"not_modeled"|"no_team"|"unparsed"|"unsupported"|"empty"|"margin"(plain_text = the question without the margin)|"title_scenario",
 *     mentions: [{alias, team: idx|null, candidates: [idx...]}], intent: null|"scenario"|"need"|"baseline",
 *     items: [{kind:"beats", winner, loser, site: null|"winner_home"|"winner_away"} | {kind:"wins_out"|"loses_out", team} | {kind:"wins_n_of_m", team, n, m, scope:"next"|"last"|"remaining"} | {kind:"next_win"|"next_loss", team}],
 *     need: null|{team, goal:"playoff"|"conference"|"title_game"|"bye"}, baseline_team: null|idx }
 * `aliases` = bundle.aliases ({map, ask, nonfbs}; built by src/aliases.py). */
(function (root) {
  "use strict";
  function norm(s) {
    return String(s).replace(/['\u2019]s\b/g, "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().replace(/&/g, " and ").replace(/['\u2019]/g, "").replace(/[^a-z0-9]+/g, " ").replace(/\s+/g, " ").trim();
  }
  var NUMW = { one: 1, two: 2, three: 3, four: 4, five: 5, six: 6, seven: 7, eight: 8, nine: 9, ten: 10, a: 1 };
  function num(x) { return /^\d+$/.test(x) ? parseInt(x, 10) : (NUMW[x] || null); }

  // betting-advice detector: any hit -> refusal, nothing else is parsed
  var REFUSE = [
    /\b(bet|bets|betting|bettor|bettors|wager|wagers|wagering|parlay|parlays|teaser|teasers|moneyline|money line|sportsbook|sportsbooks|bookie|bookies|bookmaker|gamble|gambling|handicap|handicapper|vig|prop|props|juice play)\b/,
    /\bcover(s|ed|ing)?\b/, /\bspread\b|\bspreads\b|\bats\b|\bagainst the spread\b|\bpoint spread\b/, /\bover under\b|\bover\b.*\bunder\b.*\b(points?|total)\b/, /\b(total points?|the total)\b.*\b(over|under)\b/,
    /\b(best|top|free|lock|locks|sure|safe|hammer|smash|fade|tail|value|can t miss|cant miss) (bet|bets|pick|picks|play|plays)\b/,
    /\bshould i (take|back|fade|pick|play|put|lay|place|bet|tail|hammer|smash)\b/, /\bwho should i (pick|take|back|choose|go with|tail)\b/,
    /\b(lay|place|put|drop|throw) (some )?(money|cash|dollars|\d+|a bet|it all|units?)\b/, /\bworth (betting|a bet|backing)\b/, /\b(my|the) (pick|picks|play|plays) (of|for) the (week|day|weekend)\b/,
    /\bmake me (money|rich)\b/, /\bwhat s the play\b/, /\bwho do i (back|take|like)\b/, /\b(units|unit size)\b/, /\block (of|for) the (week|day|weekend)\b/,
    /\b(?:give me|got|any|need|send me|drop me) (?:a |an |some )?(?:lock|locks|tip|tips|sure thing)\b/, /^(?:fade|tail|hammer|smash) /, /\b(?:tips|advice) (?:for|on) betting\b/
  ];
  var WIN_V = "(?:beats?|beat|defeats?|defeat|tops?|upsets?|handles?|knocks? off|takes? down|downs?|edges?|outlasts?)";
  var LOSE_V = "(?:loses?|lost|falls?|drops?(?: one)?|stumbles?|gets? upset|is upset|was upset)";
  var NUM_RX = "(\\d+|one|two|three|four|five|six|seven|eight|nine|ten)";

  function buildMatcher(al) {
    if (al._m) return al._m;
    var first = {}, keys = Object.keys(al.map).concat(al.nonfbs || []);
    keys.forEach(function (k) { var tk = k.split(" "); (first[tk[0]] = first[tk[0]] || []).push(tk); });
    for (var f in first) first[f].sort(function (a, b) { return b.length - a.length; });
    var m = { first: first }; try { Object.defineProperty(al, "_m", { value: m, enumerable: false }); } catch (e) {}
    return m;
  }
  function scan(tokens, al) {
    var M = buildMatcher(al), out = [], i = 0, mentions = [];
    while (i < tokens.length) {
      var cand = M.first[tokens[i]], hit = null;
      if (cand) for (var c = 0; c < cand.length; c++) { var tk = cand[c], ok = true; for (var j = 0; j < tk.length; j++) if (tokens[i + j] !== tk[j]) { ok = false; break; } if (ok) { hit = tk; break; } }
      if (hit) { var alias = hit.join(" "); out.push("T" + mentions.length); mentions.push(alias); i += hit.length; } else { out.push(tokens[i]); i++; }
    }
    return { text: out.join(" "), mentions: mentions };
  }

  function emptyResult() { return { refusal: false, refusal_reason: null, clarify: false, clarify_reason: null, mentions: [], intent: null, items: [], need: null, baseline_team: null, clarify_aliases: [] }; }

  function parse(text, al, opts) {
    var res = emptyResult(); opts = opts || {}; var choices = opts.choices || {};
    var n = norm(String(text || "").replace(/[,;]+/g, " zzsplit "));
    if (!n) { res.clarify = true; res.clarify_reason = "empty"; return res; }
    if (/(?:^|\s)[+-]\d{1,2}(?:\.5)?(?=[\s?.,!]|$)/.test(String(text)) && /\b(?:line|spread|favorite|favourite|underdog|dog|number|favored)\b/.test(n)) { res.refusal = true; res.refusal_reason = "betting_advice"; return res; }
    for (var r = 0; r < REFUSE.length; r++) if (REFUSE[r].test(n)) { res.refusal = true; res.refusal_reason = "betting_advice"; return res; }
    var sc = scan(n.split(" "), al), s = sc.text;
    // resolve mentions
    var mentions = sc.mentions.map(function (alias) {
      var ids = al.map[alias] || [], nonfbs = (al.nonfbs || []).indexOf(alias) >= 0 && !ids.length;
      var m = { alias: alias, team: null, candidates: ids.slice() };
      if (nonfbs) { m.nonfbs = true; return m; }
      if (alias in choices) { m.team = choices[alias]; return m; }
      if (ids.length === 1 && (al.ask || []).indexOf(alias) < 0) m.team = ids[0];
      return m;
    });
    res.mentions = mentions.map(function (m) { var o = { alias: m.alias, team: m.team, candidates: m.candidates }; if (m.nonfbs) o.not_modeled = true; return o; });
    var bad = mentions.filter(function (m) { return m.team === null; });
    if (bad.length) {
      var nf = bad.filter(function (m) { return m.nonfbs; });
      res.clarify = true; res.clarify_reason = nf.length ? "not_modeled" : "ambiguous_team";
      res.clarify_aliases = bad.map(function (m) { return m.alias; }).filter(function (a, i, arr) { return arr.indexOf(a) === i; });
      return res;
    }
    if (!mentions.length) { res.clarify = true; res.clarify_reason = "no_team"; return res; }
    if (/\bnational (title|championship|champion|champions)\b|\bwin it all\b/.test(s)) { res.clarify = true; res.clarify_reason = "unsupported"; return res; }
    // c1: margins ("by 10", "by a touchdown"): KickTip simulates wins and losses only. Offer the same question without the margin.
    var MARGIN = /\s+by\s+(?:\d+|a|one|two|three|four|five|six|seven|eight|nine|ten|double digits|at least \d+|more than \d+|over \d+)(?:\s+(?:points?|pts?|touchdowns?|tds?|field goals?|scores?|possessions?))?(?=\s*(?:[,;.?!]|and\b|then\b|while\b|$))/gi;
    if (/\bby (?:\d+|a (?:touchdown|td|field goal|score|point)|double digits|at least \d+|more than \d+|over \d+|(?:one|two|three|four|five|six|seven|eight|nine|ten) (?:points?|touchdowns?|scores?))\b/.test(n)) {
      var plain = String(text).replace(MARGIN, "").replace(/\s{2,}/g, " ").trim();
      if (plain && plain !== String(text).trim()) { res.clarify = true; res.clarify_reason = "margin"; res.plain_text = plain.slice(0, 200); return res; }
    }
    var T = function (k) { return mentions[parseInt(k, 10)].team; };

    // strip filler
    s = s.replace(/\b(?:this|next) (?:week|weekend|saturday|friday|thursday)\b|\bon (?:saturday|friday|thursday)\b|\bin week \d+\b|\bplease\b/g, " ").replace(/\s+/g, " ").trim();
    s = s.replace(/\bboth (T\d+ (?:and T\d+))/g, "$1").replace(/\s+(?:what (?:happens|changes)|then what|what does that do)$/, "");
    // group subjects: "T0 and T1 both win out" -> one clause each
    s = s.replace(/((?:T\d+ (?:and |also )?)+T\d+) (?:both |all )?((?:win|lose) out|(?:win|lose) the rest|run the table)\b/g, function (_, grp, pred) {
      return grp.match(/T\d+/g).map(function (t) { return t + " " + pred; }).join(" and ");
    });
    var clauses = s.split(/\b(?:and|then|while|but|plus|also|meanwhile|whereas|zzsplit)\b/).map(function (c) { return c.replace(/\s+/g, " ").trim(); }).filter(Boolean);
    // keep "wins N of M" intact (no and/comma inside), fine
    var lead = /^(?:what if|what happens if|what would happen if|what about if|how about if|if|suppose|assume|assuming|let s say|lets say|let say|how would things change if|how would it change if|how would that change if|what changes if|what happens when|what if instead|say|imagine|ok|okay|so|now|and|what if instead|what if)\s+/;
    var sawScenario = false, unparsedWithTeam = false, wantsNeed = false, unsupportedTitle = false;
    clauses.forEach(function (c0) {
      var c = c0, prev; do { prev = c; c = c.replace(lead, ""); } while (c !== prev);
      c = c.replace(/^(?:then |that )/, "");
      var m, site = null;
      // --- need / path questions
      var goalPart = null, nteam = null;
      if ((m = c.match(/^(?:what|how) (?:does|do|would|will|must|should|can|could|might) (?:it take for )?T(\d+) (?:to )?(?:need|have|must|do|take|get|make|reach|win|go)\b(.*)$/)) ||
          (m = c.match(/^what T(\d+) (?:needs|must do|has to do|has) to(.*)$/)) || (m = c.match(/^(?:what|how) (?:does|do|would|will) it take for T(\d+) to(.*)$/)) ||
          (m = c.match(/^(?:how (?:can|could|does|do|would|will)|what (?:path|paths|route|routes) (?:does|do)) T(\d+) (.*)$/)) ||
          (m = c.match(/^T(\d+) (?:path|paths|route|road|chances?|hopes) to(.*)$/)) || (m = c.match(/^(?:path|paths|route|road) to(.*) for T(\d+)$/))) {
        var tm, rest;
        if (/^(?:path|paths|route|road) to/.test(c)) { tm = m[2]; rest = " to" + m[1]; } else { tm = m[1]; rest = " " + m[2]; }
        var full = (/^(?:what|how)/.test(c) ? "" : "") + rest;
        var g = null;
        if (/\b(?:championship game|title game|ccg|conference championship game|conference title game|league title game|play in the (?:\w+ )?(?:championship|title) game)\b/.test(full)) g = "title_game";
        else if (/\b(?:first round )?bye\b|\btop 4\b|\btop four\b/.test(full)) g = "bye";
        else if (/\b(?:win|winning|capture|claim|take|earn) (?:the |a |their |that )?(?:\w+ ){0,3}?(?:conference|league|title|championship|crown|big 12|big ten|big 10|sec|acc|pac 12|mountain west|mwc|mac|sun belt|american|aac|c usa|cusa)\b|\bconference (?:title|championship|crown)\b/.test(full)) g = "conference";
        else if (/\b(?:make|reach|get into|get in|get to|qualify for|be in|earn a spot in|land in|make it into|make it to|sneak into|crack|in)\b.*\b(?:cfp|college football playoff|playoff|playoffs|12|top 12|field|12 team field|12 team playoff)\b|\b(?:cfp|college football playoff|playoff|playoffs|top 12|12 team field|12 team playoff)\b/.test(full)) g = "playoff";
        if (g) { res.need = { team: T(tm), goal: g }; wantsNeed = true; return; }
      }
      // --- wins out / loses out
      if ((m = c.match(/^T(\d+) (?:will |would |can |could )?(?:wins? out|runs? the table|wins? the rest(?: of (?:their|its) (?:games|schedule|season|way))?|wins? (?:all|every one) of (?:their|its) (?:remaining |rest )?(?:games|schedule)|wins? (?:all )?(?:of )?(?:their |its )?remaining(?: games)?|wins? every (?:remaining )?game|wins? (?:out the rest|out the season)|(?:is|goes|finishes|stays) undefeated (?:the rest of the way|from here)|wins? (?:its|their) (?:last|final|remaining) (?:games|ones)|wins? the remaining(?: games)?)$/))) { res.items.push({ kind: "wins_out", team: T(m[1]) }); sawScenario = true; return; }
      if ((m = c.match(/^T(\d+) (?:will |would |can |could )?(?:loses? out|loses? the rest(?: of (?:their|its) (?:games|schedule|season|way))?|loses? (?:all|every one) of (?:their|its) (?:remaining |rest )?(?:games|schedule)|loses? (?:all )?(?:of )?(?:their |its )?remaining(?: games)?|loses? every (?:remaining )?game|(?:drops?|falls?) (?:all )?(?:of )?(?:their|its) remaining(?: games)?|loses? the remaining(?: games)?)$/))) { res.items.push({ kind: "loses_out", team: T(m[1]) }); sawScenario = true; return; }
      // --- wins N of M
      if ((m = c.match(new RegExp("^T(\\d+) (?:will |would |can |could )?(?:wins?|goes|finishes|gets|takes) " + NUM_RX + " (?:of|out of) (?:the |their |its )?(last |final |next |remaining )?" + NUM_RX + "(?: (?:remaining |final |last |regular season )?(?:games?|contests?|matchups?|ones))?$")))) {
        var nn = num(m[2]), mm = num(m[4]), sp = (m[3] || "").trim(); if (nn !== null && mm !== null) { res.items.push({ kind: "wins_n_of_m", team: T(m[1]), n: nn, m: mm, scope: (sp === "last" || sp === "final") ? "last" : (sp === "remaining" ? "remaining" : "next") }); sawScenario = true; return; }
      }
      // --- c1: conference-title scenarios are not supported yet (R1b): X wins the conference / reaches or meets in the conference championship game / beats Y in it
      if (/^T\d+(?: (?:and|also) T\d+)* (?:will |would |can |could )?(?:wins?|won|takes?|claims?|captures?|clinch(?:es)?|earns?|gets?) (?:the |a |their |its |that )?(?:\w+ ){0,3}?(?:conference|league|title|championship|crown|big 12|big ten|big 10|sec|acc|pac 12|mountain west|mwc|mac|sun belt|american|aac|c usa|cusa)\b/.test(c) ||
          /\b(?:title|championship|ccg) game\b/.test(c) && /^T\d+/.test(c) && !/^(?:what|how)/.test(c) || /^T\d+ .*\b(?:in|for) the (?:\w+ ){0,2}?(?:conference )?(?:title|championship|ccg)\b/.test(c) && !/^(?:what|how)/.test(c) || /^T\d+ (?:will |would |can |could )?(?:is|are|becomes?|be) (?:the |a )?(?:\w+ ){0,2}?(?:conference )?champions?\b/.test(c) || /^T\d+ (?:will |would |can |could )?(?:makes?|reach(?:es)?|gets? to|plays? in|advances? to|hosts?) the (?:\w+ ){0,2}?(?:conference )?(?:title|championship)\b/.test(c)) { unsupportedTitle = true; return; }
      // --- c1: bare "X wins" / "X loses": X's next remaining game (the UI echoes which game that is)
      if ((m = c.match(/^T(\d+) (?:will |would |can |could |finally |somehow )?(wins?|won|beats? them|loses?|lost|falls?|drops? (?:one|a game)|stumbles?)(?: (?:its|their|the) next game| next game| theirs| his| hers|(?: (?:this|next) (?:week|weekend|game)))?$/))) {
        res.items.push({ kind: /^(?:win|won|beat)/.test(m[2]) ? "next_win" : "next_loss", team: T(m[1]) }); sawScenario = true; return;
      }
      // --- beats / loses
      var pre = "^T(\\d+) (?:will |would |can |could |to |finally |somehow )?";
      if ((m = c.match(new RegExp(pre + WIN_V + " (?:the )?T(\\d+)(?: (at home|on the road|away|in their place|at their place|at his place))?$")))) {
        site = m[3] ? (/home|their place|his place|in their place/.test(m[3]) ? "winner_home" : "winner_away") : null;
        res.items.push({ kind: "beats", winner: T(m[1]), loser: T(m[2]), site: site }); sawScenario = true; return;
      }
      if ((m = c.match(new RegExp(pre + "(?:wins?|won|prevails?|escapes?|survives?)(?: (at home|on the road))? (at|against|over|vs|versus|in|on the road at|on the road against|on the road in|on the road versus) (?:the )?T(\\d+)$")))) {
        var prep = m[3], opt = m[2] || "";
        site = /^(?:at|in)$/.test(prep) ? "winner_away" : null;
        if (opt === "at home") site = "winner_home";
        if (opt === "on the road" || /^on the road/.test(prep)) site = "winner_away";
        res.items.push({ kind: "beats", winner: T(m[1]), loser: T(m[4]), site: site }); sawScenario = true; return;
      }
      if ((m = c.match(new RegExp(pre + LOSE_V + "(?: (at home|on the road))? (to|at|against|in|on the road to|on the road at|on the road against|by) (?:the )?T(\\d+)$")))) {
        var lp = m[3], ls = m[2] || "";
        site = /home/.test(ls) ? "winner_away" : (/road/.test(ls) || /^(?:on the road)/.test(lp)) ? "winner_home" : (lp === "at" || lp === "in") ? "winner_home" : null;
        res.items.push({ kind: "beats", winner: T(m[4]), loser: T(m[1]), site: site }); sawScenario = true; return;
      }
      if ((m = c.match(/^T(\d+) (?:lose|loses|lost) (?:their|its) (?:next|last|final|remaining) game$/)) ) { /* unsupported precision */ }
      // --- baseline chance question
      if ((m = c.match(/^(?:what (?:is|are) )?(?:the )?T(\d+) (?:odds|chances?|probability|shot|odds of making)\b/)) || (m = c.match(/^(?:what (?:is|are) )?(?:the )?(?:odds|chances?|probability) (?:of |that |for )?T(\d+)\b/)) || (m = c.match(/^how likely is T(\d+)\b/)) || (m = c.match(/^(?:what|how) (?:are|is|do) T(\d+) (?:looking|chances?|doing|looks?)\b/))) { if (res.baseline_team === null) res.baseline_team = T(m[1]); return; }
      if (/T\d+/.test(c)) unparsedWithTeam = true;
    });
    if (unsupportedTitle) { res.intent = null; res.items = []; res.need = null; res.baseline_team = null; res.clarify = true; res.clarify_reason = "title_scenario"; return res; }
    if (sawScenario) {
      res.intent = "scenario"; res.baseline_team = null;
      if (wantsNeed) res.need = null;
    } else if (wantsNeed) res.intent = "need";
    else if (res.baseline_team !== null && !unparsedWithTeam) res.intent = "baseline";
    if (!res.intent || (unparsedWithTeam && !sawScenario)) { res.intent = null; res.items = []; res.need = null; res.baseline_team = null; res.clarify = true; res.clarify_reason = "unparsed"; return res; }
    if (unparsedWithTeam && sawScenario) { res.clarify = true; res.clarify_reason = "unparsed"; }
    return res;
  }

  var API = { parse: parse, norm: norm };
  if (typeof module !== "undefined" && module.exports) module.exports = API; else root.KTParse = API;
})(typeof self !== "undefined" ? self : this);
