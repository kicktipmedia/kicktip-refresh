"""Scheduled AP Top 25, Coaches Poll, and CFP committee rankings refresh.

Reads ESPN's free public rankings feed and writes data/polls.json in the shape the
site already ships: name, released, week, asof, pub, ranks [place, slug, record].
Slugs come from the ESPN team id, the same conf_2026.json map build.py and polls.py use.

Fail-open, per poll. A timeout, HTTP error, partial list (not exactly 25), malformed
entry, or unmapped team keeps the last good copy of THAT poll and prints a WARNING.
The other poll can still update. An older week, or the same week with an older or
equal publication time, is refused. This module never raises to its caller and its
CLI always exits 0: a poll problem must not block a scores publish.

asof is the publication calendar day in America/Denver ("Nov 8"), the shape of the
hand-written live file. The home page adds " MT" only when the stamp contains a
time, so a date-only stamp renders as "AP poll as of Nov 8."

The dry-run hook KT_POLLS_BASELINE=week10 (or --baseline week10) compares against a
copy of the live file rewound to week 10. It is off unless a manual non-production
dispatch sets it. KT_POLLS_FAIL=timeout|http and --fail do the same for a forced
read error. Neither is set by the scheduled workflow.
"""
import argparse, copy, datetime as dt, json, os, re, socket, sys, unicodedata, urllib.error, urllib.request, zipfile
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONF = os.path.join(ROOT, "data", "ref", "conf_2026.json")
DEFAULT_URL = "https://site.api.espn.com/apis/site/v2/sports/football/college-football/rankings"
MT = ZoneInfo("America/Denver")
UA = {"User-Agent": "Mozilla/5.0 (KickTip data refresh; contact via kicktipmedia.com)"}
SPECS = (("ap", "AP Top 25", "ap"), ("coaches", "Coaches Poll", "usa"))
REC = re.compile(r"\d+-\d+(-\d+)?")
SLUG = re.compile(r"[a-z0-9-]+")


class PollFetchError(Exception):
    """A forced read failure (--fail / KT_POLLS_FAIL). kind is the log phrase."""


def slugify(s):
    """Same rule as build.py: KickTip slug is slugify(conf loc)."""
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower().replace("'", "")
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def load_ids(path=None):
    conf = json.load(open(path or CONF, encoding="utf-8"))
    ids = {str(v["id"]): slugify(v["loc"]) for v in conf.values()}
    if len(ids) != len(set(ids.values())):
        raise RuntimeError("conf slug collision")
    return ids


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


def fmt_pub(d):
    d = d.astimezone(dt.timezone.utc).replace(microsecond=0)
    return d.strftime("%Y-%m-%dT%H:%M:%SZ" if d.second else "%Y-%m-%dT%H:%MZ")


def asof_label(d):
    return d.astimezone(MT).strftime("%b %-d")


def week_of(p):
    if not isinstance(p, dict):
        return None
    w = p.get("week")
    if isinstance(w, bool):
        return None
    if isinstance(w, int):
        return w
    if isinstance(w, str) and w.isdigit():
        return int(w)
    return None


def brief(p):
    if not isinstance(p, dict) or not p.get("released"):
        return "none"
    return "week %s pub %s" % (p.get("week"), p.get("pub"))


def classify(exc):
    if isinstance(exc, PollFetchError):
        return str(exc)
    if isinstance(exc, (TimeoutError, socket.timeout)):
        return "timeout"
    if isinstance(exc, urllib.error.HTTPError):
        return "HTTP %s" % exc.code
    if isinstance(exc, urllib.error.URLError):
        if isinstance(exc.reason, (TimeoutError, socket.timeout)):
            return "timeout"
        return "unreachable"
    if isinstance(exc, json.JSONDecodeError):
        return "malformed feed"
    return exc.__class__.__name__


def fetch_rankings(url, timeout=15, tries=2):
    """Return (feed, None) or (None, exc). No sleep: a dead host must not stall the publish."""
    last = None
    for _ in range(max(1, tries)):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.load(r), None
        except Exception as e:
            last = e
    return None, last


