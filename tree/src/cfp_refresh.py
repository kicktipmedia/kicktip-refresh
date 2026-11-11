"""CFP selection-committee Top 25, folded into data/polls.json next to AP and Coaches.

The official rankings page is read first. ESPN's public rankings feed (type "cfp")
is the fallback when that page cannot be read or is older than the feed. A release
older than the one already stored is refused. A timeout, HTTP error, short table
or unmapped team keeps the last good copy. When both sources answer and neither
has a committee poll, the step is a no-op (before the first release of a season).

The saved tree/data/cfp.json copy is used only when a fetch fails and that copy
is still within SEED_MAX_AGE_DAYS and newer than the live file. This module does
not raise.
"""
import datetime as dt, json, os, re, socket, urllib.error, urllib.request
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONF = os.path.join(ROOT, "data", "ref", "conf_2026.json")
SEED_PATH = os.path.join(ROOT, "data", "cfp.json")
HUB = "https://collegefootballplayoff.com/rankings"
ESPN = "https://site.api.espn.com/apis/site/v2/sports/football/college-football/rankings"
MT = ZoneInfo("America/Denver")
UA = {"User-Agent": "Mozilla/5.0 (KickTip data refresh; contact via kicktipmedia.com)"}
SEED_MAX_AGE_DAYS = 120
LINK = re.compile(r"/news/(\d{4})/(\d{2})/(\d{2})/rankings\b")
REC = re.compile(r"\d+-\d+(-\d+)?")
DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
SLUG = re.compile(r"[a-z0-9-]+")


def slugify(s):
    import unicodedata
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower().replace("'", "")
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def load_names(path=None):
    """Exact committee name (conf loc) -> KickTip slug. A repeated name is dropped, not guessed."""
    conf = json.load(open(path or CONF, encoding="utf-8"))
    names, dups = {}, set()
    for v in conf.values():
        loc = v.get("loc")
        if not isinstance(loc, str) or not loc.strip():
            continue
        slug = slugify(loc)
        if loc in names and names[loc] != slug:
            dups.add(loc)
        names[loc] = slug
    for loc in dups:
        names.pop(loc, None)
    return names


def denver_today(now=None):
    if now is None:
        now = dt.datetime.now(dt.timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=dt.timezone.utc)
    return now.astimezone(MT).date()


def asof_for(iso):
    y, m, d = (int(x) for x in iso.split("-"))
    return dt.date(y, m, d).strftime("%b %-d")


def parse_pub(s):
    if not isinstance(s, str) or not s.strip():
        return None
    t = s.strip().replace("Z", "+00:00")
    try:
        d = dt.datetime.fromisoformat(t)
    except ValueError:
        return None
    if d.tzinfo is None:
        return None
    return d.astimezone(dt.timezone.utc).replace(microsecond=0)


def _cells(tr):
    out = []
    for raw in re.findall(r"<td\b[^>]*>(.*?)</td>", tr, re.I | re.S):
        text = re.sub(r"<[^>]+>", " ", raw)
        text = re.sub(r"\s+", " ", text).replace("\xa0", " ").strip()
        out.append(text)
    return out


def latest_rankings_url(html, origin=HUB):
    """Newest /news/YYYY/MM/DD/rankings link on the hub, or None."""
    best = None
    for y, m, d in LINK.findall(html or ""):
        iso = "%s-%s-%s" % (y, m, d)
        try:
            dt.date(int(y), int(m), int(d))
        except ValueError:
            continue
        if best is None or iso > best[0]:
            best = (iso, "https://collegefootballplayoff.com/news/%s/%s/%s/rankings" % (y, m, d))
    return None if best is None else best[1]


