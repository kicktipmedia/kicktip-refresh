"""KickTip Top 25 refresh step: AP Top 25 and Coaches Poll ranks from ESPN's free public rankings feed.
    python3 src/polls.py && python3 src/build.py
Writes data/out/polls.json (static; the browser never calls ESPN). Fail-soft: if the feed is down or a poll is missing, the previous file is kept and
nothing is invented; a poll the feed does not carry is written as released=false (the page then says "not released yet").
Each poll keeps its OWN publication time (ESPN's lastUpdated, UTC) and week: the page prints that, never our refresh time, and never carries a rank from a
different week into the current week's column. Teams are matched by ESPN team id (data/ref/conf_2026.json); anything unmatched is listed in 'unmatched'."""
import json, os, sys, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import espn
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = f"{ROOT}/data/out/polls.json"
URL = espn.BASE + "rankings"
POLLS = (("ap", "AP Top 25", "ap"), ("coaches", "Coaches Poll", "usa"))   # (our key, label, ESPN ranking type)

def utc(s):
    """'2026-10-18T21:15Z' -> aware UTC datetime (None if absent or unreadable)."""
    try: return dt.datetime.strptime(s.replace("Z", "+0000").replace("+00:00", "+0000"), "%Y-%m-%dT%H:%M%z")
    except Exception: return None

def poll_from_feed(feed, etype, ids):
    """One poll, or None if the feed does not carry it (or it has no ranked teams)."""
    for r in feed.get("rankings", []):
        if r.get("type") != etype: continue
        ranks = r.get("ranks") or []
        if not ranks: return None
        pub = utc(r.get("lastUpdated") or "") or utc(r.get("date") or "")
        wk = (r.get("occurrence") or {}).get("value")
        rows, unmatched = [], []
        for x in ranks:
            tid = str(x["team"]["id"]); cur = x.get("current")
            if not isinstance(cur, int) or cur < 1: continue
            row = dict(r=cur, espn=tid, rec=x.get("recordSummary") or "", fp=x.get("firstPlaceVotes") or 0, pts=x.get("points"))
            if tid not in ids: unmatched.append(dict(r=cur, espn=tid, team=x["team"].get("location") or x["team"].get("name")))
            rows.append(row)
        rows.sort(key=lambda z: z["r"])
        return dict(released=True, week=wk, published=pub.strftime("%Y-%m-%dT%H:%MZ") if pub else None, feed_date=r.get("date"), ranks=rows, unmatched=unmatched)
    return None

def main():
    conf = json.load(open(f"{ROOT}/data/ref/conf_2026.json")); ids = {str(v["id"]): k for k, v in conf.items()}
    feed = espn.fetch(URL, tries=3, timeout=30)
    prev = json.load(open(OUT)) if os.path.exists(OUT) else None
    if feed is None:
        print("ESPN rankings feed unreachable;", "keeping the previous", OUT if prev else "writing 'not released'")
        if prev: return 0
        feed = {}
    out = dict(source="ESPN public rankings feed (site.api.espn.com), fetched at refresh; the page never calls ESPN", fetched=dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ"), polls={})
    for key, label, et in POLLS:
        p = poll_from_feed(feed, et, ids)
        if p is None: p = dict(released=False, week=None, published=None, feed_date=None, ranks=[], unmatched=[])
        p["name"] = label; out["polls"][key] = p
        miss = [u for u in p["unmatched"]]
        print(f"{label}: " + (f"week {p['week']}, published {p['published']}, {len(p['ranks'])} ranked, {len(miss)} unmatched {miss}" if p["released"] else "not released (feed has no ranks)"))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    tmp = OUT + ".tmp"; json.dump(out, open(tmp, "w"), indent=1); os.replace(tmp, OUT); print("wrote", OUT); return 0

if __name__ == "__main__": sys.exit(main())
