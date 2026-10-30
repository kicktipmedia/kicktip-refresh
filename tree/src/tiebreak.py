"""Table-driven conference tiebreak engine. Rules live in src/rules.py (step names); this file implements each named step.

Context (Ctx) describes ONE conference in ONE season (real or simulated):
  m      member count; members 0..m-1
  H[i][j] conference wins of i over j (conference games that count toward standings)
  rating[i] proxy for every proprietary / committee ranking step (higher = better)
  draw[i]   seeded random number, decides coin tosses / random draws
  ovp[i]    overall win pct, at most one FCS win counted      wins12[i]  total wins, at most one FCS win
  fbsp[i]   win pct vs FBS opponents (all games)
  div[i]    division id (Sun Belt only)

Step functions return a list of scores for the tied teams (higher is better) or None when the step cannot separate them.
resolve() applies a procedure: the best group at each step advances (if it fits in the remaining slots) or the rest are eliminated;
when slots are filled by a step the remaining teams revert to the start of the procedure; when the field drops to two the two-team
procedure is used. This is the common structure of all the official policies read.
"""
from itertools import combinations

class Ctx:
    def __init__(s, H, rating, draw, ovp=None, wins12=None, fbsp=None, div=None):
        s.H = H; s.m = len(H); s.rating = rating; s.draw = draw
        s.ovp = ovp; s.wins12 = wins12; s.fbsp = fbsp; s.div = div
        m = s.m
        s.W = [sum(r) for r in H]
        s.P = [[H[i][j] + H[j][i] for j in range(m)] for i in range(m)]
        s.G = [sum(r) for r in s.P]
        s.pct = [s.W[i] / s.G[i] if s.G[i] else 0.0 for i in range(m)]
        s._groups = None
    def groups(s, pool=None):
        """pool members ordered best to worst by conference win pct, equal pct grouped."""
        pool = list(range(s.m)) if pool is None else pool
        out = {}
        for i in pool: out.setdefault(round(s.pct[i], 9), []).append(i)
        return [out[k] for k in sorted(out, reverse=True)]

def _wp(w, g): return w / g if g else None
def _norm(vals):
    """None-safe: if any team has no data the step cannot separate."""
    return None if any(v is None for v in vals) else vals

# ---- steps ---------------------------------------------------------------------------------------------------
def st_h2h2(c, t):
    a, b = t
    return [c.H[a][b], c.H[b][a]] if c.P[a][b] else None

def _mini(c, t, mode):
    n = len(t)
    allplayed = all(c.P[a][b] for a, b in combinations(t, 2))
    w = [sum(c.H[a][b] for b in t if b != a) for a in t]
    g = [sum(c.P[a][b] for b in t if b != a) for a in t]
    if mode == "rr_equal":                         # Conference USA: collective record vs the tied group; skipped if the teams played unequal numbers of group games
        return [x / y for x, y in zip(w, g)] if len(set(g)) == 1 and g[0] else None
    if mode == "rr_only_pct":                      # win pct among tied teams regardless of completeness (Sun Belt)
        return [x / y if y else 0 for x, y in zip(w, g)]
    if allplayed and mode in ("rr_beat_lost", "rr_beat", "rr_only"):
        return [x / y for x, y in zip(w, g)]
    if mode == "rr_only": return None
    # not every pair played: a team that beat all the others advances; (some policies) a team that lost to all is removed
    sc = [0.0] * n
    for k, a in enumerate(t):
        if all(c.H[a][b] > 0 for b in t if b != a): sc[k] = 1.0
        elif mode == "rr_beat_lost" and all(c.H[b][a] > 0 for b in t if b != a): sc[k] = -1.0
    return sc if any(sc) else None

def _common(c, t):
    return [o for o in range(c.m) if o not in t and all(c.P[a][o] for a in t)]

def st_common_pct(c, t):
    co = _common(c, t)
    if not co: return None
    return [_wp(sum(c.H[a][o] for o in co), sum(c.P[a][o] for o in co)) for a in t]

def _ordered(c, t, opp_filter, standing_pool=None):
    """Compare record against opponent groups, best-placed group first; first group where the teams differ decides."""
    pool = standing_pool if standing_pool is not None else [i for i in range(c.m) if i not in t]
    for grp in c.groups(pool):
        grp = [o for o in grp if o not in t]
        if not grp: continue
        if not opp_filter(grp, t): continue
        sc = [_wp(sum(c.H[a][o] for o in grp), sum(c.P[a][o] for o in grp)) for a in t]
        if len(set(sc)) > 1: return sc
    return None

def st_common_ordered(c, t):            # next-highest-placed COMMON opponent (collective if tied)
    return _ordered(c, t, lambda grp, t: all(c.P[a][o] for a in t for o in grp))
def st_ordered_any(c, t):               # next-highest-placed opponent; groups not played by every team are skipped
    return _ordered(c, t, lambda grp, t: all(sum(c.P[a][o] for o in grp) > 0 for a in t))
def st_ordered_div(c, t):               # Sun Belt: next-highest in the DIVISION standings
    pool = [i for i in range(c.m) if c.div[i] == c.div[t[0]] and i not in t]
    return _ordered(c, t, lambda grp, t: all(sum(c.P[a][o] for o in grp) > 0 for a in t), pool)