def poll_from_ranking(ranking, ids, label):
    """One page-shaped poll, or (None, reason). Any bad entry rejects the whole poll."""
    ranks = ranking.get("ranks") if isinstance(ranking, dict) else None
    n = len(ranks) if isinstance(ranks, list) else 0
    if not isinstance(ranks, list) or n != 25:
        return None, "partial list (%d ranked, need 25)" % n
    pub = parse_pub(ranking.get("lastUpdated") or "") or parse_pub(ranking.get("date") or "")
    if pub is None:
        return None, "malformed entry (no publication time)"
    occ = ranking.get("occurrence") if isinstance(ranking.get("occurrence"), dict) else {}
    wk = week_of({"week": occ.get("value")})
    if wk is None:
        wk = occ.get("number") if isinstance(occ.get("number"), int) and not isinstance(occ.get("number"), bool) else None
    if not isinstance(wk, int) or wk < 1:
        return None, "malformed entry (no week)"
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
        tid = str(team["id"])
        rec = x.get("recordSummary")
        if not isinstance(rec, str) or not REC.fullmatch(rec):
            return None, "malformed entry"
        slug = ids.get(tid)
        if not slug:
            who = team.get("location") or team.get("name") or ""
            return None, "unmapped ESPN team id %s%s" % (tid, (" (%s)" % who) if who else "")
        if cur in places or slug in slugs:
            return None, "malformed entry"
        places.add(cur)
        slugs.add(slug)
        rows.append((cur, slug, rec))
    if places != set(range(1, 26)):
        return None, "partial list (places are not 1 through 25)"
    rows.sort()
    return {"name": label, "released": True, "week": str(wk), "asof": asof_label(pub), "pub": fmt_pub(pub),
            "ranks": [[c, s, rec] for c, s, rec in rows]}, None


def newer(new, old):
    """True only when new is a later week, or the same week with a later publication time."""
    if not isinstance(old, dict) or old.get("released") is not True:
        return True
    ow, nw = week_of(old), week_of(new)
    if nw is None:
        return False
    if ow is None:
        return True
    if nw > ow:
        return True
    if nw < ow:
        return False
    op, npub = parse_pub(str(old.get("pub") or "")), parse_pub(str(new.get("pub") or ""))
    if op is None or npub is None:
        return False
    return npub > op


def older_reason(new, old):
    if not isinstance(old, dict) or old.get("released") is not True:
        return "no released poll on file"
    ow, nw = week_of(old), week_of(new)
    if nw is None:
        return "no week on the new poll"
    if ow is not None and nw < ow:
        return "week %s is older than live week %s" % (nw, ow)
    if ow is not None and nw == ow:
        return "week %s pub %s is not newer than live %s" % (nw, new.get("pub"), old.get("pub"))
    return "not newer than the live poll"


def _keep(old, label):
    return old if isinstance(old, dict) else {"name": label, "released": False}


def apply_feed(live, ids, feed):
    """Merge a parsed ESPN feed onto live, one poll at a time. Returns (obj, changed, logs)."""
    logs, by = [], {}
    for r in feed.get("rankings") or []:
        if isinstance(r, dict) and r.get("type") and r["type"] not in by:
            by[r["type"]] = r
    live_polls = live.get("polls") if isinstance(live, dict) else None
    if not isinstance(live_polls, dict):
        live_polls = {}
    out = {}
    for key, label, et in SPECS:
        old = live_polls.get(key)
        ranking = by.get(et)
        if ranking is None:
            logs.append("WARNING polls: %s missing from the ESPN feed; keeping the last good poll" % label)
            out[key] = _keep(old, label)
            continue
        new, reason = poll_from_ranking(ranking, ids, label)
        if new is None:
            logs.append("WARNING polls: %s rejected (%s); keeping the last good poll" % (label, reason))
            out[key] = _keep(old, label)
            continue
        if not newer(new, old):
            logs.append("polls: %s unchanged (%s)" % (label, older_reason(new, old)))
            out[key] = _keep(old, label)
            continue
        logs.append("polls: %s updated %s -> week %s pub %s" % (label, brief(old), new["week"], new["pub"]))
        out[key] = new
    import cfp_refresh
    cfp_refresh.preserve(live_polls, out)
    merged = {"polls": out}
    return merged, merged != live, logs


