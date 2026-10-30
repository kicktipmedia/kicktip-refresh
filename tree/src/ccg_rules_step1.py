"""Official-rules conference conference championship game simulator: rules for STEP 1 conferences (Big 12, Pac-12, Big Ten, SEC, Conference USA).
Schema: SCHEMA.md. Every entry is read from the conference's own published tiebreaker text (see doc.url). No KickTip rating is ever used:
steps that need a ranking/rating/committee/coin toss are `external` / `random` and the engine reports them as 'tie not resolvable by this tool'."""
CHECKED = "2026-10-25"

H2H = dict(k="h2h", t="Head-to-head: the winner of the game between the two teams.")
def hg(mode, t="Head-to-head among the tied teams."): return dict(k="h2h_group", mode=mode, t=t)
CPCT = dict(k="common_pct", t="Win percentage against all common conference opponents (opponents every tied team played).")
RAND = dict(k="random", name="coin toss", t="Coin toss (or random draw) run by the conference office.")
OPPW = dict(k="opp_conf_pct", t="Combined conference win percentage of all conference opponents (strength of conference schedule).")
def ext(name, t=None): return dict(k="external", name=name, t=t or (name[0].upper() + name[1:] + ". The tool cannot compute this."))
def cord(opp_ties, t=None): return dict(k="common_ordered", opp_ties=opp_ties,
    t=t or "Win percentage against the best-placed common opponent in the conference standings, then the next one down, until the teams differ. If that opponent is itself a group of tied teams, the record against the group as a whole is used.")

