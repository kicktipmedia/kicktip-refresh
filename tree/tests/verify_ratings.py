"""Ported rating model must reproduce the MSM CSV exactly when fed the games the CSV was built from (MSM's games_v3_2026.json, 517 games, copied once to data/ref)."""
import sys, os, json, csv
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, R + "/src")
import ratings
G = json.load(open(R + "/data/ref/games_v3_2026_517.json"))
m = ratings.fit(G); rows = list(csv.DictReader(open(R + "/data/ref/msm_all_v3_2026.csv")))
inv = {v: k for k, v in m["fbs"].items()}
d = max(abs(round(m["rating"][m["ix"][inv[r["team"]]]], 1) - float(r["msm_rating"])) for r in rows)
same = [m["fbs"][t] for t in m["order"]] == [r["team"] for r in rows]
print("max rating diff %.2f; same rank order: %s" % (d, same)); assert d == 0 and same