def refresh(live, ids, feed=None, error=None):
    """live page object + a feed, or an error phrase. Never raises. Error keeps live."""
    if not isinstance(live, dict):
        live = {"polls": {}}
    if error:
        return live, False, ["WARNING polls: ESPN rankings %s; keeping the last good AP Top 25 and Coaches Poll" % error]
    if not isinstance(feed, dict) or not isinstance(feed.get("rankings"), list):
        return live, False, ["WARNING polls: ESPN rankings feed is malformed; keeping the last good AP Top 25 and Coaches Poll"]
    return apply_feed(live, ids, feed)


def valid_page_poll(p):
    if not isinstance(p, dict) or p.get("released") is not True:
        return False
    if week_of(p) is None or parse_pub(str(p.get("pub") or "")) is None:
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


def merge_candidate(live, cand):
    """Per-poll accept a page-shaped candidate. A bad or older poll stays at the live copy."""
    logs = []
    if not isinstance(live, dict):
        live = {"polls": {}}
    if not isinstance(cand, dict) or not isinstance(cand.get("polls"), dict):
        return live, False, ["WARNING polls: candidate is not a polls file; keeping the live file"]
    live_polls = live.get("polls") if isinstance(live.get("polls"), dict) else {}
    out = {}
    for key, label, _et in SPECS:
        old, new = live_polls.get(key), cand["polls"].get(key)
        if not valid_page_poll(new):
            logs.append("WARNING polls: %s candidate rejected; keeping the last good poll" % label)
            out[key] = _keep(old, label)
            continue
        if not newer(new, old):
            logs.append("polls: %s candidate is not newer (%s); keeping the live poll" % (label, older_reason(new, old)))
            out[key] = _keep(old, label)
            continue
        logs.append("polls: %s candidate accepted, %s -> week %s pub %s" % (label, brief(old), new["week"], new["pub"]))
        out[key] = new
    import cfp_refresh
    cfp_val, cfp_logs = cfp_refresh.merge_key(live_polls, cand.get("polls") if isinstance(cand, dict) else None)
    logs.extend(cfp_logs)
    if cfp_val is not None:
        out["cfp"] = cfp_val
    merged = {"polls": out}
    return merged, merged != live, logs


def plan(live_b, cand_b):
    """Bytes for the 3-way merge. s0 is always the live baseline. s1 changes only when a poll is newer and valid."""
    logs = []
    try:
        live = json.loads(live_b)
    except Exception:
        return live_b, live_b, False, ["WARNING polls: live polls.json is unreadable; not replacing it"]
    if cand_b is None:
        return live_b, live_b, False, ["polls: no candidate; live file is the baseline and the result"]
    try:
        cand = json.loads(cand_b)
    except Exception:
        return live_b, live_b, False, ["WARNING polls: candidate is unreadable; keeping the live file"]
    merged, changed, more = merge_candidate(live, cand)
    logs.extend(more)
    if not changed:
        return live_b, live_b, False, logs
    out_b = json.dumps(merged, separators=(",", ":"), ensure_ascii=False).encode()
    return live_b, out_b, True, logs


