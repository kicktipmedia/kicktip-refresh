"""Market lines, NUMBERS ONLY (SPEC-4 section 1, approved design: "Market line", no provider name, logo, link or book count anywhere).
Source: ESPN's free public scoreboard feed (pre-game 'odds' block) from the coverage research in /workspace/kicktip-research/ESPN-ODDS-COVERAGE.md,
No stored/older numbers are used as a fallback (t25 build): a game ESPN has no line for has no line.
Only ONE number is ever read from the feed: the point spread from the HOME team's side (negative = home favored). Provider, logo, link, moneyline, over/under and
every other field are never read and never written. Nothing is ever estimated: a game with no line has no line.
Files: data/store/espn_lines.json (snapshot of the last ESPN pull: id, home, away, kickoff, spread, pulled time), data/out/market_lines.json (merged, what build.py reads; INTERNAL, not shipped as is).
Network: only `--pull`. It makes ONE scoreboard request per day for the next 14 days (about 14 requests, 1.1 s apart), at most once per 12 h (`--force` overrides), fail soft (keeps the last snapshot).
It never contacts any odds provider, never reads private/ and needs no key.
Usage: python3 src/lines.py [--pull [--force]] | [--ingest-research DIR]   (no flag: merge only, offline)"""
import os, sys, json, time, re, glob, datetime as dt, urllib.request, urllib.error
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTD = f"{ROOT}/data/out"; STORE = f"{ROOT}/data/store/espn_lines.json"; OUT = f"{OUTD}/market_lines.json"
SB = "https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard?dates=%s&groups=80&limit=300"
MIN_INTERVAL = 12 * 3600; DAYS = 14

def utc(s): return dt.datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc)
def epoch(d): return int(d.timestamp())

def parse_day(doc, pulled_epoch):
    """Rows (id, home, away, kickoff_utc 'YYYY-MM-DDTHH:MMZ', spread_home, t) for SCHEDULED events that carry a pre-game point spread. Reads ONLY: event id, date, team display names, status name,
    odds[0].spread and homeTeamOdds.favorite (a sign sanity check). A started game is never taken (its entry would be a live line). Returns (rows, skipped_count_by_reason)."""
    rows, skip = [], {"not scheduled": 0, "no spread": 0, "sign mismatch": 0}
    for e in doc.get("events", []):
        c = (e.get("competitions") or [{}])[0]
        if (e.get("status", {}).get("type", {}).get("name")) != "STATUS_SCHEDULED": skip["not scheduled"] += 1; continue
        od = c.get("odds") or []
        if not od or not isinstance(od[0].get("spread"), (int, float)): skip["no spread"] += 1; continue
        sp = float(od[0]["spread"]); fav = (od[0].get("homeTeamOdds") or {}).get("favorite")
        if (sp < 0 and fav is False) or (sp > 0 and fav is True): skip["sign mismatch"] += 1; continue
        h = [x for x in c["competitors"] if x["homeAway"] == "home"][0]["team"]["displayName"]; a = [x for x in c["competitors"] if x["homeAway"] == "away"][0]["team"]["displayName"]
        k = e["date"]; k = k if len(k) == 17 else k[:16] + "Z"       # 'YYYY-MM-DDTHH:MMZ'
        rows.append(dict(id=str(e["id"]), home=h, away=a, kickoff=k, s=sp + 0.0, t=pulled_epoch))
    return rows, skip

def save_store(rows, note):
    os.makedirs(os.path.dirname(STORE), exist_ok=True)
    pulled = max([r["t"] for r in rows] or [0])
    tmp = STORE + ".tmp"; json.dump(dict(note=note, pulled_epoch=pulled, lines=rows), open(tmp, "w"), indent=1); os.replace(tmp, STORE)

