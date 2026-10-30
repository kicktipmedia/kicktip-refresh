"""KickTip refresh step: College Football Playoff selection committee rankings -> data/tb/cfp-rankings.json (tool cfp_committee_rankings).
    python3 tools/export_cfp_rankings.py <tree> [--payload saved.json] [--out path]
Source (free, no key): first the ESPN site rankings feed (any rankings[] entry with type "cfp"), then the ESPN core API
seasons/{yr}/types/2/weeks/{wk}/rankings/21 for the current week and the week before. A 404 / no cfp entry means "not released":
the file is written as {"asof":..., "released": false, "teams": []}. Teams are matched by ESPN team id through ref/conf_2026.json
(the same id map polls.py uses) and the bundle's team names; an id that does not map is dropped and logged, never guessed.
The page never calls ESPN. asof is the sim-bundle as_of of the tree the file ships in."""
import json, os, re, sys, urllib.request, urllib.error
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
SITE = "https://site.api.espn.com/apis/site/v2/sports/football/college-football/rankings"
CORE = "https://sports.core.api.espn.com/v2/sports/football/leagues/college-football/seasons/{yr}/types/2/weeks/{wk}/rankings/21"

def get(url):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "KickTip refresh"}), timeout=30) as r: return json.load(r)
    except urllib.error.HTTPError as e:
        if e.code == 404: return None
        raise

def id_map(tree):
    conf = json.load(open(os.path.join(ROOT, "ref", "conf_2026.json")))
    B = json.load(open(os.path.join(tree, "data", "sim-bundle.json")))
    P = json.load(open(os.path.join(tree, "data", "pred-teams.json")))["teams"]
    by_name = {}
    for t in B["teams"]:
        if t.get("g"): by_name[t["n"]] = t["g"]
    for g, p in P.items(): by_name.setdefault(p.get("n"), g)
    return {str(v["id"]): by_name.get(k) for k, v in conf.items()}, B

def tid(x):
    t = x.get("team") or {}
    if "id" in t: return str(t["id"])
    m = re.search(r"/teams/(\d+)", t.get("$ref", "")); return m.group(1) if m else None

def convert(payload, ids, asof, url):
    rows, dropped = [], []
    for x in payload.get("ranks") or []:
        cur = x.get("current"); i = tid(x)
        if not isinstance(cur, int) or cur < 1: continue
        slug = ids.get(i)
        if not slug: dropped.append({"rank": cur, "espn": i}); continue
        prev = x.get("previous"); rec = (x.get("record") or {}).get("summary") or x.get("recordSummary") or ""
        rows.append({"rank": cur, "prev": prev if isinstance(prev, int) and prev > 0 else None, "slug": slug, "record": rec})
    rows.sort(key=lambda r: r["rank"])
    wk = (payload.get("occurrence") or {}).get("value")
    out = {"asof": asof, "released": bool(rows), "week": int(wk) if wk is not None else None, "source_url": url, "teams": rows}
    if not rows: out = {"asof": asof, "released": False, "teams": []}
    return out, dropped

def main(a):
    tree = os.path.abspath(a[0]); out = os.path.join(tree, "data", "tb", "cfp-rankings.json")
    if "--out" in a: out = a[a.index("--out") + 1]
    ids, B = id_map(tree); asof = B["as_of"]
    if "--payload" in a:
        p = a[a.index("--payload") + 1]; payload = json.load(open(p)); url = a[a.index("--url") + 1] if "--url" in a else p
    else:
        payload, url = None, None
        feed = get(SITE) or {}
        for r in feed.get("rankings", []):
            if r.get("type") == "cfp" and r.get("ranks"): payload, url = r, SITE; break
        if payload is None:
            yr = int(asof[:4]); wk = min(g["wk"] for g in B["games"]) if B["games"] else 16
            for w in (wk, wk - 1):
                u = CORE.format(yr=yr, wk=w); d = get(u)
                if d and d.get("ranks"): payload, url = d, u; break
    res, dropped = convert(payload or {}, ids, asof, url)
    for d in dropped: print("cfp-rankings: dropped unmapped ESPN id", d)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    tmp = out + ".tmp"; json.dump(res, open(tmp, "w"), separators=(",", ":")); os.replace(tmp, out)
    print("wrote", out, "released" if res["released"] else "not released", len(res["teams"]), "teams")
    return 0

if __name__ == "__main__": sys.exit(main(sys.argv[1:]))
