"""Market consensus spread from The Odds API (free Starter plan, 500 credits/month). ONE call per refresh (1 credit: 1 region x 1 market).
Rules: min 12 h between calls (use --force to override); fail soft (keep last cache, label it with its fetched time); skip the call if the last
known quota is < 50 remaining; the key lives only in private/odds_api.env (never printed, never copied into build/, dist/ or any page).
Outputs: data/cache/odds_ncaaf.json (raw API reply, INTERNAL, has bookmaker names, never shipped), data/out/odds_consensus.json (consensus per game,
NO bookmaker names, links or prices), data/out/odds_meta.json (quota, fetch time, matched/unmatched lists).
Usage: python3 src/odds.py [--force]"""
import os, sys, json, time, re, statistics, unicodedata, datetime as dt, urllib.request, urllib.error
from zoneinfo import ZoneInfo
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = f"{ROOT}/data/cache/odds_ncaaf.json"; OUT = f"{ROOT}/data/out"
URL = "https://api.the-odds-api.com/v4/sports/americanfootball_ncaaf/odds/?regions=us&markets=spreads&oddsFormat=american&apiKey="
MIN_INTERVAL = 12 * 3600; LOW_QUOTA = 50
MT = ZoneInfo("America/Denver")

def key():
    for line in open(f"{ROOT}/private/odds_api.env"):
        if line.startswith("ODDS_API_KEY="): return line.split("=", 1)[1].strip()
    raise SystemExit("no key")

def now_mt(): return dt.datetime.now(MT).strftime("%Y-%m-%d %H:%M MT")

def load_meta():
    p = f"{OUT}/odds_meta.json"
    return json.load(open(p)) if os.path.exists(p) else {}

def fetch(force=False):
    meta = load_meta(); note = None
    age = time.time() - os.path.getmtime(CACHE) if os.path.exists(CACHE) else None
    rem = meta.get("requests_remaining")
    if age is not None and age < MIN_INTERVAL and not force:
        note = f"cache is {age/3600:.1f} h old (< 12 h): no call made"
    elif rem is not None and rem < LOW_QUOTA:
        note = f"quota low ({rem} remaining): no call made, last cache kept"
    else:
        try:
            r = urllib.request.urlopen(urllib.request.Request(URL + key(), headers={"User-Agent": "KickTip data refresh"}), timeout=30)
            body = json.load(r); h = r.headers
            os.makedirs(os.path.dirname(CACHE), exist_ok=True)
            tmp = CACHE + ".tmp"; json.dump(body, open(tmp, "w")); os.replace(tmp, CACHE)
            meta.update(requests_remaining=int(h.get("x-requests-remaining", -1)), requests_used=int(h.get("x-requests-used", -1)),
                        requests_last=int(h.get("x-requests-last", -1)), last_call_mt=now_mt(), last_call_epoch=int(time.time()), last_error=None)
            note = "fetched"
        except urllib.error.HTTPError as e: note = f"HTTP {e.code}: call failed, last cache kept"
        except Exception as e: note = f"{type(e).__name__}: call failed, last cache kept"
        if note != "fetched": meta["last_error"] = note
    meta["last_note"] = note
    return meta, (json.load(open(CACHE)) if os.path.exists(CACHE) else None)

ALIAS = {  # normalized API name -> normalized our name (after generic normalisation); filled from the unmatched list in odds_meta.json
    "southern mississippi golden eagles": "southern miss golden eagles",
    "sam houston state bearkats": "sam houston bearkats",
}
def norm(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    s = s.replace("&", " and ").replace("'", "").replace(".", " ").replace("-", " ")
    s = re.sub(r"\bst\b", "state", s); s = re.sub(r"[^a-z0-9() ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()

def consensus(events, games, names):
    idx = {}
    for g in games:
        idx.setdefault((norm(g["home"]), norm(g["away"])), []).append(g)
    nset = set(norm(n) for n in names)
    out, unmatched, n_ev = [], [], 0
    for ev in events or []:
        n_ev += 1
        h, a = norm(ev["home_team"]), norm(ev["away_team"]); h, a = ALIAS.get(h, h), ALIAS.get(a, a)
        pts = []
        for bk in ev.get("bookmakers", []):
            for m in bk.get("markets", []):
                if m.get("key") != "spreads": continue
                o = {norm(x["name"]): x.get("point") for x in m.get("outcomes", [])}
                o = {ALIAS.get(k, k): v for k, v in o.items()}
                if h in o and o[h] is not None: pts.append(float(o[h]))
        t = dt.datetime.strptime(ev["commence_time"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc)
        cand, flip = idx.get((h, a)), False
        if not cand: cand, flip = idx.get((a, h)), True
        if cand:
            cand = [g for g in cand if abs((dt.datetime.strptime(g["date_utc"], "%Y-%m-%dT%H:%MZ").replace(tzinfo=dt.timezone.utc) - t).total_seconds()) < 40 * 3600]
        if not cand:
            if h in nset or a in nset:  # at least one FBS team in our list but no remaining-game match
                unmatched.append(dict(home=ev["home_team"], away=ev["away_team"], commence_mt=t.astimezone(MT).strftime("%Y-%m-%d %H:%M"), reason="no remaining game with these teams" if (h in nset and a in nset) else "one team not in our FBS list"))
            continue
        g = cand[0]
        if not pts:
            unmatched.append(dict(home=ev["home_team"], away=ev["away_team"], commence_mt=t.astimezone(MT).strftime("%Y-%m-%d %H:%M"), reason="no spreads posted")); continue
        med = statistics.median(pts)
        if flip: med = -med
        med = round(med * 2) / 2
        out.append(dict(home=g["home"], away=g["away"], date_utc=g["date_utc"], market_spread_home=med + 0.0, n_books=len(pts)))
    return out, unmatched, n_ev

def main():
    force = "--force" in sys.argv
    meta, raw = fetch(force)
    sg = json.load(open(f"{OUT}/sim_games.json"))["games"]
    names = {g["home"] for g in sg} | {g["away"] for g in sg}
    cons, unm, n_ev = consensus(raw, sg, names)
    fetched = meta.get("last_call_mt")
    meta.update(events_in_cache=n_ev, games_remaining=len(sg), games_matched=len(cons), unmatched=unm, as_of_mt=fetched,
                label="Market line: point spread from public sources, rounded to 0.5. No source names or prices are stored in this file.")
    os.makedirs(OUT, exist_ok=True)
    json.dump(dict(label=meta["label"], as_of_mt=fetched, source="public sources", games=cons), open(f"{OUT}/odds_consensus.json", "w"), indent=1)
    json.dump(meta, open(f"{OUT}/odds_meta.json", "w"), indent=1)
    print(meta["last_note"], "| remaining credits:", meta.get("requests_remaining"), "| used:", meta.get("requests_used"), "| events:", n_ev, "| matched:", len(cons), "of", len(sg), "| unmatched listed:", len(unm))

if __name__ == "__main__": main()