def ingest_research(d):
    """Re-reads the saved scoreboard day files of the coverage research (no network). Each day's pull time is that request's time in requests.log (UTC)."""
    when = {}
    for line in open(f"{d}/requests.log"):
        m = re.match(r"(\S+) 200 .*scoreboard\?dates=(\d{8})&", line)
        if m: when.setdefault(m.group(2), dt.datetime.fromisoformat(m.group(1)).replace(tzinfo=dt.timezone.utc))   # first request of the day file = the file on disk
    rows, skip = [], {}
    for f in sorted(glob.glob(f"{d}/scoreboard/2026*.json")):
        day = os.path.basename(f)[:8]; r, s = parse_day(json.load(open(f)), epoch(when[day]))
        rows += r
        for k, v in s.items(): skip[k] = skip.get(k, 0) + v
    save_store(rows, "ESPN public scoreboard, saved research pull Oct 24 2026 6:30-6:45 PM ET; numbers only"); print("ingested", len(rows), "pre-game spreads;", skip); return rows

def pull(force=False):
    if os.path.exists(STORE):
        age = time.time() - json.load(open(STORE))["pulled_epoch"]
        if age < MIN_INTERVAL and not force: print(f"last pull is {age/3600:.1f} h old (< 12 h): no request made"); return None
    rows, skip, today = [], {}, dt.datetime.now(dt.timezone.utc).date()
    try:
        for i in range(DAYS):
            day = (today + dt.timedelta(days=i)).strftime("%Y%m%d")
            r = urllib.request.urlopen(urllib.request.Request(SB % day, headers={"User-Agent": "KickTip data refresh"}), timeout=30)
            r_, s = parse_day(json.load(r), int(time.time())); rows += r_
            for k, v in s.items(): skip[k] = skip.get(k, 0) + v
            time.sleep(1.1)
    except Exception as e:
        print(f"{type(e).__name__}: pull failed, the last snapshot is kept"); return None
    save_store(rows, "ESPN public scoreboard pull; numbers only"); print("pulled", len(rows), "pre-game spreads;", skip); return rows

def merge():
    """data/out/market_lines.json: one entry per game id with a line. ESPN snapshot only (no stored fallback). A game only gets a line if the
    teams match sim_games exactly (by game id). Never a book count, never a provider."""
    sg = json.load(open(f"{OUTD}/sim_games.json"))["games"]; byid = {g["id"]: g for g in sg}; out = {}
    esp = json.load(open(STORE)) if os.path.exists(STORE) else dict(lines=[], pulled_epoch=None); bad = 0
    for r in esp["lines"]:
        g = byid.get(r["id"])
        if not g or g["home"] != r["home"] or g["away"] != r["away"]: bad += 1; continue
        out[g["id"]] = dict(id=g["id"], home=g["home"], away=g["away"], kickoff=g["date_utc"], s=r["s"], t=r["t"], src="a")
    n_old = 0; t_old = None   # t25 build: the stored older numbers (data/out/odds_consensus.json) are NOT used any more. Every line shown comes from the ESPN public scoreboard pull, so the Sources strip ("Market lines: ESPN") is true for every game.
    res = dict(note="Market line numbers only (point spread, home side, negative = home favored). No provider, link or book count. src a = ESPN public scoreboard snapshot (the only source). INTERNAL; the site ships only s and t.",
               espn_pulled_epoch=esp["pulled_epoch"], fallback_epoch=t_old, counts=dict(espn=sum(1 for v in out.values() if v["src"] == "a"), fallback=n_old, espn_rows_unmatched=bad),
               lines=sorted(out.values(), key=lambda x: (x["kickoff"], x["id"])))
    json.dump(res, open(OUT, "w"), indent=1); print("market_lines.json:", res["counts"], "games with a line:", len(out)); return res

if __name__ == "__main__":
    a = sys.argv[1:]
    if "--ingest-research" in a: ingest_research(a[a.index("--ingest-research") + 1])
    elif "--pull" in a: pull("--force" in a)
    merge()