def inject_polls(base_dir, s0_dir, s1_dir, candidate=None):
    """Make S0 the live polls file and S1 the accepted update, so merge3 takes S1 when they differ.

    The pipeline build writes released=false (data/out is not in git). Copying the live
    bytes onto both sides, then the candidate onto S1 only when it is newer, is what
    lets the update through. A missing or bad candidate leaves both sides equal to live,
    and the merge keeps the live file. Never raises.
    """
    live_path = os.path.join(base_dir, "data", "polls.json")
    if not os.path.isfile(live_path):
        print("WARNING polls: live data/polls.json missing; merge left unchanged")
        return False
    live_b = open(live_path, "rb").read()
    cand_b = None
    if candidate:
        if os.path.isfile(candidate):
            cand_b = open(candidate, "rb").read()
        else:
            print("WARNING polls: candidate missing; keeping the live file")
    s0, s1, changed, logs = plan(live_b, cand_b)
    for line in logs:
        print(line)
    for folder, blob in ((s0_dir, s0), (s1_dir, s1)):
        dest = os.path.join(folder, "data", "polls.json")
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        tmp = dest + ".tmp"
        with open(tmp, "wb") as f:
            f.write(blob)
        os.replace(tmp, dest)
    print("polls: 3-way merge baseline is the live file; s1 %s" % ("carries the update" if changed else "matches it (pipeline copy not used)"))
    return changed


def degrade_to_week(live, week="10"):
    """A copy of a page file rewound one publication, for a dry-run pickup proof. Does not touch the live zip."""
    o = copy.deepcopy(live)
    target = int(week)
    for key, p in list((o.get("polls") or {}).items()):
        if key == "cfp":
            continue
        if not isinstance(p, dict) or p.get("released") is not True:
            continue
        pub = parse_pub(str(p.get("pub") or ""))
        p["week"] = str(target)
        if pub is not None:
            pub = pub - dt.timedelta(days=7)
            p["pub"] = fmt_pub(pub)
            p["asof"] = asof_label(pub)
    return o


def asof_line(polls):
    """The home as-of sentence, same rule as assets/top25.js on the live site and tools/bake_static.js."""
    def one(key, nm):
        p = (polls.get("polls") or {}).get(key) or {}
        if not p.get("released"):
            return "%s poll: not released yet." % nm
        stamp = str(p.get("asof") or "")
        if re.search(r"\d:\d\d|[ap]\.?m\b", stamp, re.I) and not stamp.endswith(" MT"):
            stamp += " MT"
        return "%s poll as of %s." % (nm, stamp)
    line = one("ap", "AP") + " " + one("coaches", "Coaches")
    cfp = (polls.get("polls") or {}).get("cfp") or {}
    if cfp.get("released") and str(cfp.get("asof") or "").strip():
        stamp = str(cfp.get("asof") or "")
        if re.search(r"\d:\d\d|[ap]\.?m\b", stamp, re.I) and not stamp.endswith(" MT"):
            stamp += " MT"
        line += " CFP, %s." % stamp
    return line


def cell(polls, slug):
    def pv(key):
        p = (polls.get("polls") or {}).get(key) or {}
        if not p.get("released"):
            return "\u2014"
        for row in p.get("ranks") or []:
            if isinstance(row, list) and len(row) >= 2 and row[1] == slug:
                return str(row[0])
        return "NR"
    bit = "AP %s \u00b7 Coaches %s" % (pv("ap"), pv("coaches"))
    cfp = (polls.get("polls") or {}).get("cfp") or {}
    if cfp.get("released"):
        rank = None
        for row in cfp.get("ranks") or []:
            if isinstance(row, list) and len(row) >= 2 and row[1] == slug:
                rank = str(row[0])
                break
        bit += " \u00b7 CFP %s" % (rank if rank else "\u2014")
    return bit


