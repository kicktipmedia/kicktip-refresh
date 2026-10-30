"""Official-rules conference conference championship game simulator: rules for STEP 2 conferences (ACC, American, Mountain West, MAC, Sun Belt).
Drop-in for /workspace/kicktip-sim/src/ccg_rules_step2.py (schema: SCHEMA.md v1). Every entry is read from the conference's own published
tiebreaker document (doc.url; saved copies in sources/). No KickTip rating is ever used: ranking / computer / committee / coin / draw steps are
`external` / `random` and the engine reports them as 'tie not resolvable by this tool'.

EXTENSIONS to schema v1 (the step 1 engine/validator must learn these; see MERGE-NOTES in RULES-SOURCES.md; reference behaviour = strict_engine.py):
  external.take     = "all"  the ranking orders the WHOLE tied group; the open spots are filled from the top of that order (one branch per way to
                             choose the spots). Absent / 1 = places ONE team, then the rest restart (the schema's default). Used by MW, American, Sun Belt.
  external.optional = True   (only in `pre`) the step may not apply: besides one branch per tied team, add a branch where nobody is picked and
                             the normal procedure runs (Mountain West CFP-ranked-team immunity).
  h2h_group mode "beat_or_lost" = a team that beat EVERY other tied team is placed first; a team that lost to EVERY other tied team is dropped;
                             nothing else (no win-percentage step). Mountain West.
"""
CHECKED = "2026-10-25"

SHORT = {"CFP-ranked team tiebreaker immunity": "CFP-ranking immunity", "highest College Football Playoff ranking (Nov 24, 2026)": "Nov 24 CFP ranking (or the computer rankings)",
         "highest ranked tied team in the latest College Football Playoff ranking that does not": "latest CFP ranking (or the computer metrics)", "highest ranked tied team in the latest College Football Playoff ranking before": "latest CFP ranking (or the computer rankings)"}
def ext(name, t=None, **kw):
    d = dict(k="external", name=name, t=t or (name[0].upper() + name[1:] + ". The tool cannot compute this."))
    d.update(kw)
    for key, short in SHORT.items():   # (merge note) display names for the sentences the page builds around a ranking step
        if name.startswith(key): d["short"] = short
    return d
def hg(mode, t): return dict(k="h2h_group", mode=mode, t=t)
H2H = dict(k="h2h", t="Head-to-head: the winner of the game between the two teams.")
CPCT = dict(k="common_pct", t="Win percentage against all common conference opponents (opponents every tied team played).")
OPPW = dict(k="opp_conf_pct", t="Combined conference win percentage of all conference opponents.")
def rnd(name, t=None): return dict(k="random", name=name, t=t or (name[0].upper() + name[1:] + ". The tool cannot compute this."))
def cord(t): return dict(k="common_ordered", opp_ties="collective", t=t)

_MW_RANK = "highest College Football Playoff ranking (Nov 24, 2026) among tied teams that win their final game, otherwise the average of the conference's named rating systems"
_MW_TAIL = [
    dict(k="overall_pct", t="Overall winning percentage (at most one win over an FCS team counts)."),
    dict(k="ordered_any", opp_ties="collective", t="Record against the next-highest-placed conference team (or tied group), going down the standings; teams a tied team did not play are skipped."),
    CPCT]
_AM_RANK = "highest ranked tied team in the latest College Football Playoff ranking that does not lose in the final weekend, otherwise the average of four computer metrics"
_SB_RANK = "highest ranked tied team in the latest College Football Playoff ranking before the final weekend that wins its final weekend game, otherwise the average of the conference's named rating systems"