def parse_official_html(html, page_url, names):
    """(poll, None) or (None, reason). Rank, team and record come from the printed table."""
    m = LINK.search(page_url or "")
    if not m:
        return None, "no release date on the rankings url"
    iso = "%s-%s-%s" % (m.group(1), m.group(2), m.group(3))
    try:
        dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None, "release date is not a calendar day"
    table = re.search(r'<table\b[^>]*class="[^"]*\bcfp-table\b[^"]*"[^>]*>(.*?)</table>', html or "", re.I | re.S)
    if not table:
        table = re.search(r'<table\b[^>]*\bid="athletic"[^>]*>(.*?)</table>', html or "", re.I | re.S)
    if not table:
        return None, "no rankings table"
    rows = []
    for tr in re.findall(r"<tr\b[^>]*>(.*?)</tr>", table.group(1), re.I | re.S):
        cells = _cells(tr)
        if len(cells) < 5 or not cells[0].isdigit():
            continue
        rows.append(cells)
    return _rows_to_poll(rows, names, iso, page_url, "cfp")


def _rows_to_poll(rows, names, iso, source, origin):
    if len(rows) != 25:
        return None, "partial list (%d ranked, need 25)" % len(rows)
    parsed, places, slugs = [], set(), set()
    for cells in rows:
        try:
            rank = int(cells[0])
        except (TypeError, ValueError):
            return None, "malformed entry"
        team, rec = cells[3], cells[4]
        if not isinstance(team, str) or not team.strip():
            return None, "malformed entry"
        team = re.sub(r"\s+", " ", team).strip()
        if not REC.fullmatch(rec or ""):
            return None, "malformed entry"
        if rank in places:
            return None, "malformed entry"
        slug = names.get(team) if names is not None else None
        if names is not None and not slug:
            return None, "unmapped team name %s" % team
        if slug in slugs:
            return None, "malformed entry"
        places.add(rank)
        if slug:
            slugs.add(slug)
        parsed.append((rank, slug, rec, team))
    if places != set(range(1, 26)):
        return None, "partial list (places are not 1 through 25)"
    parsed.sort()
    poll = {
        "name": "CFP",
        "released": True,
        "date": iso,
        "asof": asof_for(iso),
        "origin": origin,
        "source": source,
        "ranks": [[rank, slug, rec] for rank, slug, rec, _team in parsed],
    }
    return poll, None


def parse_espn_ranking(ranking, ids):
    """One ESPN type=cfp block, or (None, reason). Release day is the Denver calendar day."""
    if not isinstance(ranking, dict):
        return None, "malformed feed"
    ranks = ranking.get("ranks")
    if not isinstance(ranks, list) or len(ranks) != 25:
        return None, "partial list (%d ranked, need 25)" % (len(ranks) if isinstance(ranks, list) else 0)
    pub = parse_pub(ranking.get("lastUpdated") or "") or parse_pub(ranking.get("date") or "")
    if pub is None:
        return None, "malformed entry (no publication time)"
    iso = pub.astimezone(MT).date().isoformat()
    rows, places, slugs = [], set(), set()
    for x in ranks:
        if not isinstance(x, dict):
            return None, "malformed entry"
        cur = x.get("current")
        if type(cur) is not int or not (1 <= cur <= 25):
            return None, "malformed entry"
        team = x.get("team") if isinstance(x.get("team"), dict) else None
        if not team or team.get("id") is None:
            return None, "malformed entry"
        rec = x.get("recordSummary")
        if not isinstance(rec, str) or not REC.fullmatch(rec):
            return None, "malformed entry"
        slug = (ids or {}).get(str(team["id"]))
        if not slug:
            who = team.get("location") or team.get("name") or ""
            return None, "unmapped ESPN team id %s%s" % (team.get("id"), (" (%s)" % who) if who else "")
        if cur in places or slug in slugs:
            return None, "malformed entry"
        places.add(cur)
        slugs.add(slug)
        rows.append((cur, slug, rec))
    if places != set(range(1, 26)):
        return None, "partial list (places are not 1 through 25)"
    rows.sort()
    return {
        "name": "CFP",
        "released": True,
        "date": iso,
        "asof": asof_for(iso),
        "pub": pub.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
        "origin": "espn",
        "source": ESPN,
        "ranks": [[c, s, rec] for c, s, rec in rows],
    }, None