def check_baked(site):
    """Problems if raw home HTML does not show the polls.json as-of line and AP/Coaches cells. Empty list means it matches."""
    try:
        polls = json.load(open(os.path.join(site, "data", "polls.json"), encoding="utf-8"))
        html = open(os.path.join(site, "index.html"), encoding="utf-8").read()
        top = json.load(open(os.path.join(site, "data", "pred-top25.json"), encoding="utf-8"))
    except Exception as e:
        return ["unreadable site (%s)" % e]
    line = asof_line(polls)
    i = html.find('id="top25"')
    if i < 0:
        return ["home #top25 section is missing"]
    j = html.find("</section>", i)
    sec = html[i:j if j > i else None]
    problems = []
    if line not in sec:
        problems.append("as-of line %r is not in the home Top 25 section" % line)
    for e in (top.get("teams") or [])[:25]:
        slug = e[0] if isinstance(e, list) and e else None
        if not slug:
            continue
        m = re.search(r'<a class="h25-r"[^>]*href="/team/%s/"[\s\S]*?</a>' % re.escape(slug), sec)
        bit = cell(polls, slug)
        if not m:
            problems.append("%s row missing" % slug)
        elif bit not in m.group(0):
            problems.append("%s cell %r missing" % (slug, bit))
    return problems


def _read_live(args):
    if args.live:
        return open(args.live, "rb").read()
    if not args.zip or not os.path.isfile(args.zip):
        print("WARNING polls: live zip missing; keeping the last good polls file")
        return None
    try:
        with zipfile.ZipFile(args.zip) as z:
            return z.read("data/polls.json")
    except Exception as e:
        print("WARNING polls: could not read data/polls.json from the live zip (%s); keeping the last good polls file" % e)
        return None


def _write(path, obj):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    data = json.dumps(obj, separators=(",", ":"), ensure_ascii=False).encode()
    tmp = path + ".tmp"
    with open(tmp, "wb") as f:
        f.write(data)
    os.replace(tmp, path)
    return data