RULES = {
 "big12": dict(
  name="Big 12", fmt="top2",
  doc=dict(title="Big 12 Football Tiebreaking Procedures (2024-present)", url="https://big12sports.com/documents/2025/11/4/Big_12_Football_2024_Tiebreaker_Policy.pdf", version="republished Nov. 4, 2025", checked=CHECKED),
  extra_urls=["https://big12sports.com/news/2026/5/27/big-12-announces-opening-slate-of-football-tv-selections.aspx"],
  ccg=dict(date="2026-12-04", when="Fri Dec 4, 6:00 PM MT (7:00 PM CT)", site="AT&T Stadium, Arlington", host="neutral"),
  games_per_team=9, tie_group="equal", elim="continue",
  two=[H2H, CPCT, cord("collective"), OPPW,
       dict(k="wins12", t="Total wins in the 12-game season (at most one win over an FCS team counts)."),
       ext("a conference-specified analytics rating after the last weekend of the regular season"), RAND],
  multi=[hg("pct_else_beat_all", "Win percentage in games among the tied teams. If they did not all play each other, a team that beat every other tied team is placed first."),
         CPCT, cord("collective"), OPPW,
         dict(k="wins12", t="Total wins in the 12-game season (at most one win over an FCS team counts)."),
         ext("a conference-specified analytics rating after the last weekend of the regular season"), RAND],
  notes=["The Big 12 text says that once one team is placed, the rest start the procedure again, and that a tie cut down to two teams goes to the two-team steps. It does not say what happens to teams dropped from a longer tie for second place, so we keep going down the same list with the teams that remain.",
         "In 'wins in a 12-game season', games exempted by NCAA rules are not counted and only one FCS win counts. The step can only be worked out once every team's non-conference games are played."]),
 "pac12": dict(
  name="Pac-12", fmt="top2",
  doc=dict(title="Pac-12 Football Championship Game Tiebreakers (2026)", url="https://pac-12.com/news/2026/9/3/pac-12-announces-commercial-and-operational-updates-ahead-of-its-2026-football-season-kickoff.aspx", version="published Sept. 3, 2026", checked=CHECKED),
  ccg=dict(date="2026-12-04", when="Fri Dec 4, 6:00 PM MT (5:00 PM PT)", site="home field of the higher seed", host="higher_seed"),
  games_per_team=7, tie_group="equal", elim="continue",
  two=[H2H, cord("collective"), CPCT,
       ext("highest College Football Playoff ranking on the Tuesday before week 13 games"),
       ext("a conference-specified analytics rating after the last weekend of regular-season conference games"), RAND],
  multi=[hg("pct_only", "Win percentage in games among the tied teams. If every tied team has not played every other, this step is skipped."),
         CPCT, cord("collective"), OPPW,
         ext("a conference-specified analytics rating after the final weekend of regular-season games"), RAND],
  notes=["Only conference games through week 12 count; the week 13 home-and-home flex games do not count in the standings.",
         "The Pac-12 lists head-to-head only for a tie for first place, then says a tie for second place uses 'the two-team tiebreaker policy'. We carry both readings (head-to-head first for a tie for second place, or skipped there); when they give different pairings for the conference championship game both pairings are shown and the tool does not choose.",
         "The Pac-12 does not say what happens to teams dropped from a longer tie; we keep going down the same list with the teams that remain."]),
 "big10": dict(
  name="Big Ten", fmt="top2",
  doc=dict(title="2024 Big Ten Football Championship Game Tiebreaker", url="https://bigten.org/fb/article/blt6104802d94ebe1ab/", version="Aug. 26, 2024 (the latest edition we found)", checked=CHECKED),
  extra_urls=["https://bigten.org/news/2026/8/19/championship-2026-discover-big-ten-football-championship-game-information.aspx"],
  ccg=dict(date="2026-12-05", when="Sat Dec 5, 6:00 PM MT (8:00 PM ET)", site="Lucas Oil Stadium, Indianapolis", host="neutral"),
  games_per_team=9, tie_group="equal", elim="continue",
  two=[H2H, CPCT, cord("collective", "Record against the best-placed common opponent in the conference standings, then the next one down, until the teams differ."),
       dict(k="opp_conf_pct", t="Best cumulative conference win percentage of all conference opponents (counted even if the teams played different numbers of opponents)."),
       ext("a conference-specified analytics rating after the regular season"), RAND],
  multi=[hg("pct_else_beat_all", "Win percentage in games among the tied teams. If they did not all play each other, a team that beat every other tied team is placed first."),
         CPCT, cord("collective", "Win percentage against the best-placed common opponent in the conference standings, then the next one down, until the teams differ."),
         dict(k="opp_conf_pct", t="Best cumulative conference win percentage of all conference opponents (counted even if the teams played different numbers of opponents)."),
         ext("a conference-specified analytics rating after the regular season"), RAND],
  notes=["This is the Big Ten's 2024 published text, the most recent we found. If the Big Ten republishes it for 2026 this page will be updated.",
         "The Big Ten's text does not say how to treat a group of tied opponents when working down the standings. We use each team's record against the group as a whole.",
         "A team ruled out by a step stays out for the rest of that tie (the Big Ten says it is not pulled back in)."]),
 "sec": dict(
  name="SEC", fmt="top2",
  doc=dict(title="Southeastern Conference Official Football Tiebreakers", url="https://www.secsports.com/fbtiebreaker", version="current SEC page (the PDF behind it)", checked=CHECKED),
  extra_urls=["https://www.secsports.com/championships/football-championship"],
  ccg=dict(date="2026-12-05", when="Sat Dec 5, 2:00 PM MT (4:00 PM ET)", site="Mercedes-Benz Stadium, Atlanta", host="neutral"),
  games_per_team=9, tie_group="equal", elim="restart",
  two=[H2H, CPCT, cord("h2h_then_combine", "Record against the best-placed common opponent, then the next one down. If several common opponents are tied in the standings, they are split by their own head-to-head results first; if that does not separate them, their records are combined."),
       OPPW, ext("a conference-specified analytics rating (capped scoring margin against all conference opponents)"), RAND],
  multi=[hg("pct_else_beat_lost", "Head-to-head among the tied teams. With a full round robin, the best record wins. Otherwise a team that beat all the others is placed first, and a team that lost to all the others is dropped (if only two teams are left they are both placed)."),
         CPCT, cord("h2h_then_combine", "Record against the best-placed common opponent, then the next one down. If several common opponents are tied in the standings, they are split by their own head-to-head results first; if that does not separate them, their records are combined."),
         OPPW, ext("a conference-specified analytics rating (capped scoring margin against all conference opponents)"), RAND],
  notes=["If a step leaves a tie at the top that is too big for the open spots, the teams at the top go back to the beginning of the list and the others are dropped (SEC wording)."]),
 "usa": dict(
  name="Conference USA", fmt="top2",
  doc=dict(title="Conference USA Football Regulations, Championship Game Tiebreaker Procedure", url="https://s3.amazonaws.com/sidearm.sites/conferenceusa.com/documents/2024/9/19/CUSA_FB_Championship_Game_Tiebreaker_Policy.pdf", version="2024 policy (the one posted on conferenceusa.com)", checked=CHECKED),
  extra_urls=["https://conferenceusa.com/sports/2026/10/19/fbchamp2026.aspx"],
  ccg=dict(date="2026-12-04", when="Fri Dec 4, 5:00 PM MT (6:00 PM CT)", site="home field of the team with the higher win percentage", host="higher_pct"),
  games_per_team=8, tie_group="unequal_one_win", elim="restart",
  two=[H2H, CPCT, cord("collective_strict", "Win percentage against the common opponent(s) with the best conference record, then down the standings until the tie is broken. A group of tied opponents counts as one group; it is skipped if the teams played it an unequal number of times or have the same record against it."),
       ext("average of the conference's named rating systems"), OPPW, RAND],
  multi=[hg("pct_else_beat_all", "Head-to-head among the tied teams (win percentage if all played each other; otherwise a team that beat all the others)."),
         CPCT, cord("collective_strict", "Win percentage against the common opponent(s) with the best conference record, then down the standings until the tie is broken. A group of tied opponents counts as one group; it is skipped if the teams played it an unequal number of times or have the same record against it."),
         ext("average of the conference's named rating systems"), OPPW, RAND],
  notes=["The same steps decide the host if the two finalists have the same record.",
         "Conference USA says that when a tie among three or more teams is broken, the teams that remain start again at step 1; we do that.",
         "For a tie among three or more teams, the policy says only 'head-to-head: the winner is selected'. We carry both readings (win percentage among the tied teams if they all played each other, otherwise a team that beat all the others; or only a team that beat every other tied team); when they give different pairings for the conference championship game both pairings are shown and the tool does not choose.",
         "The policy applies 'provided all teams played an equal number of conference games' and has a separate rule for unequal schedules (teams one win behind with the same losses count as tied). The tool applies that rule if a game is ever cancelled."]),
}

