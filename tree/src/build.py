"""KickTip site build (b4): static page templates generated from the data engine output (data/out/*.json). Nothing here deploys.
python3 src/build.py  -> build/site/  (then python3 src/make_zip.py). Pages: home, 11 conference pages, 138 team pages, playoff, method, disclaimer, 404, sitemap, robots.
No prediction number is in any HTML file. Predictions live in data/pred-teams.json, pred-games.json, pred-paths.json (fetched by assets/kt.js on arrival; gate-move build: there is no disclaimer gate,
terms are accepted by use: top banner + static line under every Run control, wording in src/terms_copy.py). private/ (API key) is never read here and never copied: the build only reads data/out, data/*.json, data/ref and src/assets."""
import hashlib, os, sys, re, json, shutil, html, unicodedata, datetime as dt
from zoneinfo import ZoneInfo
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, f"{ROOT}/src")
import rules, cfp
import terms_copy
import ccg_rules, ccgsim_data
import privacy_copy
SITE = os.environ.get("KT_SITE_DIR") or f"{ROOT}/build/site"; OUTD = f"{ROOT}/data/out"; MT = ZoneInfo("America/Denver")
TERMS_EFFECTIVE = "Oct 24, 2026"   # shown on the Disclaimer / terms page. The old acceptance gate and its DISC_VERSION are retired (gate-move build).
import site_config
from site_config import SITE_URL
BASE = SITE_URL   # single source of truth for the absolute host (src/site_config.py)
E = html.escape
def J(p): return json.load(open(p))

# ---------------------------------------------------------------- data
ST = J(f"{OUTD}/sim_teams.json"); SG = J(f"{OUTD}/sim_games.json"); SD = J(f"{OUTD}/standings.json"); PA = J(f"{OUTD}/paths.json")
import models_registry as MR, method_copy, moves
MOVERS = J(f"{ROOT}/data/ref/movers.json")             # internal raw-MSM vs default make-12 (src/movers.py); only two team numbers reach the method page
ACC = J(f"{ROOT}/data/ref/accuracy_claims.json")      # every accuracy number on the method page (src/accuracy_claims.py)
assert ST.get("model") == MR.DEFAULT_ID, f"data/out was simulated with model {ST.get('model')!r}, not the default {MR.DEFAULT_ID!r}: run python3 src/run_all.py"
META = J(f"{OUTD}/run_meta.json"); REFRESH = J(f"{OUTD}/refresh_log.json"); CMAP = J(f"{ROOT}/data/ref/conf_2026.json")
CCG = J(f"{ROOT}/data/ccg.json")["ccg"]
MLINES = J(f"{OUTD}/market_lines.json") if os.path.exists(f"{OUTD}/market_lines.json") else dict(lines=[])   # src/lines.py: market line NUMBERS only (game id -> point spread, home side, and the time it was read). No provider, link or book count exists in it.
MLINE = {x["id"]: x for x in MLINES["lines"]}
MKT_LATEST = max([x["t"] for x in MLINES["lines"]] or [0])
MKT_LATEST_S = dt.datetime.fromtimestamp(MKT_LATEST, MT).strftime("%b %-d, %Y, %-I:%M %p MT") if MKT_LATEST else "not available"