def cfp_from_feed(feed, ids):
    if not isinstance(feed, dict) or not isinstance(feed.get("rankings"), list):
        return None, "malformed feed"
    found = False
    for r in feed["rankings"]:
        if isinstance(r, dict) and r.get("type") == "cfp":
            found = True
            if r.get("ranks"):
                return parse_espn_ranking(r, ids)
    if not found:
        return None, "empty"
    return None, "empty"


def valid_cfp(p):
    if not isinstance(p, dict) or p.get("released") is not True:
        return False
    if not isinstance(p.get("date"), str) or not DATE.fullmatch(p["date"]):
        return False
    try:
        dt.date.fromisoformat(p["date"])
    except ValueError:
        return False
    if not isinstance(p.get("asof"), str) or not p["asof"].strip():
        return False
    ranks = p.get("ranks")
    if not isinstance(ranks, list) or len(ranks) != 25:
        return False
    places, slugs = set(), set()
    for row in ranks:
        if not isinstance(row, list) or len(row) != 3:
            return False
        place, slug, rec = row
        if type(place) is not int or not (1 <= place <= 25):
            return False
        if not isinstance(slug, str) or not SLUG.fullmatch(slug):
            return False
        if not isinstance(rec, str) or not REC.fullmatch(rec):
            return False
        if place in places or slug in slugs:
            return False
        places.add(place)
        slugs.add(slug)
    return places == set(range(1, 26))


def cfp_date(p):
    if not isinstance(p, dict):
        return None
    d = p.get("date")
    if isinstance(d, str) and DATE.fullmatch(d):
        try:
            return dt.date.fromisoformat(d)
        except ValueError:
            return None
    return None


def newer(new, old):
    """True when new is a later release day, or the same day read from the official page over an ESPN copy with different ranks."""
    if not valid_cfp(new):
        return False
    if not isinstance(old, dict) or old.get("released") is not True or cfp_date(old) is None:
        return True
    nd, od = cfp_date(new), cfp_date(old)
    if nd > od:
        return True
    if nd < od:
        return False
    if new.get("origin") == "cfp" and old.get("origin") != "cfp" and new.get("ranks") != old.get("ranks"):
        return True
    return False


def older_reason(new, old):
    nd, od = cfp_date(new), cfp_date(old)
    if od is not None and nd is not None and nd < od:
        return "%s is older than live %s" % (nd.isoformat(), od.isoformat())
    if od is not None and nd == od:
        return "%s is not newer than live %s" % (nd.isoformat(), od.isoformat())
    return "not newer than the live rankings"


def brief(p):
    if not isinstance(p, dict) or not p.get("released"):
        return "none"
    return str(p.get("date") or "none")


def load_seed(path, names, today):
    try:
        raw = json.load(open(path, encoding="utf-8"))
    except Exception as e:
        return None, "saved release unreadable (%s)" % e
    if not isinstance(raw, dict):
        return None, "saved release is not an object"
    iso = raw.get("date")
    source = raw.get("source") or ""
    m = LINK.search(source)
    if not isinstance(iso, str) or not m or "%s-%s-%s" % m.groups() != iso:
        return None, "saved release date does not match its source url"
    try:
        released = dt.date.fromisoformat(iso)
    except ValueError:
        return None, "saved release date is not a calendar day"
    age = (today - released).days
    if age < 0 or age > SEED_MAX_AGE_DAYS:
        return None, "saved release %s is outside the %d-day window" % (iso, SEED_MAX_AGE_DAYS)
    rows = []
    for item in raw.get("ranks") or []:
        if not isinstance(item, list) or len(item) != 3:
            return None, "saved release is malformed"
        rows.append([str(item[0]), "", "", str(item[1]), str(item[2])])
    poll, reason = _rows_to_poll(rows, names, iso, source, "cfp")
    if poll is None:
        return None, reason
    if raw.get("asof"):
        poll["asof"] = raw["asof"]
    return poll, None


