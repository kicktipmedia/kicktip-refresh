"""Writes data/ref/movers.json: the make-the-12 chance the ORIGINAL (unscaled) MSM percentages would give on today's data, next to the shipped default's, for the method-page sentence about how far numbers moved.
INTERNAL comparison only: the raw path is never selectable, never shipped as data; only the numbers for the teams named in the sentence reach the method page. Same data, seed and 10,000 seasons as the shipped run (the raw path reproduces the earlier site exactly: tests/engine_test.py --regress).
python3 src/movers.py   (about 4 s; run_all.py calls it after the default simulation)"""
import os, sys, json
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, f"{ROOT}/src"); sys.dont_write_bytecode = True
import sim

def main(seasons=10000, seed=2026):
    R = sim.run(seasons, seed, verbose=False, S=sim.Season("raw")); S = R["S"]
    raw = {S.name[t]: round(float(R["cfp_site"][:, t].mean()), 4) for t in range(S.n) if t != S.FCS}
    cur = {t["team"]: t["p_cfp_12"] for t in json.load(open(f"{ROOT}/data/out/sim_teams.json"))["teams"]}
    asof = json.load(open(f"{ROOT}/data/out/sim_teams.json"))["as_of"]
    out = dict(note="INTERNAL: make-12 chance under the original unscaled MSM percentages vs the shipped default, same data/seed. Not shipped as data.", as_of=asof, seasons=seasons, seed=seed,
               teams={n: [raw[n], cur[n]] for n in sorted(raw) if n in cur})
    json.dump(out, open(f"{ROOT}/data/ref/movers.json", "w"), indent=0); print("movers.json", len(out["teams"]), "teams", asof)

if __name__ == "__main__": main()
