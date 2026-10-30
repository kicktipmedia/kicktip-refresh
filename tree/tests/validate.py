"""Back-test the tiebreak engine on past seasons: rebuild final regular-season conference standings from ESPN public JSON (conferenceCompetition games),
run src/tiebreak.py with the 2026 rules table, compare the selected title-game teams with who actually played (ESPN 'Championship' events).
Proprietary / committee steps use a proxy (overall win pct), so a result decided at the rating/draw step is reported as 'proxy-decided'."""
import sys, os, json, random
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
import espn, tiebreak, rules
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
B = espn.BASE + "scoreboard?dates={y}&seasontype=2&week={w}&groups={g}&limit=300"
GID = {"acc": 1, "big12": 4, "big10": 5, "sec": 8, "usa": 12, "midam": 15, "mwest": 17, "belt": 37, "American": 151}
HEAD = {"ACC": "acc", "Big 12": "big12", "Big Ten": "big10", "SEC": "sec", "Conference USA": "usa", "MAC": "midam", "Mountain West": "mwest", "Sun Belt": "belt", "American": "American"}
DIV_EAST = ("App State", "Coastal Carolina", "Georgia Southern", "Georgia State", "James Madison", "Marshall", "Old Dominion")

def ccg_participants(y):
    d = espn.fetch(B.format(y=y, w=15, g=80), f"{ROOT}/data/cache/val/{y}_w15_80.json", 10**9) or {"events": []}
    out = {}
    for e in d["events"]:
        c = e["competitions"][0]; hl = " ".join(n.get("headline", "") for n in c.get("notes", []))
        if "Championship" not in hl: continue
        for k, v in HEAD.items():
            if k in hl: out[v] = sorted(x["team"]["displayName"] for x in c["competitors"])
    return out

def games(y, conf, cut_week=14):
    gs = {}
    for w in range(1, cut_week + 1):
        d = espn.fetch(B.format(y=y, w=w, g=GID[conf]), f"{ROOT}/data/cache/val/{y}_w{w}_{GID[conf]}.json", 10**9)
        for e in (d or {"events": []})["events"]:
            c = e["competitions"][0]
            if not c.get("conferenceCompetition") or not c["status"]["type"]["completed"]: continue
            if any("Championship" in n.get("headline", "") for n in c.get("notes", [])): continue
            cs = c["competitors"]; hs = float(cs[0].get("score", 0)); a = float(cs[1].get("score", 0))
            gs[e["id"]] = (cs[0]["team"]["displayName"], cs[1]["team"]["displayName"], hs, a)
    return list(gs.values())

def overall(y, names, cut_week=14):
    """overall win pct from the group-80 scoreboard (proxy for proprietary steps)"""
    rec = {n: [0, 0] for n in names}
    for w in range(1, cut_week + 1):
        d = espn.fetch(B.format(y=y, w=w, g=80), f"{ROOT}/data/cache/val/{y}_w{w}_80.json", 10**9)
        for e in (d or {"events": []})["events"]:
            c = e["competitions"][0]
            if not c["status"]["type"]["completed"] or any("Championship" in n.get("headline", "") for n in c.get("notes", [])): continue
            cs = c["competitors"]
            for x, o in ((cs[0], cs[1]), (cs[1], cs[0])):
                n = x["team"]["displayName"]
                if n in rec: rec[n][0 if float(x.get("score", 0)) > float(o.get("score", 0)) else 1] += 1
    return {n: (w / (w + l) if w + l else 0) for n, (w, l) in rec.items()}

def run(y, conf):
    gs = games(y, conf)
    names = sorted({g[0] for g in gs} | {g[1] for g in gs}); ix = {n: i for i, n in enumerate(names)}; m = len(names)
    H = [[0] * m for _ in range(m)]
    for h, a, hs, as_ in gs:
        w, l = (h, a) if hs > as_ else (a, h); H[ix[w]][ix[l]] += 1
    ov = overall(y, names)
    rating = [ov[n] + 1e-6 * i for i, n in enumerate(names)]          # proxy; deterministic order
    rnd = random.Random(1); draw = [rnd.random() for _ in names]
    div = None
    if conf == "belt": div = ["East" if n.startswith(DIV_EAST) else "West" for n in names]
    c = tiebreak.Ctx(H, rating, draw, ov and [ov[n] for n in names], [ov[n] * 12 for n in names], [ov[n] for n in names], div)
    tr = []; top = tiebreak.select_ccg(c, rules.RULES[conf], tr)
    cw = {n: f"{c.W[ix[n]]}-{c.G[ix[n]] - c.W[ix[n]]}" for n in names}
    return sorted(names[i] for i in top), tr, cw, m, len(gs), names, c

if __name__ == "__main__":
    results = []
    for y in (2024, 2025):
        act = ccg_participants(y)
        for conf in GID:
            if conf not in act: print(y, conf, "no title game found on ESPN (skipped)"); continue
            got, tr, cw, m, ng, names, c = run(y, conf)
            ok = got == act[conf]
            proxy = [s for s in tr if s in ("rating", "draw", "margin_proxy", "apr")]
            top = sorted(range(m), key=lambda i: -c.pct[i])[:4]
            print(f"{y} {conf:9s} teams {m} games {ng}  {'MATCH' if ok else 'MISMATCH'}  engine={got}  actual={act[conf]}  decisive steps={tr}{'  [proxy-decided]' if proxy else ''}  top4 conf recs={[(names[i], cw[names[i]]) for i in top]}")
            results.append((y, conf, ok, bool(proxy)))
    print("summary: %d/%d match; %d of the matches/mismatches involved a proxy step" % (sum(r[2] for r in results), len(results), sum(r[3] for r in results)))