def st_opp_conf_pct(c, t):              # cumulative conference win pct of all conference opponents
    out = []
    for a in t:
        ops = [o for o in range(c.m) if c.P[a][o]]
        out.append(_wp(sum(c.W[o] for o in ops), sum(c.G[o] for o in ops)))
    return _norm(out)

def st_div_pct(c, t):                   # Sun Belt: record vs division opponents
    return _norm([_wp(sum(c.H[a][o] for o in range(c.m) if c.div[o] == c.div[a] and o != a), sum(c.P[a][o] for o in range(c.m) if c.div[o] == c.div[a] and o != a)) for a in t])
def st_common_nondiv(c, t):
    co = [o for o in range(c.m) if c.div[o] != c.div[t[0]] and all(c.P[a][o] for a in t)]
    if not co: return None
    return [_wp(sum(c.H[a][o] for o in co), sum(c.P[a][o] for o in co)) for a in t]

def st_rating(c, t): return [c.rating[a] for a in t]
def st_overall(c, t): return None if c.ovp is None else [c.ovp[a] for a in t]
def st_wins12(c, t): return None if c.wins12 is None else [c.wins12[a] for a in t]
def st_fbs(c, t): return None if c.fbsp is None else [c.fbsp[a] for a in t]
def st_apr(c, t): return None
def st_draw(c, t): return [c.draw[a] for a in t]

STEPS = {"h2h2": st_h2h2, "common_pct": st_common_pct, "common_ordered": st_common_ordered, "ordered_any": st_ordered_any,
         "ordered_div": st_ordered_div, "opp_conf_pct": st_opp_conf_pct, "div_pct": st_div_pct, "common_nondiv": st_common_nondiv,
         "rating": st_rating, "margin_proxy": st_rating, "overall_pct": st_overall, "wins12": st_wins12, "fbs_pct": st_fbs,
         "apr": st_apr, "draw": st_draw}

def run_step(c, name, t):
    if name.startswith("h2h:"): return _mini(c, t, name[4:])
    return STEPS[name](c, t)

# ---- resolution ----------------------------------------------------------------------------------------------
def resolve(c, tied, spots, rules, trace=None):
    """Return up to `spots` teams chosen from `tied` (list, in order of selection)."""
    tied = list(tied); chosen = []
    while True:
        if len(tied) <= spots: return chosen + tied
        proc = rules["two"] if len(tied) == 2 else rules["multi"]
        reverted = False
        for name in proc:
            sc = run_step(c, name, tied)
            if sc is None: continue
            best = max(sc)
            grp = [a for a, v in zip(tied, sc) if v == best]
            if len(grp) == len(tied): continue
            if trace is not None: trace.append(name)
            if len(grp) <= spots:
                chosen += grp; spots -= len(grp); tied = [a for a in tied if a not in grp]
                reverted = True; break           # remaining teams revert to the start of the procedure
            tied = grp                           # eliminate the rest, continue down the list
            if len(tied) == 2: reverted = True; break   # switch to the two-team procedure
        if not reverted and len(tied) > spots:   # draw step guarantees separation; defensive
            tied = sorted(tied, key=lambda a: -c.draw[a])[:spots]
        if spots <= 0: return chosen

def order_pair(c, pair, rules, trace=None):
    """Seed order of the two qualifiers (host / higher seed): win pct, then the two-team procedure."""
    a, b = pair
    if c.pct[a] != c.pct[b]: return [a, b] if c.pct[a] > c.pct[b] else [b, a]
    first = resolve(c, [a, b], 1, rules, trace)[0]
    return [first, b if first == a else a]

def _extended(c, pool, top):
    """ACC 'Tied Teams': best-pct teams plus teams with a different number of conference games and the same wins or same losses."""
    t1 = [i for i in pool if c.pct[i] == top]
    ext = list(t1)
    for i in pool:
        if i in t1: continue
        for j in t1:
            if c.G[i] != c.G[j] and (c.W[i] == c.W[j] or c.G[i] - c.W[i] == c.G[j] - c.W[j]):
                ext.append(i); break
    return ext

def select_ccg(c, rules, trace=None):
    """Return the title-game participants (seed order) for a conference."""
    fmt = rules["fmt"]
    if fmt == "none": return []
    if fmt == "div":
        champs = []
        for d in sorted(set(c.div)):
            pool = [i for i in range(c.m) if c.div[i] == d]
            top = max(c.pct[i] for i in pool)
            tied = [i for i in pool if c.pct[i] == top]
            champs.append(resolve(c, tied, 1, rules, trace)[0])
        a, b = champs
        if c.pct[a] != c.pct[b]: return [a, b] if c.pct[a] > c.pct[b] else [b, a]
        host = resolve(c, [a, b], 1, dict(two=rules["host"], multi=rules["host"]), trace)[0]
        return [host, b if host == a else a]
    pool = list(range(c.m)); spots = 2; chosen = []
    while spots > 0 and pool:
        top = max(c.pct[i] for i in pool)
        tier = _extended(c, pool, top) if rules.get("extended_tie_group") else [i for i in pool if c.pct[i] == top]
        if len(tier) <= spots:
            chosen += order_pair(c, tier, rules, trace) if len(tier) == 2 else tier
        else:
            chosen += resolve(c, tier, spots, rules, trace)
        spots = 2 - len(chosen); pool = [i for i in pool if i not in chosen]
    if len(chosen) == 2: chosen = order_pair(c, chosen, rules)
    return chosen
