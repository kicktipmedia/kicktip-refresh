"""Back-test the official-rules title-game engine (src/assets/ccgsim.js, run in Node) on the 2024 and 2025 regular seasons, using the cached ESPN public data that tests/validate.py reads
(no network needed when data/cache/val is present). For each conference with rules in src/ccg_rules_step*.py: rebuild final conference standings, run the engine, compare with who played the title game.
Verdicts: MATCH; MISMATCH (a real error unless the season's published rules differed from the 2026 text); NOT-RESOLVABLE (the engine reached a ranking/coin-toss step and, correctly, did not guess; counted OK if the actual pair is among the listed outcomes).
Caveat: the rules text used is the 2026 one; earlier seasons' tiebreakers (and 2024-25 division/format differences) can differ. Non-conference wins are approximated from ESPN group-80 results (FCS wins unknown)."""
import os, sys, json, subprocess
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, f"{ROOT}/src"); sys.path.insert(0, f"{ROOT}/tests")
import validate, ccg_rules, ccgsim_data
def case(y, code, rules):
    gs = validate.games(y, code)
    names = sorted({g[0] for g in gs} | {g[1] for g in gs}); ix = {n: i for i, n in enumerate(names)}
    games = [dict(id=f"{y}-{k}", h=ix[h], a=ix[a], w=1 if hs > as_ else 0) for k, (h, a, hs, as_) in enumerate(gs)]
    ov = validate.overall(y, names)
    cw = {n: sum(1 for g in gs if (g[0] == n and g[2] > g[3]) or (g[1] == n and g[3] > g[2])) for n in names}
    cg = {n: sum(1 for g in gs if n in (g[0], g[1])) for n in names}
    # overall games unknown here: approximate non-conference record from overall pct x a 12-game year
    nc = [dict(w=max(0, round(ov[n] * 12) - cw[n]), fcsw=0, fcsg=0, g=max(0, 12 - cg[n]), left=0) for n in names]
    div = None
    if code == "belt": div = [("East" if n.startswith(validate.DIV_EAST) else "West") for n in names]
    return dict(teams=[dict(short=n) for n in names], div=div, games=games, nc=nc)
def main():
    rules = ccg_rules.load(); cases = []
    for y in (2024, 2025):
        act = validate.ccg_participants(y)
        for code in rules:
            if code not in validate.GID or code not in act: continue
            r = dict(rules[code]); cases.append(dict(label=f"{y} {code}", conf=case(y, code, r), rules=r, actual=act[code]))
    p = subprocess.run(["node", f"{ROOT}/tests/ccg_backtest_run.js"], input=json.dumps(cases), capture_output=True, text=True)
    if p.returncode: print(p.stderr); sys.exit(1)
    res = json.loads(p.stdout); bad = 0
    for r in res:
        print(f"{r['label']:14s} {r['verdict']:60s} engine={r['got']}  actual={r['actual']}")
        if r["verdict"] == "MISMATCH" or "NOT among" in r["verdict"] or "actual pair NOT" in r["verdict"]: bad += 1
    nm = sum(r["verdict"] == "MATCH" for r in res); nr = sum(r["verdict"].startswith("NOT-RESOLVABLE") for r in res)
    print(f"back-test: {len(res)} cases, {nm} match, {nr} not-resolvable-by-design, {bad} problems")
    return 1 if bad else 0
if __name__ == "__main__": sys.exit(main())
