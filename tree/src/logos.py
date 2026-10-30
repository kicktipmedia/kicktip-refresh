"""ESPN school, conference and league logos (KickTip only). Spec: Creative v5c SPEC.md.
- 500 px files are byte-identical copies of the read-only cache in assets-cache/ (teamlogos/<espn id>.png, conflogos/<key>_<id>.png, ncaa-football.png).
- 32 px and 64 px files are size-only downscales of the unaltered 500 px art (PIL LANCZOS, nothing else). 
- The list of teams/conferences with a logo is GENERATED from the cache (INDEX.json: 138 teams, the 11 conference files, the one league icon), never from the mockup's used.json.
- Removal on request: delete the id's file from assets-cache (or add it to REMOVED) and rebuild; that tile then shows its initials or abbreviation fallback.
- No logo is ever used in ads, OG/share images, the favicon, the app icon or brand files."""
import os, io, json, re, shutil
from PIL import Image
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = f"{ROOT}/assets-cache"
REMOVED = set()          # ESPN team ids / conference file stems / "ncaa-football" to leave out on request
PAD = {20: 2, 24: 2, 28: 3, 32: 3, 40: 4, 48: 5, 56: 6, 64: 6, 80: 8}
CREDIT = "Team, conference and league logos courtesy of ESPN"
CREDIT_LONG = CREDIT + ". Logos are shown unaltered next to the team, conference or league name; a logo is removed on request."
CONF_ABBR = {"acc": "ACC", "American": "AAC", "big10": "B1G", "big12": "B12", "usa": "CUSA", "ind": "IND", "midam": "MAC", "mwest": "MW", "pac12": "P12", "sec": "SEC", "belt": "SBC"}

def scan():
    teams = {k for k in json.load(open(f"{CACHE}/teamlogos/INDEX.json")) if os.path.exists(f"{CACHE}/teamlogos/{k}.png") and k not in REMOVED}
    confs = {}
    for f in os.listdir(f"{CACHE}/conflogos"):
        m = re.match(r"^(.+)_(\d+)\.png$", f)
        if m and f[:-4] not in REMOVED: confs[m.group(1)] = f[:-4]
    league = os.path.exists(f"{CACHE}/ncaa-football.png") and "ncaa-football" not in REMOVED
    return teams, confs, league
TEAM_IDS, CONF_FILES, HAS_LEAGUE = scan()

def down(src, n):
    im = Image.open(src); assert im.size == (500, 500), (src, im.size)
    im = im.convert("RGBA") if im.mode != "RGBA" else im
    b = io.BytesIO(); im.resize((n, n), Image.LANCZOS).save(b, "PNG"); return b.getvalue()

def write_files(site):
    """Copy 500 px art byte-identical and write the 32/64 downscales. Returns counts."""
    out = f"{site}/assets/logos"; cnt = {"team": 0, "conf": 0, "league": 0}
    def one(src, base, stem, sizes):
        os.makedirs(f"{out}/{base}500", exist_ok=True); shutil.copyfile(src, f"{out}/{base}500/{stem}.png")
        for n in sizes:
            os.makedirs(f"{out}/{base}{n}", exist_ok=True); open(f"{out}/{base}{n}/{stem}.png", "wb").write(down(src, n))
    for tid in sorted(TEAM_IDS): one(f"{CACHE}/teamlogos/{tid}.png", "", tid, (32, 64)); cnt["team"] += 1
    for stem in sorted(CONF_FILES.values()): one(f"{CACHE}/conflogos/{stem}.png", "conf/", stem, (32, 64)); cnt["conf"] += 1
    if HAS_LEAGUE: one(f"{CACHE}/ncaa-football.png", "league/", "ncaa-football", (64,)); cnt["league"] += 1
    return cnt

def ini(n):
    w = n.replace("-", " ").split(); return n if len(n) <= 4 and n.isupper() else "".join(x[0] for x in w)[:3].upper()
def fbsz(t, size):
    inner = size - 2 * PAD[size] - 2; return max(9, min(int(size * .6), int(inner / (0.5 * max(2, len(t))))))

def tile(base, fid, size, label, lazy=False):
    """One logo tile. base: '' (team), 'conf/', 'league/'. fid None -> fallback tile (initials). No style attributes (strict CSP): size and font via classes."""
    pad = PAD[size]; im = size - 2 * pad - 2; fb = f'<b class="fb f{fbsz(label, size)}">{label}</b>'
    if fid is None: return f'<span class="lg s{size} nf" aria-hidden="true">{fb}</span>'
    if base == "league/": src, ss = f"/assets/logos/league/500/{fid}.png", ""
    elif size <= 32: src, ss = f"/assets/logos/{base}32/{fid}.png", f' srcset="/assets/logos/{base}32/{fid}.png 1x, /assets/logos/{base}64/{fid}.png 2x"'
    elif size <= 40: src, ss = f"/assets/logos/{base}64/{fid}.png", f' srcset="/assets/logos/{base}64/{fid}.png 1x, /assets/logos/{base}500/{fid}.png 2x"'
    else: src, ss = f"/assets/logos/{base}500/{fid}.png", ""
    return f'<span class="lg s{size}" aria-hidden="true"><img src="{src}"{ss} alt="" width="{im}" height="{im}" decoding="async"{" loading=\"lazy\"" if lazy else ""}>{fb}</span>'

class Marks:
    """Bound to a build: team slug/short/espn id, conference keys."""
    def __init__(self, teams, confs):
        self.t = {full: v for full, v in teams.items()}; self.confs = confs   # confs: [(key, name, slug)]
        self.by_slug = {v["slug"]: v for v in teams.values()}
        self.cslug = {k: s for k, _, s in confs}; self.cname = {k: n for k, n, _ in confs}; self.cbyname = {n: k for k, n, _ in confs}
    def team(self, full, size, lazy=False):
        v = self.t.get(full); 
        if v is None: return tile("", None, size, "FCS")
        tid = v["espn"]; return tile("", tid if tid in TEAM_IDS else None, size, ini(v["short"]), lazy)
    def conf(self, key, size, lazy=False):
        return tile("conf/", CONF_FILES.get(key), size, CONF_ABBR.get(key, key[:3].upper()), lazy)
    def league(self, size):
        return tile("league/", "ncaa-football" if HAS_LEAGUE else None, size, "NCAA")
    def js_map(self):
        t = {s: [v["espn"] if v["espn"] in TEAM_IDS else None, ini(v["short"])] for s, v in self.by_slug.items()}
        c = {s: [CONF_FILES.get(k), CONF_ABBR.get(k, k[:3].upper())] for k, _, s in self.confs}
        return json.dumps({"t": t, "c": c, "pad": PAD}, separators=(",", ":"))