# Two-reading sentences (shown as their own flagged pairings whenever the readings give different pairings for the conference championship game; never silently picked).
# alt.patch holds the rules fields that replace the default ones under reading b; reading a is the default fields above.
RULES["pac12"]["alt"] = dict(
  a="the Pac-12's two-team policy is read as starting a tie for second place with head-to-head",
  b="the Pac-12's two-team policy is read as using head-to-head only for a tie for first place, so a tie for second place starts with the win percentage against common opponents",
  box="The Pac-12's policy lists head-to-head only for a tie for first place, and says a tie for second place uses the two-team policy. That can be read two ways, and the two readings give different pairings for the conference championship game",
  patch=dict(two_second=RULES["pac12"]["two"][1:]))
RULES["usa"]["alt"] = dict(
  a="Conference USA's 'head-to-head: the winner is selected' is read, for a tie of three or more teams, as win percentage among the tied teams (or a team that beat all the others)",
  b="Conference USA's 'head-to-head: the winner is selected' is read, for a tie of three or more teams, as needing one team that beat every other tied team",
  box="Conference USA's policy says only 'head-to-head: the winner is selected' for a tie of three or more teams. That can be read two ways, and the two readings give different pairings for the conference championship game",
  patch=dict(multi=[dict(RULES["usa"]["multi"][0], mode="beat_all", t="Head-to-head among the tied teams: a team that beat every other tied team.")] + RULES["usa"]["multi"][1:]))