RULES = {
 "mwest": dict(
  name="Mountain West", fmt="top2",
  doc=dict(title="Mountain West Football Championship Tiebreaking Procedures", url="https://themw.com/documents/2026/10/12/MW_Football_Championship_Tiebreaking_Procedures.pdf", version="document dated Oct. 12, 2026", checked=CHECKED),
  extra_urls=["https://themw.com/news/2026/6/4/broadcast-details-announced-for-2026-mountain-west-football-championship-game.aspx"],
  ccg=dict(date="2026-12-04", when="Fri Dec 4, 7:00 PM MT (9:00 PM ET), FOX", site="home field of the participant with the better conference record (ties by the host rules)", host="higher_pct"),
  games_per_team=8, tie_group="equal", elim="restart",
  pre=[ext("CFP-ranked team tiebreaker immunity: the highest-ranked tied team in the Nov 24, 2026 College Football Playoff ranking that also wins its final regular-season game gets in automatically",
           "Before any other tiebreaker, the tied team ranked highest in the Nov 24, 2026 College Football Playoff ranking goes into the game (and hosts if it is tied for the best record) if it also wins its final regular-season game. This depends on the Nov 24 CFP ranking, which does not exist yet.",
           take=1, optional=True)],
  two=[H2H, ext(_MW_RANK, "The tied team that is ranked higher in the Nov 24 College Football Playoff ranking (if it won its final game); otherwise the team with the better average of four computer rankings.", take="all")] + _MW_TAIL + [rnd("coin toss by the Commissioner")],
  multi=[hg("beat_or_lost", "Mini round-robin: a team that beat every other tied team goes in; a team that lost to every other tied team is out. Then the tie starts again with the rest."),
         ext(_MW_RANK, "Tied teams ranked in the Nov 24 College Football Playoff ranking that won their final game come first (in ranking order); the others follow by the average of four computer rankings.", take="all")] + _MW_TAIL + [rnd("drawing by the Commissioner")],
  host=[H2H, ext(_MW_RANK, "The tied team ranked higher in the Nov 24 College Football Playoff ranking (if it won its final game) hosts; otherwise the better average of four computer rankings.", take="all")] + _MW_TAIL + [rnd("coin toss by the Commissioner")],
  notes=["Mountain West ties are shown as 'depends on the Nov 24 CFP ranking' until that ranking exists: the immunity step comes before every other step, for any tie for a spot or for hosting, and it also needs the team to win its final game afterwards.",
         "Host: the outright best conference record hosts. Two teams tied for the best: immunity first, then the two-team steps. Three or more tied for the best: the immune team if there is one, otherwise the two-team steps from step 1 for the two teams that qualified.",
         "Everything after the ranking step (overall record, record against the next-highest-placed team, common opponents, coin toss) is only reached on an exact tie in the ranking and is not worked out by the tool.",
         "Teams that are ineligible for the postseason are not removed (no data)."]),
 "belt": dict(
  name="Sun Belt", fmt="div",
  doc=dict(title="Sun Belt Football Tie-Breaking Procedures", url="https://sunbeltsports.org/sports/2018/8/30/FB_Tie-Breakers.aspx", version="live page (URL dated 2018; page footer 2026), read Oct. 25, 2026", checked=CHECKED),
  extra_urls=["https://sunbeltsports.org/news/2026/5/27/sun-belt-espn-announce-updates-to-2026-football-schedule.aspx", "https://sunbeltsports.org/standings.aspx?path=football"],
  ccg=dict(date="2026-12-04", when="Fri Dec 4, 7:00 PM ET (5:00 PM MT), ESPN", site="home field of the division champion with the better conference record", host="higher_pct"),
  games_per_team=8, tie_group="equal", elim="continue",
  divisions={"East": ["App State", "Coastal Carolina", "Georgia Southern", "Georgia State", "James Madison", "Marshall", "Old Dominion"],
             "West": ["Arkansas State", "Louisiana", "UL Monroe", "South Alabama", "Southern Miss", "Troy", "Louisiana Tech"]},
  two=[H2H,
       dict(k="div_pct", t="Winning percentage in games against division opponents."),
       dict(k="ordered_div", opp_ties="collective", t="Record against the team in the next-highest place of the division standings, then the next, until one team leads (a tied group counts as one)."),
       dict(k="common_nondiv", t="Winning percentage against common opponents from the other division."),
       ext(_SB_RANK, "A ranked tied team that wins in the final weekend goes in; otherwise the better average of four computer rankings.", take="all"),
       dict(k="fbs_pct", t="Overall winning percentage against FBS opponents."), rnd("coin toss by the Commissioner")],
  multi=[hg("pct_only", "Highest winning percentage in the games the tied teams played against each other."),
         dict(k="div_pct", t="Winning percentage in games against division opponents."),
         dict(k="ordered_div", opp_ties="collective", t="Record against the team in the next-highest place of the division standings, then the next, until one team leads."),
         dict(k="common_nondiv", t="Winning percentage against common opponents from the other division."),
         ext(_SB_RANK, "The highest-ranked tied team that wins in the final weekend goes in; otherwise the better average of four computer rankings.", take="all"),
         dict(k="fbs_pct", t="Overall winning percentage against FBS opponents."), rnd("determined by lot by the Commissioner")],
  host=[dict(k="h2h", t="The division champion that beat the other hosts."),
        ext(_SB_RANK, "A ranked champion that wins in the final weekend hosts (the higher-ranked if both); otherwise the better average of four computer rankings.", take="all"),
        CPCT, dict(k="fbs_pct", t="Overall winning percentage against FBS opponents."), rnd("coin toss by the Commissioner")],
  notes=["The conference's tiebreaker page still lists the OLD divisions (Texas State in the West, no Louisiana Tech); we use the rules as written and the 2026 divisions from the official 2026 standings page.",
         "The host of the conference championship game is the division champion with the better conference record; when the two have the same record the host list applies (head-to-head first). The page does not say what a three-way host tie does, which cannot happen with two champions.",
         "Steps after the ranking step are only reached on an exact tie in the ranking and are not worked out by the tool.",
         "The rule for an ineligible division champion is not modeled."]),
 "midam": dict(
  name="MAC", fmt="top2",
  doc=dict(title="MAC Football Championship Game Tiebreaker", url="https://getsomemaction.com/sports/2025/11/12/FB_1112255434.aspx", version="posted Nov. 12, 2025 (live page, footer 2026; no 2026 revision found)", checked=CHECKED),
  ccg=dict(date="2026-12-05", when="Sat Dec 5, 12:00 PM ET (10:00 AM MT), ESPN", site="Ford Field, Detroit", host="neutral"),
  games_per_team=8, tie_group="equal", elim="restart",
  two=[H2H, dict(k="common_pct", t="Win percentage against all common opponents."),
       ext("a conference-specified analytics rating after the final regular-season games", "The tied team with the higher conference-specified analytics rating.", take=1),
       dict(k="common_ordered", opp_ties="collective", t="Win percentage against common opponents in order of finish, best finisher first."),
       OPPW, rnd("draw by the Commissioner or designee")],
  multi=[hg("pct_else_beat_all", "Head-to-head among the tied teams: the best combined win percentage if they all played each other; otherwise only a team that beat every other tied team goes first."),
         dict(k="common_pct", t="Win percentage against all common opponents (opponents every tied team played)."),
         ext("a conference-specified analytics rating after the final regular-season games", "The tied team with the highest conference-specified analytics rating goes in and the tie starts again.", take=1),
         dict(k="common_ordered", opp_ties="collective", t="Win percentage against common opponents in order of finish, best finisher first."),
         OPPW, rnd("draw by the Commissioner or designee")],
  notes=["The MAC text does not say what happens to the remaining teams after one is placed in a tie of three or more, or when a tie is cut down to two teams; we start again from step 1 and use the two-team steps at two teams.",
         "The step that ranks teams by results against common opponents in order of finish comes after the rating step, so it is only reached on an exact tie in that rating and is not worked out by the tool.",
         "The rating step for three or more teams is read as placing one team (singular wording) and restarting."]),
 "acc": dict(
  name="ACC", fmt="top2",
  doc=dict(title="ACC Football Tiebreaker Policy (as amended July 1, 2026)", url="https://theacc.com/documents/2026/7/15/ACC_Football_Tiebreaker_Policy_Jully_2026.pdf", version="as amended July 1, 2026 (posted July 15, 2026)", checked=CHECKED),
  ccg=dict(date="2026-12-05", when="Sat Dec 5, 12:00 PM ET (10:00 AM MT), ABC", site="Charlotte, N.C.", host="neutral"),
  games_per_team=9, tie_group="acc_unequal", elim="restart",
  two=[H2H, ext("a conference-specified analytics rating after all regular-season games", "The tied team with the better conference-specified analytics rating.", take=1),
       rnd("draw by the Commissioner or designee")],
  multi=[hg("pct_else_beat_lost", "If the tied teams all played each other, the best record among them; if not, a team that beat every other tied team is placed first and a team that lost to every other tied team is removed. The tie then starts again."),
         ext("a conference-specified analytics rating after all regular-season games", "The tied team with the best conference-specified analytics rating goes in and the tie starts again.", take=1),
         rnd("draw by the Commissioner or designee")],
  notes=["The ACC counts as tied with the leader any team that played a different number of conference games and has the same wins or the same losses (schedules are 8 or 9 games). The policy then says ties are broken 'starting with the highest win percentage, working downward'. Read one way, the whole group is handled together by the three-or-more-team steps; read the other way, teams are simply taken in win-percentage order. When the two readings give different pairings for the conference championship game, the tool shows both and says it depends on the ACC's reading.",
         "After the ranking step only a draw remains, which is not worked out by the tool.",
         "Postseason-ineligible teams are not removed (no data)."]),
 "American": dict(
  name="American", fmt="top2",
  doc=dict(title="American Conference 2026 Football Tiebreakers (Section 10)", url="https://theamerican.org/documents/2026/9/30/26_FB_Tiebreakers.pdf", version="document dated Sept. 30, 2026", checked=CHECKED),
  extra_urls=["https://s3.amazonaws.com/sidearm.sites/theamerican.sidearmsports.com/documents/2026/9/30/26_FB_Tiebreakers.pdf"],
  ccg=dict(date="2026-12-05", when="Sat Dec 5, 8:00 PM ET (6:00 PM MT), ABC", site="home field of the participant with the better conference record", host="higher_pct"),
  games_per_team=8, tie_group="equal", elim="restart",
  two=[H2H, ext(_AM_RANK, "A tied team ranked in the latest College Football Playoff ranking that does not lose in the final weekend goes in (the higher-ranked one if both); otherwise the better average of four computer metrics.", take="all"),
       CPCT, dict(k="overall_pct", t="Overall winning percentage, not counting exempt games."), rnd("coin toss by the Commissioner")],
  multi=[hg("pct_else_beat_all", "Conference records among the tied teams; if any two did not play each other, they stay tied unless one team beat all the others."),
         ext(_AM_RANK, "The highest-ranked tied team(s) in the latest College Football Playoff ranking that do not lose in the final weekend go in; otherwise the better average of four computer metrics.", take="all"),
         CPCT, dict(k="overall_pct", t="Overall winning percentage, not counting exempt games."), rnd("drawing by the Commissioner")],
  host=[H2H, ext(_AM_RANK, "The tied team ranked higher in the latest College Football Playoff ranking (and not losing in the final weekend) hosts; otherwise the better average of four computer metrics.", take="all"),
        CPCT, dict(k="overall_pct", t="Overall winning percentage, not counting exempt games."), rnd("coin toss by the Commissioner")],
  notes=["Section 10.4 of the document (teams with unequal schedules: a team with fewer games that beat all other tied teams ranks ahead on head-to-head; teams need at least 7 conference games) is not worked out: every team has 8 conference games.",
         "'Exempt games' in the overall-record step cannot be identified from our data; that step is only reached after the ranking step.",
         "The Army-Navy game (Dec 12) is outside the standings."]),
}