def classify(exc):
    if isinstance(exc, (TimeoutError, socket.timeout)):
        return "timeout"
    if isinstance(exc, urllib.error.HTTPError):
        return "HTTP %s" % exc.code
    if isinstance(exc, urllib.error.URLError):
        if isinstance(exc.reason, (TimeoutError, socket.timeout)):
            return "timeout"
        return "unreachable"
    return exc.__class__.__name__


def fetch_text(url, timeout=8):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = r.read(2_000_001)
    if len(data) > 2_000_000:
        raise ValueError("response too large")
    return data.decode("utf-8", "replace")


def fetch_json(url, timeout=8):
    return json.loads(fetch_text(url, timeout=timeout))


def select(old, official, official_err, espn_poll, espn_err, seed, seed_err):
    """The release to store. Returns (poll or None, logs, kind).

    The official page wins a same-day tie. ESPN is used when its release day is later.
    The saved copy is used only when both reads fail.
    """
    logs = []
    best = None
    if official is not None:
        logs.append("polls: CFP official page %s" % official.get("date"))
        best = official
    elif official_err and official_err != "empty":
        logs.append("WARNING polls: CFP official page failed (%s)" % official_err)
    else:
        logs.append("polls: CFP official page has no rankings")
    if espn_poll is not None:
        ed, bd = cfp_date(espn_poll), cfp_date(best) if best else None
        if best is None or (ed and bd and ed > bd):
            logs.append("polls: CFP ESPN feed %s" % espn_poll.get("date"))
            best = espn_poll
        elif ed and bd and ed <= bd:
            logs.append("polls: CFP ESPN feed %s is not newer than the official page" % espn_poll.get("date"))
    elif espn_err and espn_err != "empty":
        logs.append("WARNING polls: CFP ESPN feed failed (%s)" % espn_err)
    else:
        logs.append("polls: CFP ESPN feed has no committee poll")
    if best is not None and newer(best, old):
        kind = "official" if best.get("origin") == "cfp" else "espn"
        return best, logs, kind
    if best is not None:
        logs.append("polls: CFP unchanged (%s)" % older_reason(best, old))
        return None, logs, "keep"
    if official_err == "empty" and espn_err == "empty":
        logs.append("polls: CFP not released; no-op")
        return None, logs, "empty"
    both_failed = official_err not in (None, "empty") and espn_err not in (None, "empty")
    if both_failed and seed is not None and newer(seed, old):
        logs.append("polls: CFP using the saved release %s because the fetch failed" % seed.get("date"))
        return seed, logs, "seed"
    if both_failed:
        if seed_err:
            logs.append("WARNING polls: CFP saved release not used (%s)" % seed_err)
        logs.append("WARNING polls: CFP keeping the last good rankings")
        return None, logs, "keep"
    logs.append("polls: CFP not released; no-op")
    return None, logs, "empty"


def apply(live, names, ids, official=None, official_err=None, espn_poll=None, espn_err=None,
          seed=None, seed_err=None):
    """Merge one CFP result onto a page object. Never raises. Does not drop AP or Coaches."""
    try:
        if not isinstance(live, dict):
            live = {"polls": {}}
        polls = live.get("polls") if isinstance(live.get("polls"), dict) else {}
        old = polls.get("cfp")
        chosen, logs, kind = select(old, official, official_err, espn_poll, espn_err, seed, seed_err)
        if chosen is None:
            return live, False, logs
        out = json.loads(json.dumps(live))
        out.setdefault("polls", {})
        if not isinstance(out["polls"], dict):
            out["polls"] = {}
        out["polls"]["cfp"] = chosen
        logs.append("polls: CFP updated %s -> %s (%s)" % (brief(old), chosen.get("date"), kind))
        return out, out != live, logs
    except Exception as e:
        return live if isinstance(live, dict) else {"polls": {}}, False, [
            "WARNING polls: CFP step failed (%s); keeping the last good rankings" % e]


def preserve(live_polls, out):
    """Copy a stored CFP poll onto a rebuilt AP/Coaches object so a poll refresh cannot drop it."""
    if isinstance(live_polls, dict) and "cfp" in live_polls and "cfp" not in out:
        out["cfp"] = live_polls["cfp"]