def slugify(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower().replace("'", "")
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")
CONFS = [("acc", "ACC", "acc"), ("American", "American", "american"), ("big10", "Big Ten", "big-ten"), ("big12", "Big 12", "big-12"), ("usa", "Conference USA", "conference-usa"),
         ("ind", "Independents", "independents"), ("midam", "MAC", "mac"), ("mwest", "Mountain West", "mountain-west"), ("pac12", "Pac-12", "pac-12"), ("sec", "SEC", "sec"), ("belt", "Sun Belt", "sun-belt")]
CSLUG = {k: s for k, _, s in CONFS}; CNAME = {k: n for k, n, _ in CONFS}
TEAMS = {}  # full name -> dict
for t in ST["teams"]:
    loc = CMAP[t["team"]]["loc"]; TEAMS[t["team"]] = dict(full=t["team"], short=loc, slug=slugify(loc), conf=t["conf"], sim=t)
assert len({v["slug"] for v in TEAMS.values()}) == 138
import logos
for _k, _v in TEAMS.items(): _v["espn"] = CMAP[_k]["id"]
M = logos.Marks(TEAMS, CONFS)   # logo tiles (ESPN, unaltered; see src/logos.py)
CRED = f'<p class="cred">{logos.CREDIT}</p>'
SHORT = {k: v["short"] for k, v in TEAMS.items()}; SLUG = {k: v["slug"] for k, v in TEAMS.items()}

def tcell(full, lazy=False, extra=""):
    """Team name link with its logo tile beside it (logo is not part of the link; tile is aria-hidden, the name is the accessible text)."""
    return f'<span class="tnm">{M.team(full, 24, lazy)}<a class="tl" href="/team/{SLUG[full]}/">{E(SHORT[full])}</a></span>'
def gunit(full, text, lazy=True):
    return f'<span class="gu">{M.team(full, 24, lazy) if full else M.team(None, 24, lazy)}<span>{E(text)}</span></span>'
def parse_mt(s): return dt.datetime.strptime(s.replace(" MT", ""), "%Y-%m-%d %H:%M").replace(tzinfo=MT)
def fmt_long(d): return d.strftime("%a, %b %-d, %Y, %-I:%M %p MT")
MODEL_ASOF = parse_mt(ST["as_of"]); MODEL_ASOF_S = fmt_long(MODEL_ASOF)
RESULTS_ASOF_S = fmt_long(parse_mt(J(f"{ROOT}/data/out/refresh_log.json")["refreshed_mt"]))   # when the game results were last pulled (ESPN); the model is recalculated from them afterwards (MODEL_ASOF_S)
SEASONS = f"{META['seasons']:,}"
SCHED = J(f"{ROOT}/data/store/schedule.json")
IDMAP = {v["id"]: k for k, v in CMAP.items() if k in TEAMS}

REF_T = parse_mt(REFRESH["refreshed_mt"]).astimezone(dt.timezone.utc)
LIVE_ST = ("STATUS_IN_PROGRESS", "STATUS_HALFTIME", "STATUS_END_PERIOD", "STATUS_DELAYED", "STATUS_SUSPENDED")

def game_when(g):
    """(sort key, label). ESPN 'time TBA' placeholders sit at 04:00-05:00Z (midnight ET): use the ET calendar date and say TBA."""
    u = dt.datetime.strptime(g["date_utc"], "%Y-%m-%dT%H:%MZ").replace(tzinfo=dt.timezone.utc)
    if g["date_utc"][11:] in ("04:00Z", "05:00Z"):
        d = (u - dt.timedelta(hours=5)).date() if False else u.date()
        return u, d.strftime("%a %b %-d") + ", time TBA"
    m = u.astimezone(MT); return u, m.strftime("%a %b %-d, %-I:%M %p MT")

def game_state(g):
    """None for a game that has not started at the last ESPN refresh; else a label. Started games get no pre-game numbers."""
    st = g.get("status", "")
    if st in ("STATUS_POSTPONED", "STATUS_CANCELED"): return "Postponed" if st == "STATUS_POSTPONED" else "Canceled"
    u = dt.datetime.strptime(g["date_utc"], "%Y-%m-%dT%H:%MZ").replace(tzinfo=dt.timezone.utc)
    tba = g["date_utc"][11:] in ("04:00Z", "05:00Z")
    if st in LIVE_ST: return "In progress"
    if not tba and u <= REF_T: return "Started; final score not in yet"
    return None

def mt_day(iso):
    u = dt.datetime.strptime(iso, "%Y-%m-%dT%H:%MZ").replace(tzinfo=dt.timezone.utc); return u.astimezone(MT).strftime("%a %b %-d")

def nice_stamp(s):
    """'2026-10-23 23:05 MT' -> 'Oct 23, 2026, 11:05 PM MT' (site date style)."""
    return fmt_long(parse_mt(s)).split(", ", 1)[1]
def nice_ccg(t):
    """'Sat 2026-12-05, noon ET (...)' -> 'Sat, Dec 5, 2026, noon ET (...)'."""
    def f(m): d = dt.date(int(m.group(2)), int(m.group(3)), int(m.group(4))); return f"{m.group(1)}, {d.strftime('%b')} {d.day}, {d.year}"
    return re.sub(r"\b(Mon|Tue|Wed|Thu|Fri|Sat|Sun) (\d{4})-(\d\d)-(\d\d)", f, t)
def results_card(full=None, members=None, title="Results", limit=None):
    """Final scores from ESPN (static facts). Team page: that team's results. Conference page: games between members."""
    ids = {CMAP[full]["id"]} if full else {CMAP[t]["id"] for t in members}
    rows = []
    for g in sorted((g for g in SCHED if g["done"] and g["hs"] is not None), key=lambda g: g["date"], reverse=True):
        if full:
            if g["home"] not in ids and g["away"] not in ids: continue
        elif not (g["home"] in ids and g["away"] in ids): continue
        rows.append(g)
    if not rows: return ""
    total = len(rows)
    if limit: rows = rows[:limit]
    def nm(i, n):
        t = IDMAP.get(i); return (f'<a class="tl" href="/team/{SLUG[t]}/">{E(SHORT[t])}</a>' if t else E(n))
    out = []
    for g in rows:
        if full:
            home = g["home"] in ids; oid, on = (g["away"], g["an"]) if home else (g["home"], g["hn"]); mine, theirs = (g["hs"], g["as_"]) if home else (g["as_"], g["hs"])
            site = "Neutral site" if g["neutral"] else ("Home" if home else "Away")
            out.append(f'<tr><td>{mt_day(g["date"])}</td><td>{nm(oid, on)}<span class="note">{site}</span></td><td><b>Final</b> &middot; {"W" if mine > theirs else "L"} {mine}-{theirs}</td></tr>')
        else:
            hw = g["hs"] > g["as_"]; w, l = ((g["home"], g["hn"], g["hs"]), (g["away"], g["an"], g["as_"])) if hw else ((g["away"], g["an"], g["as_"]), (g["home"], g["hn"], g["hs"]))
            out.append(f'<tr><td>{mt_day(g["date"])}</td><td>{nm(g["away"], g["an"])} {"vs" if g["neutral"] else "at"} {nm(g["home"], g["hn"])}</td><td><b>Final</b> &middot; {nm(w[0], w[1])} {w[2]}, {nm(l[0], l[1])} {l[2]}</td></tr>')
    note = f'<p class="note">Final scores from ESPN public data, last checked {E(nice_stamp(REFRESH["refreshed_mt"]))}.' + (f' Showing the latest {limit} of {total}; every result is on the team pages.' if limit and total > limit else "") + '</p>'
    return f'<div class="card"><h2>{title}</h2>' + tbl('<th>Date (MT)</th><th>Game</th><th>Result</th>' if not full else '<th>Date (MT)</th><th>Opponent</th><th>Result</th>', "".join(out), "", kind="g") + note + '</div>'

# ---------------------------------------------------------------- standings (static, not predictions)
def rec_pct(rec):
    w, l = rec.split("-"); w, l = int(w), int(l); return w / (w + l) if w + l else 0
BELT_DIV = {n: d for d, ns in rules.RULES["belt"]["divisions"].items() for n in ns}
STAND = {}
for ck, rows in SD.items():
    r = sorted(rows["standings"], key=lambda x: (-(x["conf_pct"] or 0), -x["conf_w"], -rec_pct(x["overall"]), SHORT[x["team"]]))
    STAND[ck] = r
GAMES = SG["games"]
GAP_BASIS = ("computed from the unrounded numbers (the KickTip line is rounded to 0.5 only for display)" if any("model_spread_raw" in x for x in GAMES)
             else "computed from the numbers shown (the KickTip line is rounded to 0.5; the engine will store the unrounded line from its next run)")
def gkey(g): return f"{SLUG[g['home']]}~{SLUG.get(g['away'], 'fcs')}"
def team_games(full):
    return sorted([g for g in GAMES if g["home"] == full or g["away"] == full], key=lambda g: g["date_utc"])

# ---------------------------------------------------------------- chrome
def pct_free(t): return t  # marker: static text never carries prediction numbers
NAV = (("Home", "/"), ("Conferences", "/#conferences"), ("Playoff Picture", "/playoff/"), ("My teams", "/#my-teams"), ("Method", "/method/"))   # my-teams build: the My teams link (a count badge is added by assets/myteams.js)
SHORT_DISC = "Chances are for information and entertainment only, not advice or a guarantee."
CCGDEF = '<p class="ccgdef">CCG = conference championship game</p>'
def banner(dyn, here=""):
    load = ('<div class="ldm" data-loadbar hidden><p data-loadmsg role="status"></p></div>'
            '<noscript><div class="ldm"><p>Turn on JavaScript to see the chances. Without it this page shows no simulation numbers.</p></div></noscript>') if dyn else ""
    return (f'<div class="ban" role="note"><b>Chances are for information only, not advice.</b><span class="l"><a href="/disclaimer/">Full disclaimer</a>' + ("" if here == "method" else '<a href="/method/">How we make the numbers</a>') + '</span></div>' + load)
def sources_block(dyn, extra=""):
    mk = (" Spreads: ESPN, numbers only, shown when one has been posted." if dyn else "")
    if extra: mk = ""   # /top25/ (the only page that passes extra): no market line or model line is shown there, so the strip does not mention them
    first = (("Schedules and results: ESPN public data. Chances: KickTip model (estimates), " + SEASONS + " simulated seasons.") if extra else ("Schedules and results: ESPN public data. Chances, win probabilities and KickTip's expected margin: KickTip model (estimates), " + SEASONS + " simulated seasons." + mk)) if dyn else "Schedules and results: ESPN public data. Method and wording: KickTip."
    return (f'<section class="src" aria-label="Sources"><div class="w"><p><b>Sources and last updated (MT)</b></p><p>{first}</p>'
            f'<p>Game results last pulled: {RESULTS_ASOF_S}. Model numbers recalculated from them: {MODEL_ASOF_S}. Rules: official conference tiebreaker policies (links on each conference page). {SHORT_DISC.split(". ")[0]}.</p>{f'<p>{extra}</p>' if extra else ''}</div></section>')
ASK_METHOD = ('<h2 id="ask">Ask KickTip (what-if questions)</h2><p>On each conference, team and playoff page, the Ask KickTip button lets you fix one or more game results (for example, "What if BYU loses to Texas Tech?" or "What if BYU wins?", which means that team\'s next remaining game) and see how the chances change. '
    'It re-runs the same season simulation described above with those results set, and shows the chances before and after. <b>It runs in your browser:</b> when you tap Run, your browser downloads the model data (public files, the same ones that power this site) and the simulation code from this site and does the work itself. The question you type is not sent to any server. '
    'It uses the model selected on the page you are on (the KickTip blend unless you picked another) and each answer says which model it used. A run uses up to 10,000 simulated seasons, fewer on a slow device, and every answer shows the number used, so changes of about a point or less are within simulation noise; '
    'the "before" numbers come from a fresh run too, so they can differ from the page by a point or two. It works with wins and losses only, not scores or margins, and conference-title scenarios are not supported yet. '
    'Ask KickTip gives simulation analysis only; it does not give betting advice, picks or lines, and it declines to.</p>')
ASK_PAGES = ("conference", "team", "playoff", "top25")   # c1: pages that carry the Ask KickTip pill
def RBV(name):   # content-hash cache-busting token for the Rootables assets (first 10 hex of sha256 of src/assets/<name>)
    return hashlib.sha256(open(f"{SITE}/assets/{name}", "rb").read()).hexdigest()[:10]   # hashes the BUILT file (build() copies and fills the assets before any page is written)
CV = ""                                          # asset URLs carry a content hash added at the end of build() (hash_assets): no hand-set cache-busting tokens
def page(title, path, body, *, active="", dyn=False, need="", ptype="static", extra="", desc="", conf="", team="", hero=None, av="", rb=False, ex=(), src_extra=""):
    av = ""   # content hash is added to every /assets/*.js|css reference by hash_assets() after all pages are written
    nav = "".join(f'<a href="{h}"{" class=\"on\" aria-current=\"page\"" if a == active else ""}>{a}</a>' for a, h in NAV)
    desc = desc or "Standings, tiebreakers and paths to the conference championship game for all 11 FBS groups, plus the 12-team playoff field."
    main_attr = f' data-need="{need}" data-page="{ptype}"' + (f' data-conf="{conf}"' if conf else "") + (f' data-team="{team}"' if team else "") + (f' data-exa="{E(ex[0])}" data-exb="{E(ex[1])}"' if ex else "") if dyn else ""
    script = f'<script src="/assets/lg.js{av}" defer></script><script src="/assets/kt.js{av}" defer></script>' if dyn else f'<script src="/assets/kt.js{av}" defer></script>'   # refresh-2032 merge: lg.js keeps ?v=chip2 (file unchanged, same as live); rev2: ungated pages (method, disclaimer, 404) load kt.js too, ONLY so internal links keep ?model= (it returns before any gate/prediction code)
    if ptype == "top25":   # /top25/: own content-hash tokens for kt.js (it gained the KTTop25 hook), top25.js and top25.css, so a cached older kt.js can never meet this page
        script = f'<script src="/assets/lg.js{av}" defer></script><script src="/assets/top25.js?v={RBV("top25.js")}" defer></script><script src="/assets/kt.js{av}" defer></script>'
        extra = f'<link rel="stylesheet" href="/assets/top25.css?v={RBV("top25.css")}">' + extra
    if ptype == "playoff":   # bracket "Fit to screen" (/playoff/ only): own content-hash tokens, no change to kt.js / kt.css
        script += f'<script src="/assets/bracket-fit.js?v={RBV("bracket-fit.js")}" defer></script>'; extra = f'<link rel="stylesheet" href="/assets/bracket-fit.css?v={RBV("bracket-fit.css")}">' + extra
    if ptype == "ccgsim":   # official-rules conference championship game simulator: no model data, no chat pill; own content-hash tokens (src/assets/ccgsim*.js|css)
        script = f'<script src="/assets/lg.js{av}" defer></script><script src="/assets/kt.js{av}" defer></script><script src="/assets/ccgsim.js?v={RBV("ccgsim.js")}" defer></script><script src="/assets/ccgsim-ui.js?v={RBV("ccgsim-ui.js")}" defer></script>'
        extra = f'<link rel="stylesheet" href="/assets/ccgsim.css?v={RBV("ccgsim.css")}">' + extra
    script += f'<script src="/assets/myteams.js?v={RBV("myteams.js")}" defer></script><script src="/assets/account.js?v={RBV("account.js")}" defer></script>'; extra = f'<link rel="stylesheet" href="/assets/myteams.css?v={RBV("myteams.css")}">' + extra   # my-teams build: on every page (header count; the Save control, stars and the My teams section need a page that loads predictions)
    ask = dyn and ptype in ASK_PAGES   # c1 chat
    if ask: script += f'<script src="/assets/chat.js{CV}" defer></script>'
    if rb: script += f'<script src="/assets/rootables.js?v={RBV("rootables.js")}" defer></script>'; extra = f'<link rel="stylesheet" href="/assets/rootables.css?v={RBV("rootables.css")}">' + extra   # Rootables (team pages only): own content-hash version token, so a code change needs no cache purge
    pillbtn = '<button type="button" id="kpill" class="askpill" aria-haspopup="dialog" aria-expanded="false"><i aria-hidden="true">?</i>Ask KickTip: what if...</button>' if ask else ""
    canon = "" if path == "/404.html" else f'<link rel="canonical" href="{BASE}{path}">'
    ogurl = "" if path == "/404.html" else f'<meta property="og:url" content="{BASE}{path}">'
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><title>{E(title)} | KickTip Media</title>
<meta name="description" content="{E(desc)}">{canon}<meta name="color-scheme" content="light">
<link rel="icon" type="image/png" sizes="32x32" href="/assets/brand/icon/kicktip-icon-32.png"><link rel="icon" href="/favicon.ico" sizes="any"><link rel="apple-touch-icon" href="/assets/brand/icon/kicktip-apple-touch-180.png"><link rel="manifest" href="/site.webmanifest"><meta name="theme-color" content="#262B31"><meta property="og:site_name" content="KickTip Media"><meta property="og:type" content="website"><meta property="og:title" content="{E(title)} | KickTip Media"><meta property="og:description" content="{E(desc)}">{ogurl}<meta property="og:image" content="{BASE}/assets/brand/social/kicktip-og-1200x630.png"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630"><meta property="og:image:alt" content="KickTip Media"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:image" content="{BASE}/assets/brand/social/kicktip-og-1200x630.png"><link rel="preload" href="/assets/fonts/BarlowCondensed-Bold.woff2" as="font" type="font/woff2" crossorigin><link rel="preload" href="/assets/fonts/SourceSans3-400.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="/assets/kt.css{av}">{f'<link rel="stylesheet" href="/assets/chat.css{CV}">' if ask else ""}{extra}</head><body{' class="has-ask"' if ask else ''}>
<a class="skip" href="#main">Skip to content</a>
{terms_copy.BANNER_HTML}
<header class="hd"><div class="w"><a class="brand" href="/" aria-label="KickTip Media home"><img src="/assets/brand/logo/kicktip-header-nosub-transparent.png" width="118" height="52" alt="KickTip Media"></a>
<div class="tog" role="group" aria-label="Sport: Football now, basketball coming soon"><span class="on">Football</span><span class="off">Basketball<em class="soon">SOON</em></span></div><nav class="nav" aria-label="Main">{nav}</nav></div></header>
<main id="main"{main_attr}>
{body}
</main>
{sources_block(dyn, src_extra)}
<footer class="ft"><div class="w"><img class="flock" src="/assets/brand/logo/kicktip-media-lockup-transparent.png" width="220" height="97" alt="KickTip Media" loading="lazy"><p><b>Information and entertainment only, not advice or a guarantee. Use at your own risk.</b></p>
<p><a href="/disclaimer/">Full disclaimer</a><a href="/privacy/">Privacy</a><a href="/method/">Method</a><a href="/playoff/">Playoff picture</a><a href="/top25/">Top 25</a><a href="/games/">This week&#8217;s games</a></p>
<p><span class="cred">{logos.CREDIT}.</span> Logos are shown unaltered next to the team, conference or league name; a logo is removed on request.</p><p>from the team behind Mtn Sports Media</p></div></footer>
{pillbtn}{script}</body></html>'''

def hero_html(h1, p, kick="", crumbs="", head=None, after=""):
    """head: optional (css class, logo html, label) -> the logo tile sits beside the h1 (conference: 56 px; team: 80 px; playoff: 56 px league icon with its text label)."""
    h = f"<h1>{E(h1)}</h1>"
    if head:
        cls, tl, label = head
        h = f'<div class="{cls}">{tl}' + (f'<div><span class="lgn">{E(label)}</span>{h}</div>' if label else h) + '</div>'
    return f'<section class="hero"><div class="w">{crumbs}{f"<p class=kick>{E(kick)}</p>" if kick else ""}{h}<p>{p}</p>{after}</div></section>'
def pills(active_slug):
    return "".join(f'<a href="/conference/{s}/"{" class=\"on\" aria-current=\"page\"" if s == active_slug else ""}>{M.conf(k, 24)}{E(n)}</a>' for k, n, s in CONFS)
def tbl(head, rows, cls="", minw="", kind=""):
    """kind: 'n' = rank tables (col 1 = #/seed, col 2 = team; both stay pinned on phones), 'g' = game tables (col 1 = date, col 2 = game; both pinned)."""
    return f'<p class="hint">Swipe the table sideways &rarr;</p><div class="tw{" tk-" + kind if kind else ""}"><table{cls}><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table></div>'
PENDING = '<span class="lk">Loading</span>'   # placeholder in the static HTML until kt.js fills the numbers (static pages carry no model number)
LINE_NOTE = ('<p class="note"><b>How to read the spread and expected margin.</b> Each spread names the favorite and the points ESPN lists it as winning by, with a minus sign: Utah \u22123.0 means Utah is the favorite by 3.0. KickTip\'s expected margin is our own number from the model, shown as the team KickTip favors and the points, for example \u201cUtah by 3.5\u201d (rounded to 0.5 on the page). '
             'The spread is shown with the time it was read (MT) and only when ESPN has listed one. Neither number is a recommendation. Information only.</p>')
def game_cards(games, focus=None, slate=False):
    """Game list as cards (Creative D1-D4). Static HTML carries only facts (date, teams, status); every number (win chance, KickTip line, market line, gap) is drawn by assets/kt.js after the data loads
    into [data-c=wp] and [data-c=ln]. A started game has no win chance or KickTip line; if a line was stored for it the block shows 'Line closed' and the last number. FCS games have no lines block."""
    out = []
    for g in games:
        _, when = game_when(g); h, a = SHORT[g["home"]], SHORT.get(g["away"], "FCS opponent"); stt = game_state(g); fcs = g["away"] not in TEAMS
        if focus:
            opp = a if g["home"] == focus else h; site = "Neutral site" if g["neutral"] else ("Home" if g["home"] == focus else "Away")
            oslug = SLUG.get(g["away"] if g["home"] == focus else g["home"]); ofull = g["away"] if g["home"] == focus else g["home"]
            ol = tcell(ofull, True) if oslug else f'<span class="tnm">{M.team(None, 24, True)}<span>{E(opp)}</span></span>'
            tm = f'{ol}<span class="note">{site}{", conference game" if g["conference_game"] else ""}</span>'
        else:
            tm = f'<span class="gm">{gunit(g["away"] if g["away"] in TEAMS else None, a)}<span>{"vs" if g["neutral"] else "at"}</span>{gunit(g["home"], h)}</span>'
        top = f'<div class="gtag">{E(when)}</div><div class="gtm">{tm}</div>'
        if stt:
            lv = g.get("live"); sc = f" ({E(a)} {lv[1]}, {E(h)} {lv[0]} at last check)" if lv else ""
            top += f'<p class="gst">{E(stt)}{sc}. No win chance or KickTip line is shown once a game has started.</p>'
        else: top += f'<div class="gwc" data-c="wp">{PENDING}</div>'
        ln = f'<div class="gln" data-c="ln">{PENDING}</div>' if (not fcs and (not stt or (g["id"] in MLINE and g.get("status") not in ("STATUS_POSTPONED", "STATUS_CANCELED")))) else ""
        u, _ = game_when(g); tba = g["date_utc"][11:] in ("04:00Z", "05:00Z")
        sl = f' data-d="{int(u.timestamp())}" data-cf="{E(gconfs(g)[0])}" data-cn="{E(gconfs(g)[1])}"' if slate else ""
        out.append(f'<article class="gc" data-gk="{gkey(g)}" data-id="{g["id"]}" data-h="{E(h)}" data-a="{E(a)}" data-k="{0 if tba else int(u.timestamp())}"{sl} aria-label="{E(a)} at {E(h)}"><div class="gct">{top}</div>{ln}</article>')
    return '<p class="note ionly">Information only, not betting advice.</p><div class="gcl' + (" gcm" if slate else "") + '">' + "".join(out) + '</div>'
def gconfs(g):
    """(space-separated conference slugs of the two teams, label of the home team's conference) for the /games/ filter and sort."""
    cs = {k: s_ for k, _, s_ in CONFS}; nm = {k: n for k, n, _ in CONFS}
    ks = [TEAMS[t]["conf"] for t in (g["home"], g["away"]) if t in TEAMS]
    return " ".join(sorted({cs[k] for k in ks})), nm[TEAMS[g["home"]]["conf"]]
def slate_games():
    """Games that have not started, FBS vs FBS, kicking off within 7 days of the data refresh, by date."""
    lim = REF_T + dt.timedelta(days=7)
    return [g for g in sorted(GAMES, key=lambda g: (g["date_utc"], g["id"])) if not game_state(g) and g["away"] in TEAMS and game_when(g)[0] < lim]
def games_page():
    gl = slate_games()
    cs = [(k, n, s_) for k, n, s_ in CONFS if any(gconfs(g)[0].split() and s_ in gconfs(g)[0].split() for g in gl)]
    opts = '<option value="all">All conferences</option>' + "".join(f'<option value="{s_}">{E(n)}</option>' for _, n, s_ in cs)
    ctl = ('<div class="gctl" data-slate-ctl hidden><label>Conference <select id="gsel">' + opts + '</select></label>'
           '<label>Sort by <select id="gsort"><option value="dA">Date and time (earliest first)</option><option value="dD">Date and time (latest first)</option><option value="cA">Conference (A to Z)</option>'
           '<option value="gA">Gap (smallest first)</option><option value="gD">Gap (largest first)</option></select></label><span class="note" data-slate-count aria-live="polite"></span></div>')
    rows = ""
    for g in gl:
        u, when = game_when(g); tba = g["date_utc"][11:] in ("04:00Z", "05:00Z"); h, a = SHORT[g["home"]], SHORT[g["away"]]; cf, cn = gconfs(g)
        rows += (f'<tr data-gk="{gkey(g)}" data-id="{g["id"]}" data-h="{E(h)}" data-a="{E(a)}" data-k="{0 if tba else int(u.timestamp())}" data-d="{int(u.timestamp())}" data-cf="{E(cf)}" data-cn="{E(cn)}">'
                 f'<td>{E(when)}</td><th scope="row"><span class="gm">{gunit(g["away"], a)}<span>{"vs" if g["neutral"] else "at"}</span>{gunit(g["home"], h)}</span></th><td>{E(cn)}</td>'
                 f'<td data-c="wp">{PENDING}</td><td data-c="kl">{PENDING}</td><td data-c="mk">{PENDING}</td></tr>')   # live B5 layout: no Gap column
    sb = lambda k, t: f'<th aria-sort="{"ascending" if k == "d" else "none"}"><button type="button" class="sb" data-sort="{k}">{t}</button></th>'
    head = sb("d", "Date (MT)") + "<th>Game</th>" + sb("c", "Conference") + "<th>KickTip win chance</th><th>KickTip's expected margin</th><th>Spread (ESPN)</th>"   # live B5 header labels (copy owned by the live site)
    table = (f'<div class="tw gtbl"><table class="gt"><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table></div>')
    body = (hero_html("This week's games", "Every FBS-vs-FBS game that has not started and kicks off within a week of the last data refresh, with KickTip's expected margin and, when one has been posted, ESPN's spread.", "Game slate") +
            f'<section class="sec"><div class="w">{banner(True)}<div class="card">{CRED}<p class="note">{len(gl)} games. Sorted by date and time unless you choose another sort. Sorting only reorders the list; nothing is ranked or highlighted.</p>{ctl}'
            f'<div data-slate>{game_cards(gl, slate=True)}{table}</div>' + LINE_NOTE + '<p class="note">Lines usually appear within about a day of kickoff. Games against FCS opponents and games that have started are not listed here.</p></div></div></section>')
    return page("This week's games", "/games/", body, active="", dyn=True, need="pred-teams,pred-games,pred-lines", ptype="slate",
                desc="This week's FBS games with KickTip's expected margin and ESPN's spread when one has been posted. Information only, not betting advice.")

# ---------------------------------------------------------------- plain-English tiebreak steps
STEP = {"h2h2": "Head-to-head result between the two teams", "common_pct": "Record against all common conference opponents",
        "common_ordered": "Record against the highest-placed common opponent in the standings, then the next, and so on",
        "opp_conf_pct": "Combined conference win percentage of each team's conference opponents", "wins12": "Total wins in a 12-game season",
        "rating": "Ranking-based step (CFP rank, computer composite or similar): KickTip uses its rating as a stand-in",
        "margin_proxy": "Scoring-margin step: KickTip uses its rating as a stand-in", "overall_pct": "Overall win percentage",
        "ordered_any": "Record against the highest-placed opponent in the standings, then the next, and so on",
        "div_pct": "Record against division opponents",
        "ordered_div": "Record against the highest-placed team in the division standings, then the next", "common_nondiv": "Record against common non-division opponents",
        "fbs_pct": "Win percentage against FBS opponents", "draw": "Random draw (coin toss)"}
OFFICIAL = ("theacc.com", "big12sports.com", "secsports.com", "theamerican.org", "conferenceusa.com", "sunbeltsports.org", "themw.com", "bigten.org", "getsomemaction.com", "pac-12.com", "collegefootballplayoff.com")
def ccgw(t):   # display-only: the rules data (src/rules.py, part of the model version hash, so NOT edited) says 'title game'; every shipped page says 'conference championship game'
    return re.sub(r"(?<!conference )title[ -]game", "conference championship game", t)
def src_links(srcs):
    out = []
    for s in srcs:
        s = ccgw(s)
        m = re.match(r"(https?://([^/\s]+)\S*)", s)
        if not m: out.append(f'<li><span class="note">{E(s)}</span></li>'); continue
        host = m.group(2).replace("www.", ""); note = s[len(m.group(1)):].strip(); kind = "official source" if host in OFFICIAL else "published report"
        auto = " (link may not open for automated readers)" if "bigten.org/fb/article/blt6104802d94ebe1ab" in m.group(1) else ""
        out.append(f'<li><a href="{E(m.group(1))}" rel="noopener">{E(host)}</a> <span class="note">{kind}{" " + E(note) if note else ""}{auto}</span></li>')
    return "".join(out)

# ---------------------------------------------------------------- pred data (dyn JSON)
def model_data(mid):
    """(sim_teams, sim_games, paths) of one model; the default is data/out, alternates are data/out/m/<id>/ (same data, seed and as_of, written by run_all.py)."""
    if mid == MR.DEFAULT_ID: return ST, SG, PA
    d = f"{OUTD}/m/{mid}"; st, sg, pa = J(f"{d}/sim_teams.json"), J(f"{d}/sim_games.json"), J(f"{d}/paths.json")
    assert st["model"] == mid and sg["model"] == mid, f"{d} was not simulated with model {mid}"
    assert st["as_of"] == ST["as_of"] and st["seasons"] == ST["seasons"] and st["seed"] == ST["seed"], f"{mid}: as_of/seasons/seed differ from the default run"
    assert [(g["id"], g["home"], g["away"]) for g in sg["games"]] == [(g["id"], g["home"], g["away"]) for g in SG["games"]], f"{mid}: game list differs from the default run"
    assert {t["team"]: t["rank_now"] for t in st["teams"]} == {t["team"]: t["rank_now"] for t in ST["teams"]}, f"{mid}: rank_now differs (it is the KickTip rating rank for every model)"
    return st, sg, pa
def model_meta(mid):
    m = MR.BY_ID[mid]; return dict(id=mid, name=m["name"], btn=m["btn"], default=bool(m.get("default")), short=m["short"], blurb=m["blurb"])

BUNDLES = {}   # model id -> the sim bundle as shipped (the Top 25 rank order is read from it)
MOVES_REPORT = {}   # internal (data/out/moves_report.json, not shipped): per model, why chips are or are not shown
def build_pred(mid=MR.DEFAULT_ID):
    st_, sg_, pa_ = model_data(mid); sim_of = {t["team"]: t for t in st_["teams"]}
    chip, chip_info = moves.chips(mid, st_, SHORT); MOVES_REPORT[mid] = chip_info
    teams = {}
    for full, v in TEAMS.items():
        s = sim_of[full]; pp = pa_["teams"].get(full)
        teams[v["slug"]] = dict(n=v["short"], cs=CSLUG[v["conf"]], cn=CNAME[v["conf"]], c=s["p_ccg"], w=s["p_conf_title"], p=s["p_cfp_12"], b=s["p_cfp_bye"],
                                x=(pp["p_ccg_if_wins_out"] if pp else None))
        if full in chip: teams[v["slug"]]["m"] = chip[full]       # 'why it moved' chip: [rounded signed points, popover text]; absent = no chip (src/moves.py decides; assets/kt.js only draws it)
    # field "if the season ended today": current conference leaders stand in for champions; the committee stand-in is the rating rank (cfp.field)
    names = list(TEAMS); rank = {i: TEAMS[n]["sim"]["rank_now"] for i, n in enumerate(names)}; idx = {n: i for i, n in enumerate(names)}
    order = sorted(range(len(names)), key=lambda i: rank[i])
    champs = {ck: idx[STAND[ck][0]["team"]] for ck in STAND if ck != "ind"}
    nd = idx.get("Notre Dame Fighting Irish")
    g6 = [i for i, n in enumerate(names) if TEAMS[n]["conf"] in cfp.G6]
    seeds = cfp.field(rank, champs, order, nd, g6); lead = set(champs.values())
    field = [[TEAMS[names[i]]["slug"], 1 if i in lead else 0] for i in seeds]
    pt = dict(model=model_meta(mid), models=[model_meta(x["id"]) for x in MR.MODELS], model_label="Model line, KickTip analysis (not a market line)", model_asof=MODEL_ASOF_S, seasons=META["seasons"], teams=teams, field=field)
    g = {}
    for x in sg_["games"]:
        k = gkey(x)
        if game_state(x): continue                      # started, postponed or canceled: no pre-game numbers
        if x["away"] == "FCS opponent": g[k] = [None, None, None]; continue
        g[k] = [x["model_home_win_prob"], x["model_spread_home"], x.get("model_spread_raw")]   # [win chance, KickTip line (home side, rounded to 0.5), unrounded KickTip line or null]. Market lines are model-independent: /data/pred-lines.json
    pg = dict(model=model_meta(mid), model_label="Model line, KickTip analysis (not a market line)", model_asof=MODEL_ASOF_S, g=g)
    paths = {}
    for full, p in pa_["teams"].items():
        paths[SLUG[full]] = dict(rec=p["conf_record"], best=p["best_case_conf_record"], st=p["status"], wo=p["p_ccg_if_wins_out"],
                                 rows=[[r["final_conf_wins"], r["share_of_sims"], r["p_ccg"]] for r in p["by_final_conf_wins"]])
    pp = dict(model=model_meta(mid), t=paths)
    return pt, pg, pp, field

# ---------------------------------------------------------------- pages
TOP25_RANK_BY = "gs"   # "gs": the strength each model uses for its own lines (sim-bundle model.gs, falling back to model.s exactly as assets/ks/sim.js does), so switching models re-ranks.
                      # "rank_now": the MSM composite rating rank, the same under every model (the bracket order on /playoff/). One constant decides; flip it and rebuild.
def build_top25(mid, pt_):
    """data/pred-top25.json (per model): all 138 FBS teams in KickTip rank order as [slug, wins, losses, strength]. Ties break by Make the 12 chance, then name. The strength is shipped only so a test can
    re-check the order; the page never shows it (it is in model units, not rating points: see NOTES-top25.md)."""
    b = BUNDLES[mid]; m = b["model"]; g = m.get("gs") or m["s"]; rows = []
    for i, t in enumerate(b["teams"]):
        v = TEAMS.get(t["n"])
        if not v: continue                                    # the FCS placeholder
        key = round(g[i], 4) if TOP25_RANK_BY == "gs" else -v["sim"]["rank_now"]
        rows.append((-key, -pt_["teams"][v["slug"]]["p"], v["short"], [v["slug"], v["sim"]["overall_w"], v["sim"]["overall_l"], key]))
    rows.sort(key=lambda r: r[:3]); assert len(rows) == 138
    return dict(model=mid, rank_by=TOP25_RANK_BY, asof=MODEL_ASOF.strftime("%b %-d, %-I:%M %p"), teams=[r[3] for r in rows])
def build_polls(src=None):
    """data/polls.json for the page, from data/out/polls.json (python3 src/polls.py): ESPN ids become our slugs and each poll's own publication time is turned into an MT label. A poll that is missing or
    unreleased is written released=false, and the page then shows 'not released yet' and dashes (it never shows another week's poll under this one)."""
    if src is None: src = json.load(open(f"{OUTD}/polls.json")) if os.path.exists(f"{OUTD}/polls.json") else {"polls": {}}
    wk = [int(q["week"]) for q in src["polls"].values() if q.get("released") and q.get("week")]
    if not src["polls"]: print("WARNING: data/out/polls.json missing; run python3 src/polls.py. The page will say the polls are not released yet.")
    esp = {str(v["espn"]): v["slug"] for v in TEAMS.values()}; out = {}
    for k, label in (("ap", "AP Top 25"), ("coaches", "Coaches Poll")):
        q = src["polls"].get(k)
        if not q or not q.get("released") or not q.get("published") or (wk and int(q["week"]) < max(wk)):   # an older week than the other poll's is "not released yet": last week's rank never sits in this week's column
            if q and q.get("released") and wk and int(q["week"]) < max(wk): print(f"NOTE: {label} is still week {q['week']} while the other poll is week {max(wk)}: shown as not released yet")
            out[k] = dict(name=label, released=False); continue
        pub = dt.datetime.strptime(q["published"], "%Y-%m-%dT%H:%MZ").replace(tzinfo=dt.timezone.utc).astimezone(MT)
        un = [x for x in q["ranks"] if str(x["espn"]) not in esp]
        if un: print(f"WARNING: {label}: {len(un)} ranked team(s) not matched to a KickTip team: {un}")
        out[k] = dict(name=label, released=True, week=q["week"], asof=pub.strftime("%b %-d, %-I:%M %p"), pub=q["published"], ranks=[[x["r"], esp[str(x["espn"])], x["rec"]] for x in q["ranks"] if str(x["espn"]) in esp])
    return dict(polls=out)

def home_page():
    cards = "".join(f'<a class="conf" href="/conference/{s}/"><span class="cht">{M.conf(k, 32, True)}<b>{E(n)}</b></span><span>{sum(1 for v in TEAMS.values() if v["conf"] == k)} teams{" &middot; no conference championship game" if k == "ind" else ""}</span></a>' for k, n, s in CONFS)
    how = ('<div class="how"><div class="card"><span class="n">STEP 1</span><b>Read every result</b>Scores and schedules for all 138 FBS teams come from ESPN public data and are checked each day.</div>'
           f'<div class="card"><span class="n">STEP 2</span><b>Play out the season</b>We simulate the rest of the season {SEASONS} times, using conference tiebreaker rules to pick the teams in each conference championship game.</div>'
           '<div class="card"><span class="n">STEP 3</span><b>Read the chances</b>Each team gets a chance to reach its conference championship game, win its conference and make the 12-team playoff.</div></div>')
    states = ('<section class="sec" data-pt="0"><div class="w"><h2>State sites</h2><div class="strip">'
              '<div class="st"><span class="tag live">Live</span><b>Mtn Sports Media</b>Utah</div>'
              '<div class="st"><span class="tag">Coming soon</span><b>Arizona</b></div>'
              '<div class="st"><span class="tag">Coming soon</span><b>Colorado</b></div></div></div></section>')
    body = (hero_html("Every conference race. One playoff picture.", "Standings, tiebreakers and paths to the conference championship game for all 11 FBS groups, plus the 12-team field, refreshed daily.", "KickTip Media") +
            '<section class="sec mtsec" id="my-teams" aria-label="My teams" hidden><div class="w" id="mt-root"></div></section>' +
            f'<section class="sec"><div class="w">{banner(True)}<div class="card"><h2>Top chances to make the 12</h2><p class="ccgdef">CCG = conference championship game</p>{CRED}'
            + tbl('<th class="n">#</th><th>Team</th><th>Conference</th><th class="n">Make the 12<small>model</small></th><th class="n">First-round bye<small>model</small></th><th class="n">Reach CCG<small>model</small></th><th class="n">Win conference<small>model</small></th>', "", ' id="top12"', kind="n")
            + '<p class="note">Chances come from ' + SEASONS + ' simulated seasons. Teams in a conference with no conference championship game show n/a for those columns.</p><p class="cta"><a href="/playoff/">See the 12-team field and bracket</a> &middot; <a href="/games/">See this week&#8217;s games</a></p><p class="cta"><a href="/top25/">See the KickTip Top 25</a></p></div></div></section>'
            f'<section class="sec" style="padding-top:0" id="conferences"><div class="w"><h2>Conference races</h2><div class="grid">{cards}</div></div></section>'
            + states +
            f'<section class="sec" style="padding-top:0"><div class="w"><h2>How it works</h2>{how}<p class="cta"><a href="/method/">Read the full method</a></p></div></section>').replace(' style="padding-top:0"', ' data-pt="0"')
    return page("Every conference race, one playoff picture", "/", body, active="Home", dyn=True, need="pred-teams", ptype="home", ex=("BYU Cougars", "Utah Utes"))

def conf_page(ck, cname, cs):
    R = rules.RULES[ck]; S = STAND[ck]; n = len(S); fmt = R["fmt"]
    members = [TEAMS[r["team"]] for r in S]
    if fmt == "top2": lead = f"{n} teams. The top two in conference play meet in the conference championship game. Chances come from {SEASONS} simulated seasons."
    elif fmt == "div": lead = f"{n} teams in two divisions. The East and West division champions meet in the conference championship game. Chances come from {SEASONS} simulated seasons."
    else: lead = f"{n} teams with no conference championship game. Their playoff chances come from {SEASONS} simulated seasons."
    divcol = fmt == "div"
    if fmt == "none":
        head = '<th class="n">#</th><th>Team</th><th class="n">Overall</th><th class="n">Make the 12<small>model</small></th>'
        rows = "".join(f'<tr><td class="n">{i+1}</td><td>{tcell(r["team"], i >= 8)}</td><td class="n">{r["overall"]}</td><td class="n" data-f="p" data-t="{SLUG[r["team"]]}">{PENDING}</td></tr>' for i, r in enumerate(S))
        note = "Independents have no conference standings. Order here is by overall record."
    else:
        head = ('<th class="n">#</th><th>Team</th>' + ("<th>Division</th>" if divcol else "") + '<th class="n">Conf</th><th class="n">Overall</th><th class="n">Reach CCG<small>model</small></th><th class="n">Win conference<small>model</small></th><th class="n">Make the 12<small>model</small></th>')
        rows = "".join(f'<tr><td class="n">{i+1}</td><td>{tcell(r["team"], i >= 8)}</td>' + (f'<td>{BELT_DIV.get(r["team"], "")}</td>' if divcol else "") +
                       f'<td class="n">{r["conf_w"]}-{r["conf_l"]}</td><td class="n">{r["overall"]}</td>' + "".join(f'<td class="n" data-f="{f}" data-t="{SLUG[r["team"]]}">{PENDING}</td>' for f in "cwp") + '</tr>' for i, r in enumerate(S))
        note = "Listed by conference win percentage, then conference wins, then overall record, then name. Official tiebreakers are applied inside the simulation, not in this table."
    # remaining conference games
    if fmt == "none":
        mem = {r["team"] for r in S}; rem = [g for g in GAMES if g["home"] in mem or g["away"] in mem]; rtitle = "Remaining games"
    else:
        mem = {r["team"] for r in S}; rem = [g for g in GAMES if g["conference_game"] and g["home"] in mem and g["away"] in mem]; rtitle = "Remaining conference games"
    rem.sort(key=lambda g: g["date_utc"])
    rem_html = (f'<div class="card"><h2>{rtitle}</h2>' + game_cards(rem) + LINE_NOTE + '</div>') if rem else ""
    if fmt != "none": rem_html += results_card(members=[r["team"] for r in S], title="Recent results", limit=20)
    # tiebreak explainer
    if fmt == "none": tb = "<p>Independents do not play for a conference title, so no conference tiebreaker applies. Their playoff chances use the same 12-team rules as everyone else.</p>"
    else:
        steps = "".join(f"<li>{E(STEP[s])}</li>" for s in R["two"])
        tb = (f'<p>When two teams finish tied in conference play, {E(cname)} applies these steps in order until one team is ahead:</p><ol>{steps}</ol>'
              '<p class="note">Ties among three or more teams use a similar list, starting with results among the tied teams. This is a plain-English summary of the official policy; the official text controls.</p>')
    flags = "".join(f"<li>{E(ccgw(f))}</li>" for f in R["flags"])
    tgame = (f'<div class="card"><h2>Conference championship game</h2><p>{E(nice_ccg(R["ccg"]))}</p><p class="note">Time, TV and site are as announced by the conference.</p></div>' if fmt != "none" else "")
    simcard = (f'<div class="card"><h2>Conference championship game simulator</h2><p>Set the remaining games and see who would play in the conference championship game under {E(cname)}\u2019s published rules.</p><p class="cta"><a href="/conference/{cs}/simulator/">Open the simulator</a></p></div>' if ck in CCG_RULES else "")
    side = (tgame + simcard + f'<div class="card"><h2>Who controls their destiny</h2><ul class="dest" id="dest"><li>{PENDING}</li></ul><p class="note">Chance to reach the conference championship game if the team wins all of its remaining conference games (model).</p></div>' * (fmt != "none") +
            f'<div class="card"><h2>How {E(cname)} ties are broken</h2>{tb}</div>' +
            (f'<div class="card"><h2>Known limitations</h2><ul>{flags}</ul><h3>Rules sources</h3><ul>{src_links(R["sources"])}</ul></div>' if fmt != "none" else ""))
    body = (hero_html(f"{cname} race", E(lead), "Conference", head=("chd", M.conf(ck, 56), None)) +
            f'<section class="sec" style="padding-bottom:0"><div class="w"><h2 class="h2s">All 11 conferences</h2><nav class="tabs" aria-label="All 11 conferences">{pills(cs)}</nav><p class="hint">Swipe the conference list sideways &rarr;</p></div></section>'
            f'<section class="sec" data-pt="8"><div class="w">{banner(True)}</div><div class="w two"><div><h2>Standings</h2>{CCGDEF if fmt != "none" else ""}{CRED}{tbl(head, rows, kind="n")}<p class="note">{E(note)} Chances: share of {SEASONS} simulated seasons (model).</p>{rem_html}</div><div>{side}</div></div></section>')
    body = body.replace(' style="padding-bottom:0"', ' data-pb="0"')
    return page(f"{cname} race", f"/conference/{cs}/", body, active="Conferences", dyn=True, need="pred-teams,pred-games,pred-lines", ptype="conference", conf=cs, ex=(members[0]["full"], members[min(1, len(members) - 1)]["full"]), desc=f"{cname} standings, remaining games and chances to reach the conference championship game and make the 12-team playoff.")

def team_page(full, v):
    ck = v["conf"]; cname = CNAME[ck]; cs = CSLUG[ck]; R = rules.RULES[ck]; S = STAND[ck]
    row = next(r for r in S if r["team"] == full); pos = S.index(row) + 1
    games = team_games(full); fmt = R["fmt"]
    if fmt == "none": standing = f"{cname}: no conference standings or conference championship game. Overall record {row['overall']}."
    else: standing = f"Conference record {row['conf_w']}-{row['conf_l']}, overall {row['overall']}. Currently {pos} of {len(S)} in the {cname} order (conference win percentage)."
    tiles = ""
    labels = [("c", "Reach CCG"), ("w", "Win the conference"), ("p", "Make the 12"), ("b", "First-round bye")]
    if fmt == "none": labels = labels[2:]
    tiles = '<div class="tiles">' + "".join(f'<div class="tile"><b data-tile="{k}">&ndash;</b><span>{l} (model)</span></div>' for k, l in labels) + '</div>'
    pathcard = ""
    if fmt != "none":
        pathcard = ('<div class="card"><h2>Paths to the conference championship game</h2><p class="ccgdef">CCG = conference championship game</p><p>Chance to reach the conference championship game by number of conference wins, from the same simulated seasons. If the team wins out, its chance is <b data-wo>&ndash;</b>.</p>'
                    + tbl('<th class="n">Final conference wins</th><th class="n">Share of seasons<small>model</small></th><th class="n">Reach CCG<small>model</small></th>', f'<tr><td colspan="3">{PENDING}</td></tr>', ' id="paths" style="min-width:0"').replace(' style="min-width:0"', ' class="fld"').replace('<div class="tw">', '<div class="tw tk-p">') + '</div>')
    others = "".join(f'<li><a href="/team/{TEAMS[r["team"]]["slug"]}/">{E(SHORT[r["team"]])}</a></li>' for r in S if r["team"] != full)
    games_card = (f'<div class="card"><h2>Remaining games</h2>{CRED}' + game_cards(games, full) + LINE_NOTE +
                  '<p class="note">Games against FCS opponents are counted in the simulation but have no line.</p></div>') if games else '<div class="card"><h2>Remaining games</h2><p>No regular-season games remain in our schedule data.</p></div>'
    games_card += results_card(full=full, title="Results")
    crumbs = f'<p class="crumbs"><a href="/conference/{cs}/">{E(cname)}</a></p>'
    body = (hero_html(v["short"], E(standing), "Team path", crumbs, head=("thd", M.team(full, 80), None), after=f'<div class="mt-svw on-dark" data-mtsave data-slug="{v["slug"]}" data-name="{E(v["short"])}" hidden></div>') +
            f'<section class="sec"><div class="w">{banner(True)}<h2>Chances</h2>{CCGDEF if fmt != "none" else ""}{tiles}<p class="note">Chances come from {SEASONS} simulated seasons, using the model selected in the model control. Not a guarantee.</p></div></section>'
            f'<section class="sec rbs"><div class="w"><section class="card rb" id="rootables" aria-labelledby="rbh" data-rb="idle" data-name="{E(v["short"])}"{" data-noccg=" + chr(34) + "1" + chr(34) if fmt == "none" else ""}><div class="rb-hd"><h2 id="rbh">Rootables</h2></div><p class="rb-sub">Who to cheer for this week, for {E(v["short"])}\u2019s make-the-12 chance.</p>'
            '<button type="button" class="rb-run" data-run>Run Rootables</button>' + terms_copy.RUN_FULL_HTML + '<noscript><p class="rb-msg">Turn on JavaScript to run Rootables.</p></noscript></section></div></section>'
            f'<section class="sec" data-pt="0"><div class="w two"><div>{games_card}</div><div>{pathcard}'
            f'<div class="card"><h2>More in the {E(cname)}</h2><ul class="chips">{others}</ul></div></div></div></section>')
    return page(f"{v['short']} path", f"/team/{v['slug']}/", body, active="Conferences", dyn=True, need="pred-teams,pred-games,pred-paths,pred-lines", ptype="team", team=v["slug"], conf=cs, rb=True, ex=(full, full),
                desc=f"{v['short']}: conference standing, remaining games with KickTip's expected margin and ESPN's spread, and chances to reach the conference championship game and make the playoff field.")

# ---------------------------------------------------------------- full bracket (b9). Static markup only: seeds and format text, never a team or a number. kt.js fills [data-seed] on arrival.
def bk_team(i, bye=False):
    return f'<div class="sl{" bye" if bye else ""}"><span class="sd">{i}</span><span class="tm" data-seed="{i}"></span></div>'
def bk_win(txt, key):
    return f'<div class="sl ph"><span class="sd"></span><span class="tm" data-win="{key}">{txt}</span></div>'
def bk_game(label, slots, gid, aria):
    return f'<li class="gm" data-g="{gid}"><div class="g" role="group" aria-label="{aria}"><p class="gl">{label}</p>{slots}</div></li>'
def bracket_html():
    r1 = "".join(bk_game(f"No. {i} hosts No. {17 - i}", bk_team(i) + bk_team(17 - i), f"r1-{i}", f"First round: No. {i} hosts No. {17 - i}") for i in (5, 8, 6, 7))
    qf = "".join(bk_game(f"No. {i} vs No. {a}/{b} winner", bk_team(i, True) + bk_win(f"Winner of No. {a} vs No. {b}", f"{a}-{b}"), f"qf-{i}", f"Quarterfinal: No. {i} plays the winner of No. {a} vs No. {b}")
                 for i, a, b in ((4, 5, 12), (1, 8, 9), (3, 6, 11), (2, 7, 10)))
    sf = (bk_game("Semifinal A", bk_win("Winner of the No. 4 quarterfinal", "q4") + bk_win("Winner of the No. 1 quarterfinal", "q1"), "sf-a", "Semifinal A: winners of the No. 4 and No. 1 quarterfinals") +
          bk_game("Semifinal B", bk_win("Winner of the No. 3 quarterfinal", "q3") + bk_win("Winner of the No. 2 quarterfinal", "q2"), "sf-b", "Semifinal B: winners of the No. 3 and No. 2 quarterfinals"))
    fin = bk_game("National championship", bk_win("Winner of semifinal A", "sfa") + bk_win("Winner of semifinal B", "sfb"), "f", "National championship: winners of semifinals A and B")
    rd = lambda cls, h, g: f'<div class="rd {cls}"><h3>{h}</h3><ol>{g}</ol></div>'
    return ('<div class="bkt" data-bkt hidden role="group" aria-label="Bracket view"><button type="button" class="bkb" data-bkview="full" aria-pressed="true">Full bracket</button><button type="button" class="bkb" data-bkview="rounds" aria-pressed="false">By round</button></div>'
            '<p class="hint bkh">Swipe the bracket sideways &rarr;</p>'
            '<div class="bkw" tabindex="0" role="region" aria-label="Playoff bracket, scrolls sideways on small screens"><div class="bk" data-bk="full">'
            + rd("r1", "First round", r1) + rd("r2", "Quarterfinals", qf) + rd("r3", "Semifinals", sf) + rd("r4", "Championship", fin) + '</div></div>'
            '<p class="note">Seeds are 1 to 12 by rank. The higher seed hosts in the first round and byes go to seeds 1 to 4. Quarterfinals: 1 plays the 8/9 winner, 2 plays the 7/10 winner, 3 plays the 6/11 winner, 4 plays the 5/12 winner. The bracket is not reseeded. The percentages are each team\'s chance to make the 12 over '
            f'{SEASONS} simulated seasons (model), not the chance of winning a game. KickTip does not publish playoff-game probabilities. The full field is in the table below.</p>'
            '<p class="note bkcue">Bracket order uses the MSM team rank as a committee stand-in, under every model.</p>')
def playoff_page():
    br = bracket_html()
    logic = ('<ul><li>The field has 12 teams. The champions of the ACC, Big Ten, Big 12 and SEC get automatic bids. The highest-ranked team from the American, Conference USA, MAC, Mountain West, Pac-12 and Sun Belt also gets one, whether or not it is a champion. Notre Dame gets one if it is ranked in the top 12. The remaining spots go to the next highest-ranked teams: seven in all when Notre Dame is not in the top 12, six when it is.</li>'
             '<li>Teams are seeded 1 to 12 by rank. Seeds 1 to 4 get a first-round bye. Seeds 5 to 8 host first-round games against seeds 12 to 9.</li>'
             '<li>The first-round winners meet seeds 4, 3, 2 and 1 in the quarterfinals, then the bracket runs to the national championship game.</li></ul>'
             '<p class="note">The field below is "if the season ended today": current conference leaders stand in for champions and KickTip\'s rating rank stands in for the selection committee. It is a model view, not the committee\'s ranking. Automatic qualifiers ranked outside the top 12 are seeded after the at-large teams, and only the four highest seeds get byes. Sources: the College Football Playoff\'s Jan. 23, 2026 format announcement (12 teams, byes, home first-round games); for the automatic-bid breakdown, its <a href="https://collegefootballplayoff.com/news/2026/8/6/sc-aug-2627" rel="noopener">Aug. 6, 2026 announcement</a> and <a href="https://www.ncaa.com/news/football/article/2026-02-03/how-college-football-playoff-automatic-qualifiers-work-byes-seeds" rel="noopener">NCAA.com\'s explainer</a>.</p>')
    fh = '<th class="n">Seed</th><th>Team</th><th>Conference</th><th>Path</th>'
    body = (hero_html("Playoff picture", "If the season ended today: 12 teams, the top 4 seeds get byes, and seeds 5 to 8 host first-round games.", "12-team field", head=("phd", M.league(56), "NCAA Football")) +
            f'<section class="sec"><div class="w">{banner(True)}<div class="card"><h2>How the field is chosen</h2>{logic}<p class="cta"><a href="/top25/">See the KickTip Top 25</a></p></div>'
            f'<div class="card" id="bracket"><h2>Bracket if the season ended today</h2>{CRED}{br}</div>'
            f'<div class="card"><h2>The field</h2>{tbl(fh, "", " id=\"field\" class=\"fld\"", kind="n")}<p class="note bkcue">Bracket order uses the MSM team rank as a committee stand-in, under every model.</p></div>'
            f'<div class="card"><h2>Chances to make the 12</h2><p class="ccgdef">CCG = conference championship game</p>{tbl(f"""<th class="n">#</th><th>Team</th><th>Conference</th><th class="n">Make the 12<small>model</small></th><th class="n">First-round bye<small>model</small></th><th class="n">Reach CCG<small>model</small></th><th class="n">Win conference<small>model</small></th>""", "", " id=\"chances\"", kind="n")}'
            f'<p class="note">Top 25 teams by chance to make the 12. Chances come from {SEASONS} simulated seasons (model).</p></div></div></section>')
    return page("Playoff picture", "/playoff/", body, active="Playoff Picture", dyn=True, need="pred-teams", ptype="playoff", ex=("BYU Cougars", "Utah Utes"), desc="The 12-team playoff field, bracket logic and each team's chance to make the 12.")

def top25_page():
    th = ('<th class="n">KickTip rank</th><th>Team</th><th class="n">AP rank</th><th class="n">Coaches rank</th><th class="n">KickTip vs AP</th><th class="n">KickTip vs Coaches</th>'
          '<th>Conference</th><th class="n">Record</th><th class="n">Make the 12<small>model</small></th>')
    lst = lambda tid, lid, cap: f'<div class="tw t25-tw"><table id="{tid}"><caption class="vh">{cap}</caption><thead><tr>{th}</tr></thead><tbody></tbody></table></div><ol class="t25-cards" id="{lid}"></ol>'
    hero = hero_html("KickTip Top 25", "The KickTip Top 25, compared with the AP and Coaches polls. A computer rating, not a poll.</p><p>KickTip ranks teams by a computer rating built from game results, with no voters, so it can differ from the polls.", "KickTip rating")
    body = (hero + f'<section class="sec t25"><div class="w">{banner(True)}<p class="t25-asof" data-t25asof></p>'
            '<div class="card t25-run"><h2>Run a scenario</h2><p>Pick a game result and see how chances change. Ratings and ranks here do not change.</p>'
            '<button type="button" class="t25-btn" data-t25run aria-haspopup="dialog">Run scenario</button>' + terms_copy.RUN_FULL_HTML + '</div>'
            '<div class="card"><h2>The KickTip Top 25</h2><p class="note" data-t25model></p>'
            f'<p class="note">Make the 12 comes from {SEASONS} simulated seasons.</p><p class="ccgdef">CCG = conference championship game</p>'
            '<p class="t25-def">KickTip vs AP: poll rank minus KickTip rank. A plus means KickTip ranks the team higher than the poll, a minus means lower, 0 means the same. NR means not ranked by that poll.</p>'
            + lst("t25", "t25l", "The KickTip Top 25 with AP and Coaches poll ranks") +
            '<p class="cta"><a href="/#conferences">See every team by conference</a></p></div>'
            '<section class="card" id="t25out" hidden><h2>Ranked in a poll, outside the KickTip 25</h2><p class="note">These teams are ranked by at least one poll but not in the KickTip 25.</p>'
            + lst("t25o", "t25ol", "Teams ranked in a poll but outside the KickTip 25") + '</section></div></section>')
    return page("KickTip Top 25 vs the AP and Coaches polls", "/top25/", body, active="", dyn=True, need="pred-teams,pred-top25", ptype="top25", ex=("BYU Cougars", "Utah Utes"),
                desc="KickTip's Top 25 ranked by the KickTip blend rating, compared with the recent AP and Coaches polls. Information only.",
                src_extra="Poll ranks (AP Top 25, Coaches Poll) via ESPN. Team, conference and league logos courtesy of ESPN.")

CCG_RULES = ccg_rules.load()
# F3: the one place for the simulator page label (the favorite wording in the app itself is FAV_COPY at the top of src/assets/ccgsim.js)
SIM_FAV_LABEL = "Starting results use ESPN's pre-game favorite, or the team with the better record (or the home team when records are level) where none is listed yet, for information only; change any game. Standings are based on {cname} rules as published by the conference; not a prediction."
def sim_page(ck, cname, cs):
    """/conference/<slug>/simulator/: official published tiebreaker rules only (never a KickTip rating or the blend); starting results are the ESPN pre-game favorites from /data/pred-lines.json, or the better-record team where none is listed (set in the browser from /data/ccg-sim.json)."""
    label = SIM_FAV_LABEL.format(cname=cname)
    body = (f'<section class="sec"><div class="w simw"><div class="card sim" id="sim" data-code="{ck}" data-name="{E(cname)}">'
            f'<h1 id="ttl">Conference championship game simulator</h1><p class="lab" id="lab">{E(label)}</p>{CCGDEF}'
            f'<div id="sim-app"><noscript><p class="xhow">Turn on JavaScript to use the simulator. It needs no sign-in and stores nothing.</p></noscript></div>'
            f'<p class="ns"><a href="/conference/{cs}/">Back to the {E(cname)} race</a></p></div></div></section>')
    return page(f"{cname} conference championship game simulator", f"/conference/{cs}/simulator/", body, active="Conferences", dyn=False, ptype="ccgsim",
                desc=f"Set the remaining {cname} games and see who would play in the conference championship game under the conference's published tiebreaker rules. Rules walkthrough only.",
                src_extra=f"Tiebreaker rules: {E(CCG_RULES[ck]['doc']['title'])} (link on the page). Starting results: ESPN's pre-game favorite where listed, otherwise the team with the better record (or the home team when records are level): overall record first, then conference record; no number is shown.")

def market_counts():
    """(unstarted FBS-vs-FBS games with a line that is not closed at build time, unstarted games): same list as /data/pred-games.json and /data/pred-lines.json, so the method page cannot drift from them."""
    shown = total = 0
    for x in GAMES:
        if game_state(x): continue
        total += 1
        if x["away"] == "FCS opponent": continue
        if x["id"] in MLINE: shown += 1
    return shown, total
def build_lines():
    """/data/pred-lines.json (fetched by assets/kt.js on arrival with the other /data/pred-*.json files): {gkey: [spread home side, read time (epoch s), kickoff (epoch s, 0 when the time is TBA)]}. Numbers only: no provider, link or book count.
    The page decides 'Line closed' in the visitor's browser (game started or the line is older than 24 h), so it stays right between data refreshes."""
    l = {}
    for x in GAMES:
        o = MLINE.get(x["id"])
        if not o or x["away"] not in TEAMS or x.get("status") in ("STATUS_POSTPONED", "STATUS_CANCELED"): continue
        tba = x["date_utc"][11:] in ("04:00Z", "05:00Z"); u = dt.datetime.strptime(x["date_utc"], "%Y-%m-%dT%H:%MZ").replace(tzinfo=dt.timezone.utc)
        l[gkey(x)] = [o["s"], int(o["t"]), 0 if tba else int(u.timestamp())]
    return dict(l=l)
def method_page():
    matched, n_pre = market_counts(); n_live = sum(1 for x in GAMES if game_state(x)); n_rem = n_pre + n_live   # every count below comes from the same game list as /data/pred-games.json
    if n_rem != META["remaining_games"]: print(f"WARNING: run_meta remaining_games={META['remaining_games']} but game list gives {n_rem}")
    sim_games = f"{n_rem} games ({n_pre} not yet started" + (f" plus {n_live} in progress or awaiting a final score" if n_live else "") + ")"
    c = lambda t: f'<li>{t}</li>'
    conf_links = "".join(f'<li><a href="/conference/{s}/">{E(n)}</a></li>' for _, n, s in CONFS)
    body = hero_html("Method", "How KickTip makes its numbers, where they come from, and what they cannot tell you.", "Plain English") + f'''<section class="sec"><div class="w prose">{banner(False, "method")}
<div class="card"><h2>Rules sources at a glance</h2><ul><li>American: official 2026 tiebreaker document (Sept. 30, 2026).</li><li>MAC: official tiebreaker text from Nov. 12, 2025. The MAC has published no 2026 revision.</li><li>Big Ten: official announcement of the tiebreaking procedures (Aug. 2024), the latest edition we found.</li><li>Mountain West: steps follow a published report of the conference's rules; we did not find the conference's own tiebreaker page.</li><li>Sun Belt and Conference USA: official conference documents; conference championship game times and TV are confirmed on the conference pages.</li></ul><p class="note">Each conference page links its sources.</p></div>
<h2>What KickTip does</h2><p>KickTip plays out the rest of the college football season thousands of times, applies each conference's tiebreaker rules and the 12-team playoff rules to every simulated season, and counts how often each team reaches its conference championship game, wins its conference and makes the 12. Everything is for information and entertainment only. Using KickTip means you accept the terms on the <a href="/disclaimer/">full terms and disclaimer</a> page.</p>
<h2>The simulation</h2><ul>{c("A game counts as remaining until ESPN shows it final. Games that have started are shown with their score when we have it, get no pre-game numbers, and are still simulated as unplayed until the next daily refresh.")}{c(f"We simulate the remaining {sim_games} {SEASONS} times. The same seed and the same data give the same answer.")}{c("Each game's win probability comes from the model you have selected (the KickTip blend unless you pick another; see The models below): the strength gap between the teams plus a home-field adjustment, converted to a probability with a conversion fitted only on games the model had not yet seen. Neutral-site games get no home-field adjustment.")}{c("After each simulated season we build the conference standings, break ties with the conference's own rules, pick the conference championship game teams, and then build the 12-team field.")}{c("Chances are the share of simulated seasons in which something happened. A 30% chance means it happened in about 3 of every 10 simulated seasons.")}</ul>
{method_copy.models_html(MR, META["games_rated"])}
{method_copy.accuracy_html(ACC)}
{method_copy.changed_html(MODEL_ASOF.strftime("%b %-d, %Y"), MOVERS)}
{ASK_METHOD}
<h2>Expected margin and spread</h2><ul><li><b>KickTip's expected margin.</b> Our own number: the strength difference between the teams, plus home field, converted to points and rounded to 0.5, and shown as the team KickTip favors and the points, for example “Utah by 3.5”. It comes from the same model that drives the simulation (the model you select; the KickTip blend by default).</li><li id="spread"><b>Spread (ESPN)</b> is the number of points ESPN lists the favorite as winning by, read as a snapshot before game day. A spread closes 24 hours after its read time or at kickoff, whichever comes first, so it is not live. Once the game has started or the number is more than 24 hours old, the game reads “Spread no longer current” and the old number is not used. Utah −3.0 means Utah is the favorite by 3.0. We show it for information only. KickTip is not a betting site. It comes from ESPN’s public scoreboard, numbers only, shown with the time it was read (MT). We do not link to where it came from, we show no prices, we never estimate a spread, and we show one only where ESPN has listed one. Right now that is {matched} of the {n_pre} games that have not started (the rest read “No spread listed yet”; spreads usually appear within about a day of kickoff). When ESPN has not listed one, the game reads “No spread listed yet”, and KickTip’s expected margin is a separate number from our own model. Both are information only.</li><li>Neither number is a recommendation, and KickTip is not a betting site.</li></ul>
<p class="note">Each spread names the favorite and the points ESPN lists it as winning by (in our data files a negative number means the home team is favored). We check KickTip's expected margins against ESPN's spreads. The model is fitted to games already played, so differences of a point or two are normal. Some games differ a lot, which means our rating and ESPN's favorite disagree about a team; treat those expected margins with extra caution.</p>
<h2>Tiebreakers</h2><p>Each conference has its own tiebreaker policy, which we encode step by step. Where a policy uses a proprietary or committee ranking, KickTip's rating stands in for it. Back-test: run on the 2024 and 2025 regular seasons, the engine picked the same two conference championship game teams the conference actually sent in 16 of 18 cases; both misses were decided at a stand-in step. Conference pages list each step and the official sources.</p>
<ul class="chips">{conf_links}</ul>
<h2>Where the data comes from</h2><ul>{c("Schedules, scores and conference membership: ESPN public data, cached and refreshed daily. If a source fails, the last good copy is used and the page shows when it was last updated.")}{c("Rules: official conference tiebreaker policies (linked on each conference page).")}{c("Market lines: ESPN, numbers only, shown when posted.")}{c("Team, conference and league logos courtesy of ESPN. They are shown unaltered next to the team, conference or league name, a logo is removed on request, and no logo is used in ads, share images or the KickTip mark.")}{c("The underlying data files are public.")}</ul>
<p><b>Game results last pulled:</b> {RESULTS_ASOF_S}. <b>Model numbers recalculated from them:</b> {MODEL_ASOF_S}. <b>Spreads last read:</b> {MKT_LATEST_S}. All times are Mountain Time.</p>
<h2 id="privacy">Privacy and saved teams</h2><p>{PRIVACY_LINE}</p><p>What KickTip keeps in your browser, and only when you choose to: the model you pick (if it is not the default), the bracket view you pick on the playoff page (Fit to screen or By round; Full bracket, the default, saves nothing), and, if you tap Save on My teams, your followed teams and your headline-number choices. Nothing is stored before you choose, tapping Run saves nothing, and there is no analytics. My teams has a Clear button that removes your saved teams and headline numbers. If you sign in, we also keep, on our server, the account id, email and name (if shared) that your sign-in gives us, plus your followed teams and headline-number choices, until you delete your account (My teams, Delete my account). Nothing else about you is stored except a short-lived counter, a keyed hash of your connection address and never the address itself, that limits sign-in attempts and saves. The <a href="/privacy/">privacy page</a> has the full detail. See the <a href="/disclaimer/">full terms and disclaimer</a>.</p>
<h2>Known limitations</h2><ul>{c("Steps that rely on other public rating systems, CFP rank or computer composites are approximated by KickTip's rating. Check each conference page for its flags.")}{c("The MAC has published no 2026 tiebreaker revision, so we use its Nov. 2025 official text; the Mountain West's steps follow a published report of its rules.")}{c("The simulation does not model injuries, suspensions, weather or postseason ineligibility.")}{c("Early in the season the KickTip blend leans on each team's final strength from last year, and that weight fades as games are played, so teams that changed a lot since last year are rated less accurately until they have played.")}{c("Every chance, win probability and line on KickTip is an estimate from a model, not a result.")}{c("Scores are not simulated, only wins and losses, so scoring-margin tiebreakers use the rating instead.")}{c("Playoff rule for 2026-27: the champions of the ACC, Big Ten, Big 12 and SEC, the highest-ranked team from the other six conferences (champion or not), Notre Dame if ranked in the top 12, and the next highest-ranked teams fill the 12. The model uses this one rule for every number on the site, and uses the rating rank as a stand-in for the selection committee.")}{c("A 'conference leader' stands in for the champion in the 'if the season ended today' bracket.")}{c("Games against FCS opponents are counted in the simulation but shown without a win probability or line.")}</ul>
</div></section>'''
    return page("Method", "/method/", body, active="Method", desc="How KickTip simulates the season, works out its expected margin, and where its data comes from.")

PRIVACY_LINE = privacy_copy.COOKIE_LONG   # LONG cookie line (Creative, sha 0dfdf2668896): /method/, /disclaimer/. The SHORT line (privacy_copy.COOKIE_SHORT) is in the sign-in sheet footer and the My teams line
def disclaimer_page():
    body = hero_html("Terms and disclaimer", f"Effective {TERMS_EFFECTIVE} (MT). By using KickTip, including tapping Run on any tool, you accept these terms. There is no pop-up and nothing to tick.", "Please read") + f'''<section class="sec"><div class="w prose">
<h2>Use is acceptance</h2><p>These are the full terms for KickTip. Using this site means you accept them. That includes viewing a page, using a tool, and tapping Run on any tool, where a short reminder and a link to this page sit directly under the button. Nothing here asks you to tick a box or press Accept, and no page is held back until you do.</p>
<h2>The six points</h2><ol><li>KickTip is not a betting site.</li><li>Everything on KickTip is information and entertainment only.</li><li>Nothing on KickTip is advice or a guarantee. Make no decision based on this material.</li><li>KickTip does not recommend using this material to place bets.</li><li>You use it at your own risk.</li><li>KickTip is not liable for any loss.</li></ol>
<h2>In more detail</h2>
<p><b>Not a betting site.</b> KickTip does not take or place bets, does not link to sportsbooks, and has no sportsbook affiliates, ads, bonuses or promo codes.</p>
<p><b>Information and entertainment only.</b> Chances, win probabilities and expected margins are produced by a statistical model or, where labeled, summarized from a public data service. They are estimates and can be wrong.</p>
<p><b>Expected margin and spread.</b> "KickTip's expected margin" is our own number from the model. "Spread (ESPN)" is the number of points ESPN lists the favorite as winning by, shown with the time it was read in MT. It is not our number, may be out of date, and is not an offer or a recommendation.</p>
<p><b>Not advice or a guarantee.</b> Words like "lock" or "in with wins" describe the model's output, not a certainty. Nothing here is financial, legal or gambling advice. Make no decision based on this material.</p>
<p><b>No recommendation to bet.</b> We do not recommend using any KickTip material to place a bet of any kind. If you choose to gamble anyway, you do so on your own judgment, and only where it is legal for you.</p>
<p><b>Your own risk; no liability.</b> You use KickTip at your own risk. To the extent the law allows, KickTip and its operators are not liable for any loss or damage that comes from using or relying on this site.</p>
<h2>What we store on your device</h2><p>{PRIVACY_LINE} KickTip uses no analytics, and unless you sign in nothing you do here is sent to us. Tapping Run saves nothing. Apart from your account if you sign in (below), the only things we save are choices you make: if you pick a model other than the default, which model you picked (one word, kept only on this device) so it is remembered next visit; on the playoff bracket, if you choose Fit to screen or By round, which view you picked (kept in your own browser on your own device and never sent to us; Full bracket, the default, saves nothing); and, if you tap Save on My teams, your followed teams and your headline-number choices, kept on this device. If you sign in, we also keep, on our server, the account id, email and name (if shared) that your sign-in gives us, plus your followed teams and headline-number choices, until you delete your account from the account menu. Nothing else is kept except a short-lived counter, a keyed hash of your connection address and never the address itself, that limits sign-in attempts and saves. Two small markers also stay in your browser after you sign in or tap Not now (the first letter of your name, and the time you tapped Not now). Clear this site's data in your browser, tap Clear on My teams, or choose 'Use the default model', to remove them. The data files behind the pages are public.</p>
<p>See also <a href="/privacy/">privacy</a> and <a href="/method/">how the numbers are made</a>.</p></div></section>'''
    return page("Terms and disclaimer", "/disclaimer/", body, desc="KickTip terms and disclaimer: not a betting site, information and entertainment only. Using the site means you accept them.")

def privacy_page():
    lead, inner = privacy_copy.privacy_body(site_config.PRIVACY_CONTACT_EMAIL, site_config.PHASE3_EMAIL_LINK, site_config.PRIVACY_UPDATED, site_config.EMAIL_LINK_TTL_SECONDS)
    body = hero_html("Privacy", E(lead)) + f'''<section class="sec"><div class="w prose">{inner}</div></section>'''
    return page("Privacy", "/privacy/", body, desc="KickTip privacy: what we collect if you sign in, why, and how to delete it. No ads, no analytics, no data sales.")

def p404():
    body = hero_html("Page not found", 'That page does not exist. Try the <a href="/">home page</a> or pick a conference below.') + f'<section class="sec"><div class="w"><nav class="tabs" aria-label="All 11 conferences">{pills("")}</nav></div></section>'
    return page("Page not found", "/404.html", body)

# ---------------------------------------------------------------- write
def w(path, text):
    p = f"{SITE}/{path}"; os.makedirs(os.path.dirname(p), exist_ok=True); open(p, "w", encoding="utf-8").write(text)
HASH_ORDER = ("assets/ks/sim.js", "assets/chat-worker.js", "assets/ks/parse.js", "assets/ks/scenario.js", "assets/ks/answer.js", "assets/chat.js", "assets/chat.css", "assets/lg.js", "assets/kt.css", "assets/kt.js")
def hash_assets():
    """Content-hash the static asset URLs at build time: every reference to a file in HASH_ORDER becomes /assets/<file>?v=<first 10 hex of the sha256 of that file's final bytes>.
    A file's own references to other hashed files are rewritten BEFORE its hash is taken (HASH_ORDER lists leaves first), so a change in sim.js also changes chat-worker.js's and chat.js's hash.
    Any code or asset change gives a new URL, so no Cloudflare cache purge is ever needed; the same bytes always give the same URL (cache stays warm). The files themselves are not renamed."""
    import hashlib
    tok = {}
    def sub(txt):
        for rel, h in tok.items(): txt = re.sub(r"(/" + re.escape(rel) + r")(?=[\"'])", lambda m: m.group(1) + "?v=" + h, txt)
        return txt
    for rel in HASH_ORDER:
        fp = f"{SITE}/{rel}"; b = open(fp, "rb").read().decode("utf-8"); b2 = sub(b)
        if b2 != b: open(fp, "w", encoding="utf-8").write(b2)
        tok[rel] = hashlib.sha256(b2.encode("utf-8")).hexdigest()[:10]
    for dp, _, fs in os.walk(SITE):
        for f in fs:
            if f.endswith(".html"):
                fp = os.path.join(dp, f); t = open(fp, encoding="utf-8").read(); t2 = sub(t)
                if t2 != t: open(fp, "w", encoding="utf-8").write(t2)
    json.dump(tok, open(f"{OUTD}/asset_hashes.json", "w"), indent=1); print("asset hashes:", tok)
def build():
    if os.path.exists(SITE): shutil.rmtree(SITE)
    os.makedirs(SITE)
    shutil.copytree(f"{ROOT}/src/assets", f"{SITE}/assets", ignore=shutil.ignore_patterns("fonts-src"))
    js = open(f"{SITE}/assets/kt.js").read().replace("__ALT_MODELS__", ",".join(MR.ALT_IDS)).replace("__MODEL_KEY__", MR.STORE_KEY); open(f"{SITE}/assets/kt.js", "w").write(js)
    for _n in ("chat.js", "rootables.js"):   # the ONE set of Run-control texts (src/terms_copy.py) is copied into the JS that draws Run controls
        _cj = open(f"{SITE}/assets/{_n}").read().replace("__RUN_FULL_HTML__", terms_copy.RUN_FULL_HTML).replace("__RUN_SHORT_HTML__", terms_copy.RUN_SHORT_HTML); open(f"{SITE}/assets/{_n}", "w").write(_cj)
    _mj = open(f"{SITE}/assets/myteams.js").read().replace("__SAVE_HTML__", terms_copy.SAVE_HTML).replace("__PRIVACY_SHORT__", privacy_copy.COOKIE_SHORT).replace("__CAP_LOCAL__", str(site_config.MYTEAMS_CAP_LOCAL)); open(f"{SITE}/assets/myteams.js", "w").write(_mj)   # my-teams: the one Save terms text + the local cap come from src/terms_copy.py and src/site_config.py
    _aj = open(f"{SITE}/assets/account.js").read().replace("__BANNER_INNER__", f"<b>{html.escape(terms_copy.BANNER_BOLD)}</b> {html.escape(terms_copy.BANNER_REST)}").replace("__SIGNIN_HTML__", terms_copy.SIGNIN_HTML).replace("__PRIVACY_LINE__", privacy_copy.COOKIE_SHORT); open(f"{SITE}/assets/account.js", "w").write(_aj)   # phase 2: sheet copy comes from src/terms_copy.py (banner, terms line) and the one privacy line
    _wk = open(f"{ROOT}/src/worker/worker.js").read(); assert _wk.count("__TEAM_SLUGS__") == 1; assert _wk.count("__EMAIL_LINK_TTL_SECONDS__") == 1
    open(f"{SITE}/_worker.js", "w").write(_wk.replace("__TEAM_SLUGS__", json.dumps(sorted(v["slug"] for v in TEAMS.values()))).replace("__EMAIL_LINK_TTL_SECONDS__", str(int(site_config.EMAIL_LINK_TTL_SECONDS))))   # Pages advanced mode: the accounts Worker. _routes.json sends only /api/* to it; every page and asset stays a static file
    open(f"{SITE}/_routes.json", "w").write(json.dumps({"version": 1, "include": ["/api/*"], "exclude": []}, indent=1) + "\n")
    os.makedirs(f"{SITE}/assets/ks")
    for _f in ("sim", "parse", "scenario", "answer"): shutil.copy(f"{ROOT}/src/web/{_f}.js", f"{SITE}/assets/ks/{_f}.js")   # browser engine; the Worker loads sim.js, the panel loads the rest
    _slug = {v["full"]: v["slug"] for v in TEAMS.values()}; _cs = {k: s_ for k, _, s_ in CONFS}
    for _mid, _src, _dst in (("blend", f"{ROOT}/data/out/web", "data"), ("elo", f"{ROOT}/data/out/web/m/elo", "data/m/elo"), ("eff", f"{ROOT}/data/out/web/m/eff", "data/m/eff")):
        _b = json.load(open(f"{_src}/bundle.json")); assert _b["model_id"] == _mid and _b["as_of"] == ST["as_of"], f"{_mid}: bundle model/as_of mismatch ({_b['model_id']}, {_b['as_of']} vs {ST['as_of']}): run python3 src/run_all.py"
        for _t in _b["teams"]:
            if _t["n"] in TEAMS: _t["s"] = SHORT[_t["n"]]; _t["g"] = SLUG[_t["n"]]; _t["cs"] = _cs.get(TEAMS[_t["n"]]["conf"], "")
        BUNDLES[_mid] = _b
        w(f"{_dst}/sim-bundle.json", json.dumps(_b, separators=(",", ":"), ensure_ascii=False))   # public model data, fetched on arrival
        _wd = f"{ROOT}/data/out/whatif" if _mid == "blend" else f"{ROOT}/data/out/whatif-models/{_mid}"
        _wi = json.load(open(f"{_wd}/index.json")); assert _wi["as_of"] == ST["as_of"], f"{_mid}: what-if shards as_of {_wi['as_of']} != {ST['as_of']}"
        shutil.copytree(_wd, f"{SITE}/{_dst}/whatif")
    open(f"{SITE}/assets/fonts/LICENSES.txt", "w").write("Barlow Condensed (Jeremy Tribby) and Source Sans 3 (Adobe) are licensed under the SIL Open Font License 1.1 (https://openfontlicense.org). Self-hosted, Latin subset.\n")
    cnt = logos.write_files(SITE); print("logos", cnt)
    _lg = open(f"{SITE}/assets/lg.js").read().replace("__LOGO_MAP__", M.js_map()); open(f"{SITE}/assets/lg.js", "w").write(_lg)
    shutil.copy(f"{ROOT}/src/favicon.ico", f"{SITE}/favicon.ico")   # byte-identical to icon/favicon.ico of the V2 package
    pt, pg, pp, field = build_pred()
    for n, d in (("pred-teams", pt), ("pred-games", pg), ("pred-paths", pp)): w(f"data/{n}.json", json.dumps(d, separators=(",", ":"), ensure_ascii=False))
    for mo in MR.MODELS[1:]:       # alternates: fetched by assets/kt.js only when the visitor picks that model
        a_t, a_g, a_p, a_f = build_pred(mo["id"]); assert a_f == field, "bracket order must be the same for every model (KickTip rating rank)"
        for n, d in (("pred-teams", a_t), ("pred-games", a_g), ("pred-paths", a_p)): w(f"data/m/{mo['id']}/{n}.json", json.dumps(d, separators=(",", ":"), ensure_ascii=False))
    for _mid, _dst, _pt in [(MR.DEFAULT_ID, "data", pt)] + [(mo["id"], f"data/m/{mo['id']}", None) for mo in MR.MODELS[1:]]:
        w(f"{_dst}/pred-top25.json", json.dumps(build_top25(_mid, _pt if _pt else build_pred(_mid)[0]), separators=(",", ":"), ensure_ascii=False))
    w("data/polls.json", json.dumps(build_polls(), separators=(",", ":"), ensure_ascii=False))
    w("data/pred-lines.json", json.dumps(build_lines(), separators=(",", ":"), ensure_ascii=False))   # market lines: model-independent, numbers only
    json.dump(MOVES_REPORT, open(f"{OUTD}/moves_report.json", "w"), indent=1); print("chips:", {k: (v["chips"], v["status"]) for k, v in MOVES_REPORT.items()})
    w("data/ccg-sim.json", json.dumps(ccgsim_data.build_data(), separators=(",", ":"), ensure_ascii=False))   # results only: no rating, no line
    _cr = ccg_rules.load(); _ce = ccg_rules.validate(_cr); assert not _ce, _ce
    w("data/ccg-rules.json", json.dumps(dict(codes=sorted(_cr), rules=_cr), separators=(",", ":"), ensure_ascii=False))
    urls = ["/"]
    w("index.html", home_page())
    for ck, n, s in CONFS:
        w(f"conference/{s}/index.html", conf_page(ck, n, s)); urls.append(f"/conference/{s}/")
        if ck in CCG_RULES: w(f"conference/{s}/simulator/index.html", sim_page(ck, n, s)); urls.append(f"/conference/{s}/simulator/")
    for full, v in sorted(TEAMS.items(), key=lambda kv: kv[1]["slug"]): w(f"team/{v['slug']}/index.html", team_page(full, v)); urls.append(f"/team/{v['slug']}/")
    for path, fn in (("playoff", playoff_page), ("top25", top25_page), ("games", games_page), ("method", method_page), ("disclaimer", disclaimer_page), ("privacy", privacy_page)): w(f"{path}/index.html", fn()); urls.append(f"/{path}/")
    w("404.html", p404())
    w("robots.txt", f"User-agent: *\nAllow: /\nDisallow: /data/\nDisallow: /api/\n\nSitemap: {BASE}/sitemap.xml\n")
    w("site.webmanifest", json.dumps(dict(name="KickTip Media", short_name="KickTip", start_url="/", display="browser", background_color="#121519", theme_color="#262B31",
        icons=[dict(src="/assets/brand/icon/kicktip-icon-192.png", sizes="192x192", type="image/png"), dict(src="/assets/brand/icon/kicktip-icon-512.png", sizes="512x512", type="image/png")]), indent=1) + "\n")
    w("sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "".join(f"<url><loc>{BASE}{u}</loc></url>\n" for u in urls) + "</urlset>\n")
    w("_headers", "/*\n  Content-Security-Policy: default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; font-src 'self'; connect-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'; worker-src 'self'\n  X-Content-Type-Options: nosniff\n  Referrer-Policy: no-referrer\n  Permissions-Policy: camera=(), microphone=(), geolocation=()\n/assets/*\n  Cache-Control: public, max-age=86400\n/data/*\n  X-Robots-Tag: noindex, nofollow\n  Cache-Control: public, max-age=300\n")
    hash_assets()
    if os.environ.get("KT_HDR", "p") != "off":   # sticky slim header (src/header-kit/): post-processes the finished site tree; KT_HDR=q builds option Q, KT_HDR=off skips it
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "header-kit")); import apply_header; apply_header.apply(SITE)
    n = sum(len(fs) for _, _, fs in os.walk(SITE)); print("built", SITE, n, "files;", len(urls), "pages in sitemap")

if __name__ == "__main__": build()
