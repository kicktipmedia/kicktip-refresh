"""CFP field and bracket for 2026-27 (official sources: collegefootballplayoff.com/news/2026/1/23/2627-format, .../2026/8/6/sc-aug-2627, NCAA.com 2026-02-03).
Official wording: the 12 schools are the conference champions of the ACC, Big Ten, Big 12 and SEC, and the HIGHEST-RANKED TEAM from the American, Conference USA, MAC,
Mountain West, Pac-12 or Sun Belt (it need not be a champion), along with the next highest-ranked teams; Notre Dame is in if ranked in the top 12 (NCAA.com calls this an automatic bid).
Seeding is straight by ranking; seeds 1-4 get byes; automatic qualifiers ranked outside the top 12 are seeded after the at-large teams.
field(): 4 power champions + best-ranked Group of 6 team (champion or not) + Notre Dame if ranked <=12 + remaining spots at-large by rank. One rule, used for prose and numbers.
rank[t] = 1-based rank by the rating proxy (committee stand-in). Returns the 12 team indices in seed order."""
P4 = ["acc", "big10", "big12", "sec"]; G6 = ["American", "usa", "midam", "mwest", "pac12", "belt"]

def _finish(rank, auto, order):
    F = [t for t in order if t in auto]
    for t in order:
        if len(F) < 12 and t not in auto: F.append(t)
    F.sort(key=lambda t: rank[t])
    return [t for t in F if rank[t] <= 12 or t not in auto] + [t for t in F if rank[t] > 12 and t in auto]

def field(rank, champs, order, nd=None, g6=()):
    """champs: {conf: team (champion or None)}; order: team indices best to worst; g6: all team indices in the six Group of 6 conferences."""
    auto = set(champs[c] for c in P4 if champs.get(c) is not None)
    if len(g6): auto.add(min(g6, key=lambda t: rank[t]))
    if nd is not None and rank[nd] <= 12: auto.add(nd)
    return _finish(rank, auto, order)

def bracket(seeds):
    """seeds: 12 teams in seed order. Returns byes (seeds 1-4) and first-round pairings (5v12, 6v11, 7v10, 8v9). Higher seed hosts."""
    return dict(byes=seeds[:4], first_round=[(seeds[4], seeds[11]), (seeds[5], seeds[10]), (seeds[6], seeds[9]), (seeds[7], seeds[8])],
                quarterfinals_if_chalk=[(seeds[0], seeds[7]), (seeds[1], seeds[6]), (seeds[2], seeds[5]), (seeds[3], seeds[4])])