def merge_key(live_polls, cand_polls):
    """(value or None, logs). None means leave the key off."""
    old = live_polls.get("cfp") if isinstance(live_polls, dict) else None
    if not isinstance(cand_polls, dict) or "cfp" not in cand_polls:
        return old, []
    new = cand_polls.get("cfp")
    if not valid_cfp(new):
        return old, ["WARNING polls: CFP candidate rejected; keeping the last good rankings"]
    if not newer(new, old):
        if isinstance(old, dict) and old.get("ranks") == new.get("ranks") and old.get("date") == new.get("date"):
            return old, ["polls: CFP unchanged (%s)" % new.get("date")]
        return old, ["polls: CFP candidate is not newer (%s); keeping the live rankings" % older_reason(new, old)]
    return new, ["polls: CFP candidate accepted, %s -> %s" % (brief(old), new.get("date"))]


def read_sources(names, ids, today, html=None, html_url=None, feed=None, fail="", timeout=8, network=True, seed_path=SEED_PATH):
    """Official page, then ESPN. Returns the kwargs apply() expects, besides live/names/ids.

    html/feed skip that source's network read. fail=timeout|http skips both reads.
    The saved release is loaded only when both reads fail.
    """
    official, official_err = None, None
    espn_poll, espn_err = None, None
    if fail in ("timeout", "http"):
        official_err = espn_err = "timeout" if fail == "timeout" else "HTTP 503"
    elif fail:
        official_err = espn_err = "unknown fail hook"
    else:
        if html is not None:
            official, official_err = parse_official_html(html, html_url or "", names)
            if official is None and not official_err:
                official_err = "malformed page"
        elif network:
            official, official_err = _fetch_official(names, timeout)
        else:
            official_err = "empty"
        if feed is not None:
            espn_poll, espn_err = cfp_from_feed(feed, ids)
        elif network:
            try:
                espn_poll, espn_err = cfp_from_feed(fetch_json(ESPN, timeout=timeout), ids)
            except Exception as e:
                espn_err = classify(e)
        else:
            espn_err = "empty"
    seed, seed_err = None, None
    both_failed = official is None and espn_poll is None and official_err not in (None, "empty") and espn_err not in (None, "empty")
    if both_failed and seed_path:
        seed, seed_err = load_seed(seed_path, names, today)
    return dict(official=official, official_err=None if official is not None else official_err,
                espn_poll=espn_poll, espn_err=None if espn_poll is not None else espn_err,
                seed=seed, seed_err=seed_err)


def _fetch_official(names, timeout):
    try:
        hub = fetch_text(HUB, timeout=timeout)
    except Exception as e:
        return None, classify(e)
    url = latest_rankings_url(hub)
    if not url:
        return None, "empty"
    try:
        page = fetch_text(url, timeout=timeout)
    except Exception as e:
        return None, classify(e)
    poll, reason = parse_official_html(page, url, names)
    if poll is None:
        return None, reason or "malformed page"
    return poll, None


# --- home #top25 display patch (the live script and stylesheet, not the pipeline /top25/ copies) ---