def _main(argv):
    ap = argparse.ArgumentParser(description="Refresh AP and Coaches polls. Always exits 0.")
    ap.add_argument("--zip", help="live site zip; data/polls.json inside is the baseline")
    ap.add_argument("--live", help="live polls.json path (tests)")
    ap.add_argument("--out", help="written only when a poll actually updates")
    ap.add_argument("--baseline-out", help="written only for a dry-run week10 baseline")
    ap.add_argument("--feed", help="read this JSON instead of the network")
    ap.add_argument("--url", default="")
    ap.add_argument("--baseline", default="", help="week10 rewinds the comparison copy; dry run only")
    ap.add_argument("--fail", default="", help="timeout or http; off unless set")
    ap.add_argument("--ids", default="")
    ap.add_argument("--check-site", help="compare baked home HTML to data/polls.json; always exits 0")
    ap.add_argument("--cfp", action="store_true", help="also refresh the CFP committee rankings; a failure stays a warning")
    ap.add_argument("--timeout", type=float, default=15)
    a = ap.parse_args(argv)
    if a.check_site:
        probs = check_baked(a.check_site)
        try:
            print("polls: baked as-of expected " + asof_line(json.load(open(os.path.join(a.check_site, "data", "polls.json"), encoding="utf-8"))))
        except Exception as e:
            print("WARNING polls: baked-HTML check could not read polls.json (%s)" % e)
        if probs:
            for p in probs:
                print("WARNING polls: baked HTML: " + p)
        else:
            print("polls: baked HTML matches polls.json")
        print("POLLS_CHANGED=0")
        return 0
    live_b = _read_live(a)
    if live_b is None:
        print("POLLS_CHANGED=0")
        return 0
    try:
        live = json.loads(live_b)
    except Exception as e:
        print("WARNING polls: live polls.json is unreadable (%s); keeping it" % e)
        print("POLLS_CHANGED=0")
        return 0
    try:
        ids = load_ids(a.ids or None)
    except Exception as e:
        print("WARNING polls: team id map unreadable (%s); keeping the last good polls file" % e)
        print("POLLS_CHANGED=0")
        return 0
    url = a.url or os.environ.get("KT_POLLS_URL") or DEFAULT_URL
    fail = (a.fail or os.environ.get("KT_POLLS_FAIL") or "").strip()
    baseline = (a.baseline or os.environ.get("KT_POLLS_BASELINE") or "").strip()
    if baseline and baseline != "week10":
        print("WARNING polls: ignoring unknown baseline %r (only week10 is a dry-run hook)" % baseline)
        baseline = ""
    feed, error = None, None
    if fail == "timeout":
        error = "timeout"
        print("polls: forced timeout (KT_POLLS_FAIL / --fail); no request sent")
    elif fail == "http":
        error = "HTTP 503"
        print("polls: forced HTTP 503 (KT_POLLS_FAIL / --fail); no request sent")
    elif fail:
        print("WARNING polls: ignoring unknown KT_POLLS_FAIL/%s; reading the feed" % fail)
        fail = ""
    if error is None and a.feed:
        print("polls: reading feed file %s" % a.feed)
        try:
            feed = json.load(open(a.feed, encoding="utf-8"))
        except Exception as e:
            error = "malformed feed"
            print("WARNING polls: feed file unreadable (%s)" % e)
    elif error is None:
        print("polls: reading %s" % url)
        feed, exc = fetch_rankings(url, timeout=a.timeout, tries=2)
        if exc is not None:
            error = classify(exc)
    live_view, live_changed, live_logs = refresh(live, ids, feed=feed, error=error)
    print("polls: live file %s; %s" % (brief(live.get("polls", {}).get("ap")), brief(live.get("polls", {}).get("coaches"))))
    for line in live_logs:
        print(line)
    print("polls: against the real live file: %s" % ("update" if live_changed else "no-op"))
    use, use_changed = live_view, live_changed
    wrote_base = False
    if baseline == "week10":
        if error or feed is None:
            print("WARNING polls: baseline simulation not applied because the ESPN feed was not read; the live file stays the baseline")
        else:
            base = degrade_to_week(live, "10")
            use, use_changed, sim_logs = refresh(base, ids, feed=feed)
            print("polls: simulated baseline week 10 (dry run only; the live zip is not modified)")
            for line in sim_logs:
                print(line)
            if a.baseline_out and use_changed:
                _write(a.baseline_out, base)
                wrote_base = True
                print("POLLS_BASELINE=%s" % os.path.abspath(a.baseline_out))
    if a.cfp or os.environ.get("KT_CFP") == "1":
        try:
            import cfp_refresh
            names = cfp_refresh.load_names(a.ids or None)
            fail_cfp = (os.environ.get("KT_CFP_FAIL") or "").strip()
            html = html_url = feed_cfp = None
            html_path = (os.environ.get("KT_CFP_HTML") or "").strip()
            feed_path = (os.environ.get("KT_CFP_FEED") or "").strip()
            if html_path and not fail_cfp:
                html = open(html_path, encoding="utf-8").read()
                html_url = (os.environ.get("KT_CFP_URL") or "").strip()
            if feed_path and not fail_cfp:
                feed_cfp = json.load(open(feed_path, encoding="utf-8"))
            elif feed is not None and not fail_cfp and not (a.url or os.environ.get("KT_POLLS_URL")):
                feed_cfp = feed
            src = cfp_refresh.read_sources(
                names, ids, cfp_refresh.denver_today(), html=html, html_url=html_url, feed=feed_cfp,
                fail=fail_cfp, timeout=8, network=not fail_cfp and html is None)
            use, cfp_changed, cfp_logs = cfp_refresh.apply(use, names, ids, **src)
            for line in cfp_logs:
                print(line)
            use_changed = use_changed or cfp_changed
        except Exception as e:
            print("WARNING polls: CFP step failed (%s); keeping the last good rankings" % e)
    if use_changed and a.out:
        _write(a.out, use)
        print("POLLS_OUT=%s" % os.path.abspath(a.out))
        print("POLLS_CHANGED=1")
    else:
        if baseline == "week10" and not wrote_base:
            print("polls: simulated baseline produced no update")
        print("POLLS_CHANGED=0")
    return 0


def main(argv=None):
    try:
        return _main(sys.argv[1:] if argv is None else argv)
    except Exception as e:
        print("WARNING polls: %s: %s; keeping the last good polls file" % (e.__class__.__name__, e))
        print("POLLS_CHANGED=0")
        return 0


if __name__ == "__main__":
    sys.exit(main())