HOME_JS = "KickTip home Top 25 block"
_JS_LABEL = (
    "  function label(nm, kt, rec, ps, slug, p) {\n"
    "    return nm + ', KickTip rank ' + kt + '. Record ' + rec + '. ' + say(ps.ap, 'ap', slug) + ', ' + say(ps.coaches, 'coaches', slug) + '. Chance to make the 12-team playoff field ' + pctSay(p) + '.';\n"
    "  }"
)
_JS_LABEL_NEW = (
    "  function cfpBit(ps, slug) {\n"
    "    var s = ps.cfp; if (!s || !s.on) return '';\n"
    "    return ' \\u00b7 CFP ' + (s.rank[slug] === undefined ? '\\u2014' : String(s.rank[slug]));\n"
    "  }\n"
    "  function cfpSay(ps, slug) {\n"
    "    var s = ps.cfp; if (!s || !s.on) return '';\n"
    "    return s.rank[slug] === undefined ? ', outside the CFP 25' : ', CFP ' + s.rank[slug];\n"
    "  }\n"
    "  function label(nm, kt, rec, ps, slug, p) {\n"
    "    return nm + ', KickTip rank ' + kt + '. Record ' + rec + '. ' + say(ps.ap, 'ap', slug) + ', ' + say(ps.coaches, 'coaches', slug) + cfpSay(ps, slug) + '. Chance to make the 12-team playoff field ' + pctSay(p) + '.';\n"
    "  }"
)
_JS_REPS = (
    (_JS_LABEL, _JS_LABEL_NEW, 1),
    (" + pv(ps.coaches, slug) + '</span>", " + pv(ps.coaches, slug) + cfpBit(ps, slug) + '</span>", 1),
    (
        "    el.innerHTML = '<span>' + one('ap') + ' ' + one('coaches') + '</span>';",
        "    var cfp = ps.cfp && ps.cfp.on && ps.cfp.asof ? ' CFP, ' + esc(mt(ps.cfp.asof)) + '.' : '';\n"
        "    el.innerHTML = '<span>' + one('ap') + ' ' + one('coaches') + cfp + '</span>';",
        1,
    ),
    (
        "var ps = { ap: pollState(P, 'ap'), coaches: pollState(P, 'coaches') };",
        "var ps = { ap: pollState(P, 'ap'), coaches: pollState(P, 'coaches'), cfp: pollState(P, 'cfp') };",
        1,
    ),
    ("['ap', 'coaches']", "['ap', 'coaches', 'cfp']", 2),
)
_CSS_OLD = ".t25h .h25-sb{display:block;margin-top:2px;font:400 13px/1.3 'Source Sans 3','KT Source Fallback',Arial,sans-serif;color:var(--s);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}"
_CSS_NEW = ".t25h .h25-sb{display:block;margin-top:2px;font:400 13px/1.3 'Source Sans 3','KT Source Fallback',Arial,sans-serif;color:var(--s);white-space:normal;overflow:visible}"


def patch_home_js(text):
    """(new text, None) or (original, reason). A pipeline /top25/ script is left untouched."""
    if HOME_JS not in text:
        return text, "not the home Top 25 script"
    if "function cfpBit(" in text:
        return text, None
    for old, _new, n in _JS_REPS:
        if text.count(old) != n:
            return text, "home Top 25 script is missing a CFP marker"
    out = text
    for old, new, n in _JS_REPS:
        out = out.replace(old, new, n)
    return out, None


def patch_home_css(text):
    if ".t25h .h25-sb{" not in text:
        return text, "not the home Top 25 stylesheet"
    if _CSS_NEW in text:
        return text, None
    if text.count(_CSS_OLD) != 1:
        return text, "home Top 25 subtitle rule was not found"
    return text.replace(_CSS_OLD, _CSS_NEW, 1), None


def patch_text(rel, text):
    if rel == "assets/top25.js":
        return patch_home_js(text)[0]
    if rel == "assets/top25.css":
        return patch_home_css(text)[0]
    return text


def patch_site(site):
    """Patch the shipped home Top 25 script and stylesheet in place. Never raises."""
    notes = []
    try:
        for rel, fn in (("assets/top25.js", patch_home_js), ("assets/top25.css", patch_home_css)):
            path = os.path.join(site, rel)
            if not os.path.isfile(path):
                notes.append("polls: CFP display skipped, %s missing" % rel)
                continue
            text = open(path, encoding="utf-8").read()
            new, err = fn(text)
            if err:
                notes.append("polls: CFP display skipped, %s (%s)" % (rel, err))
                continue
            if new != text:
                tmp = path + ".tmp"
                with open(tmp, "w", encoding="utf-8") as f:
                    f.write(new)
                os.replace(tmp, path)
                notes.append("polls: CFP display updated %s" % rel)
    except Exception as e:
        notes.append("WARNING polls: CFP display patch failed (%s); rankings text is unchanged" % e)
    for line in notes:
        print(line)
    return notes
