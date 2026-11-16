#!/usr/bin/env python3
"""Scores-only patch for the live KickTip site.

A full refresh 3-way-merges the live zip with the pipeline sites (tree/tools/merge3.py).
Two edits would make that merge fail and block kicktipmedia.com:

- sim-bundle.json "played" is a JSON list. merge3 conflicts when both the live
  file and the new pipeline site change a list element, and apply_data then exits 2.
- Conference standings <tbody> and the remaining-games <div class="gcl"> are
  replaced from the pipeline only when the live region still matches the old
  pipeline. Editing them skips that resolver and git merge-file conflicts.
- The same is true of a results row or a hero W-L sentence: the next build
  changes that line too, and merge-file cannot find the old text.

So this patcher does not run build.py or apply_data, and it does not rewrite
those regions. It inserts one scores card on its own line, immediately after
the stable "Skip to content" link. git merge-file keeps that line and still
applies the pipeline's score, record, and stamp updates. A second run with the
same inputs removes nothing and adds nothing.

The card carries the final score, a Final tag, the results row, and the W-L
and conference record implied by the page's current record plus the games the
page does not show yet. Model stamps (data-asof / kt-asof), pred-teams.json,
what-if files, and every other sim byte stay identical.

Usage:
  python3 tools/fast_patch.py --site DIR --tree DIR [--stamp "YYYY-MM-DD HH:MM MT"] [--check] [--out-zip ZIP]
  python3 tools/fast_patch.py --fp TREE
  python3 tools/fast_patch.py --chain --state state.json --live-id ID --canonical ID
  python3 tools/fast_patch.py --yield-check --state state.json --canonical ID --base-sha SHA
Exit 0 ok, 31 allowlist, 32 records or a byte outside the scores card changed.
--chain exits 20 when the deploy is not a fast-scores chain from --live-id.
"""
import argparse, datetime, hashlib, html, json, os, re, sys, time, unicodedata, zipfile
from zoneinfo import ZoneInfo

MT = ZoneInfo("America/Denver")
CONF_SLUG = {
    "acc": "acc", "American": "american", "big10": "big-ten", "big12": "big-12",
    "usa": "conference-usa", "ind": "independents", "midam": "mac",
    "mwest": "mountain-west", "pac12": "pac-12", "sec": "sec", "belt": "sun-belt",
}
SKIP_LINK = '<a class="skip" href="#main">Skip to content</a>'
BLOCK_RE = re.compile(r'\n<div class="card kt-fast" data-kt-fast="1">(?:(?!</div>).)*</div>')
ASOF_RE = re.compile(r'<span class="kt-asof"[^>]*>.*?</span>|data-asof="[^"]*"', re.S)
HERO_CONF = re.compile(r'Conference record (\d+)-(\d+), overall (\d+)-(\d+)')
HERO_OV = re.compile(r'Overall record (\d+)-(\d+)')
ROW_RE = re.compile(r'<tr\b.*?</tr>', re.S)
FINAL_RE = re.compile(r'<b>Final</b> &middot; ([WL]) (\d+)-(\d+)')
YIELD_TEXT = "yield: another deploy landed; next tick retries"


class PatchError(Exception):
    def __init__(self, code, msg):
        self.code = code
        super().__init__(msg)


def slugify(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower().replace("'", "")
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def short_stamp(s):
    d = datetime.datetime.strptime(s.replace(" MT", "").strip(), "%Y-%m-%d %H:%M")
    hour = d.strftime("%I").lstrip("0")
    return "%s %d, %s:%s MT" % (d.strftime("%b"), d.day, hour, d.strftime("%M %p"))


def mt_day(iso):
    u = datetime.datetime.strptime(iso, "%Y-%m-%dT%H:%MZ").replace(tzinfo=datetime.timezone.utc)
    d = u.astimezone(MT)
    return "%s %s %d" % (d.strftime("%a"), d.strftime("%b"), d.day)


def scores_fp(schedule):
    """Fingerprint of ESPN finals only. Kickoffs and spreads stay on the full run."""
    rows = []
    for g in schedule:
        if not g.get("done") or g.get("status") != "STATUS_FINAL":
            continue
        if g.get("hs") is None or g.get("as_") is None:
            continue
        rows.append((str(g["id"]), str(g["home"]), str(g["away"]), int(g["hs"]), int(g["as_"])))
    rows.sort()
    return hashlib.sha256(json.dumps(rows).encode()).hexdigest()[:16]


def load_conf(tree):
    raw = json.load(open(os.path.join(tree, "data/ref/conf_2026.json"), encoding="utf-8"))
    by_id = {}
    for name, v in raw.items():
        by_id[str(v["id"])] = dict(name=name, short=v.get("loc") or name, slug=slugify(v.get("loc") or name),
                                   conf=v.get("conf") or "", espn=str(v["id"]))
    return by_id


def load_schedule(tree):
    return json.load(open(os.path.join(tree, "data/store/schedule.json"), encoding="utf-8"))


def read_site(site):
    files = {}
    for dirpath, _, names in os.walk(site):
        for name in sorted(names):
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, site).replace(os.sep, "/")
            with open(path, "rb") as f:
                files[rel] = f.read()
    return files


def strip_block(text):
    return BLOCK_RE.sub("", text)


def decode(files, rel):
    return files[rel].decode("utf-8")


def finals(schedule):
    out = []
    for g in schedule:
        if not g.get("done") or g.get("status") != "STATUS_FINAL":
            continue
        if g.get("hs") is None or g.get("as_") is None:
            continue
        if (int(g["hs"]), int(g["as_"])) == (0, 0):
            continue
        out.append(g)
    out.sort(key=lambda g: (g.get("date") or "", str(g["id"])), reverse=True)
    return out


def team_page(slug):
    return "team/%s/index.html" % slug


def conf_page(code):
    slug = CONF_SLUG.get(code)
    return "conference/%s/index.html" % slug if slug else None


def shown_wl(html, opp_slug):
    """(letter, mine, theirs) from an official results row, ignoring the fast card."""
    body = strip_block(html)
    for row in ROW_RE.findall(body):
        if "/team/%s/" % opp_slug not in row:
            continue
        m = FINAL_RE.search(row)
        if m:
            return m.group(1), int(m.group(2)), int(m.group(3))
    return None


def hero_record(html):
    body = strip_block(html)
    m = HERO_CONF.search(body)
    if m:
        return dict(cw=int(m.group(1)), cl=int(m.group(2)), w=int(m.group(3)), l=int(m.group(4)), conf=True)
    m = HERO_OV.search(body)
    if m:
        return dict(cw=None, cl=None, w=int(m.group(1)), l=int(m.group(2)), conf=False)
    return None


def classify_game(g, files, teams):
    """Return 'new', 'correction', 'shown', or 'held'.

    A saved final whose winner would flip is held, the same rule as refresh.py
    correct_scores. The official row stays so the next full merge can still see it.
    """
    home, away = teams.get(str(g["home"])), teams.get(str(g["away"]))
    hs, as_ = int(g["hs"]), int(g["as_"])
    sides = []
    if away and home:
        sides.append((away, home, as_, hs, as_ > hs))
        sides.append((home, away, hs, as_, hs > as_))
    elif away or home:
        me = away or home
        mine, theirs = (as_, hs) if away else (hs, as_)
        opp_slug = ""
        page = team_page(me["slug"])
        if page in files:
            body = strip_block(decode(files, page))
            letter = "W" if mine > theirs else "L"
            if ("%s %d-%d" % (letter, mine, theirs)) in body:
                return "shown"
        return "new" if mine != theirs else "held"
    else:
        return "shown"
    saw = False
    for me, opp, mine, theirs, won in sides:
        page = team_page(me["slug"])
        if page not in files:
            continue
        got = shown_wl(decode(files, page), opp["slug"])
        if not got:
            continue
        saw = True
        letter, d_mine, d_theirs = got
        if letter == ("W" if won else "L") and d_mine == mine and d_theirs == theirs:
            continue
        if letter != ("W" if won else "L"):
            return "held"
        return "correction"
    if not saw:
        return "new" if hs != as_ else "held"
    return "shown"


def record_delta(files, games, teams):
    """Wins and losses to add to the hero sentence for games the page does not show yet."""
    delta = {}
    for g in games:
        if g.get("_kind") != "new":
            continue
        home, away = teams.get(str(g["home"])), teams.get(str(g["away"]))
        hs, as_ = int(g["hs"]), int(g["as_"])
        if hs == as_:
            continue
        winner = home if hs > as_ else away
        loser = away if hs > as_ else home
        conf = bool(g.get("espn_conf")) and home and away and home["conf"] and home["conf"] == away["conf"] and home["conf"] != "ind"
        for me, win in ((winner, True), (loser, False)):
            if not me:
                continue
            d = delta.setdefault(me["slug"], dict(w=0, l=0, cw=0, cl=0))
            d["w" if win else "l"] += 1
            if conf:
                d["cw" if win else "cl"] += 1
    return delta


def expected_records(files, delta, teams_by_slug):
    out = {}
    for slug, d in delta.items():
        page = team_page(slug)
        if page not in files:
            continue
        base = hero_record(decode(files, page))
        if not base:
            continue
        rec = dict(w=base["w"] + d["w"], l=base["l"] + d["l"])
        if base["conf"]:
            rec["cw"] = base["cw"] + d["cw"]
            rec["cl"] = base["cl"] + d["cl"]
        else:
            rec["cw"] = rec["cl"] = None
        out[slug] = rec
    return out


def link(team):
    if not team:
        return ""
    return '<a class="tl" href="/team/%s/">%s</a>' % (team["slug"], html.escape(team["short"]))


def describe(g, teams):
    """One score line. Away winner: 'Utah 40-39 at Arizona'. Home winner: 'BYU 28-7 vs Baylor'."""
    home, away = teams.get(str(g["home"])), teams.get(str(g["away"]))
    hn = home["short"] if home else (g.get("hn") or "Home")
    an = away["short"] if away else (g.get("an") or "Away")
    hs, as_ = int(g["hs"]), int(g["as_"])
    if g.get("neutral") or hs >= as_:
        left, ls, right, rs, where = (hn, hs, an, as_, "vs")
    else:
        left, ls, right, rs, where = (an, as_, hn, hs, "at")
    return "%s %s %d-%d %s %s" % (g["id"], left, ls, rs, where, right)


def result_row(g, teams):
    home, away = teams.get(str(g["home"])), teams.get(str(g["away"]))
    hs, as_ = int(g["hs"]), int(g["as_"])
    day = mt_day(g["date"]) if g.get("date") else ""
    where = "vs" if g.get("neutral") else "at"
    game = "%s %s %s" % (link(away) or html.escape(g.get("an") or "Away"), where, link(home) or html.escape(g.get("hn") or "Home"))
    if hs == as_:
        cell = "%s %d, %s %d" % (link(home) or html.escape(g.get("hn") or ""), hs, link(away) or html.escape(g.get("an") or ""), as_)
    elif hs > as_:
        cell = "%s %d, %s %d" % (link(home) or html.escape(g.get("hn") or ""), hs, link(away) or html.escape(g.get("an") or ""), as_)
    else:
        cell = "%s %d, %s %d" % (link(away) or html.escape(g.get("an") or ""), as_, link(home) or html.escape(g.get("hn") or ""), hs)
    note = ""
    if g.get("_kind") == "correction":
        note = " <span class=\"note\">corrected score</span>"
    return '<tr data-gid="%s"><td>%s</td><td>%s</td><td><b>Final</b> &middot; %s%s</td></tr>' % (
        html.escape(str(g["id"])), html.escape(day), game, cell, note)


def record_phrase(slug, rec, teams_by_slug):
    name = html.escape(teams_by_slug[slug]["short"])
    if rec.get("cw") is None:
        return "%s %d-%d" % (name, rec["w"], rec["l"])
    return "%s %d-%d, conference %d-%d" % (name, rec["w"], rec["l"], rec["cw"], rec["cl"])


def render_block_full(games, records, teams, teams_by_slug, stamp):
    rows = "".join(result_row(g, teams) for g in games)
    recs = "".join(record_phrase(slug, records[slug], teams_by_slug) + ". " for slug in sorted(records))
    data = ";".join("%s=%d-%d,%s" % (slug, records[slug]["w"], records[slug]["l"],
                                    "" if records[slug].get("cw") is None else "%d-%d" % (records[slug]["cw"], records[slug]["cl"]))
                    for slug in sorted(records))
    hide = ",".join('.gc[data-id="%s"],tr[data-id="%s"]' % (g["id"], g["id"]) for g in games if g.get("_kind") == "new")
    style = ("<style>%s{display:none}</style>" % hide) if hide else ""
    rec_p = ('<p class="kt-rec" data-rec="%s">%s</p>' % (html.escape(data), recs.strip())) if recs else ""
    table = ""
    if rows:
        table = '<table><thead><tr><th>Date (MT)</th><th>Game</th><th>Result</th></tr></thead><tbody>%s</tbody></table>' % rows
    text = short_stamp(stamp) if stamp else ""
    return ('<div class="card kt-fast" data-kt-fast="1"><p class="kt-scores">Scores updated %s.</p>%s%s%s</div>'
            % (html.escape(text), table, rec_p, style))


def _stamp_norm(text):
    return re.sub(r"Scores updated [^<]*\.", "Scores updated STAMP.", text)


def place(html, block):
    """Insert or replace the scores card. A new clock on the same scores is not a change."""
    found = BLOCK_RE.search(html)
    if found and block and _stamp_norm(found.group(0)) == _stamp_norm("\n" + block):
        return html
    html = BLOCK_RE.sub("", html)
    if not block:
        return html
    if SKIP_LINK in html:
        return html.replace(SKIP_LINK, SKIP_LINK + "\n" + block, 1)
    if "</body>" in html:
        return html.replace("</body>", block + "\n</body>", 1)
    return html


def pages_for(games, teams, files):
    """rel path -> games to list on that page."""
    want = {}
    def add(rel, g):
        if rel in files:
            want.setdefault(rel, []).append(g)
    for g in games:
        add("index.html", g)
        add("games/index.html", g)
        home, away = teams.get(str(g["home"])), teams.get(str(g["away"]))
        for t in (home, away):
            if t:
                add(team_page(t["slug"]), g)
        if home and away and g.get("espn_conf") and home["conf"] == away["conf"]:
            page = conf_page(home["conf"])
            if page:
                add(page, g)
    return want


def pred_sums(blob):
    doc = json.loads(blob.decode("utf-8"))
    teams = doc.get("teams") or {}
    s = {k: round(sum((v.get(k) or 0) for v in teams.values()), 2) for k in "pbwc"}
    return s, len(teams)


def json_key_paths(before, after, prefix=""):
    if type(before) is not type(after):
        yield prefix or "$"
        return
    if isinstance(before, dict):
        keys = list(before) + [k for k in after if k not in before]
        for k in keys:
            path = prefix + "." + k if prefix else k
            if k not in before or k not in after:
                yield path
            else:
                yield from json_key_paths(before[k], after[k], path)
        return
    if isinstance(before, list):
        if len(before) != len(after):
            yield prefix or "$"
            return
        for i, (x, y) in enumerate(zip(before, after)):
            yield from json_key_paths(x, y, "%s[%d]" % (prefix, i))
        return
    if before != after:
        yield prefix or "$"


def json_allowed(rel, before, after):
    """True when a JSON byte change stays inside the scores allowlist."""
    try:
        b, a = json.loads(before.decode("utf-8")), json.loads(after.decode("utf-8"))
    except ValueError:
        return False
    paths = list(json_key_paths(b, a))
    if not paths:
        return True
    base = rel.split("/")[-1]
    if base == "sim-bundle.json":
        return all(p == "played" or p.startswith("played[") or p.startswith("played.") for p in paths)
    if base == "pred-top25.json":
        return all(re.fullmatch(r"teams\[\d+\]\[[12]\]", p) for p in paths)
    return False


def check_allowlist(before, after):
    changed = sorted(rel for rel in set(before) | set(after) if before.get(rel) != after.get(rel))
    for rel in changed:
        if rel not in before or rel not in after:
            raise PatchError(31, "files added or removed: %s" % rel)
        if rel.endswith(".html"):
            continue
        if rel.endswith(".json") and json_allowed(rel, before[rel], after[rel]):
            continue
        raise PatchError(31, "file outside the scores allowlist: %s" % rel)
    for rel, blob in before.items():
        if rel.endswith("pred-teams.json") and after.get(rel) != blob:
            raise PatchError(31, "pred-teams.json changed: %s" % rel)
        if rel.startswith("data/whatif/") and after.get(rel) != blob:
            raise PatchError(31, "what-if file changed: %s" % rel)
        if rel.endswith("sim-bundle.json") and after.get(rel) != blob:
            # Allowed only when the parsed diff is the played key. This patcher does not take that path.
            if not json_allowed(rel, blob, after[rel]):
                raise PatchError(31, "sim-bundle.json changed outside played: %s" % rel)
    if "data/pred-teams.json" not in after:
        raise PatchError(32, "pred-teams.json missing")
    sums, _n = pred_sums(after["data/pred-teams.json"])
    if sums != {"p": 12.0, "b": 4.0, "w": 10.0, "c": 20.0}:
        raise PatchError(32, "pred-teams sums %s" % sums)
    for rel in changed:
        if not rel.endswith(".html"):
            continue
        old, new = decode(before, rel), decode(after, rel)
        if strip_block(old) != strip_block(new):
            raise PatchError(32, "bytes outside the scores card changed in %s" % rel)
        if ASOF_RE.findall(old) != ASOF_RE.findall(new):
            raise PatchError(32, "model as-of stamp changed in %s" % rel)


def parse_data_rec(block):
    m = re.search(r'data-rec="([^"]*)"', block)
    if not m or not m.group(1):
        return {}
    out = {}
    for part in m.group(1).split(";"):
        if not part:
            continue
        slug, _, rest = part.partition("=")
        ov, _, conf = rest.partition(",")
        w, l = ov.split("-")
        rec = dict(w=int(w), l=int(l), cw=None, cl=None)
        if conf:
            cw, cl = conf.split("-")
            rec["cw"], rec["cl"] = int(cw), int(cl)
        out[slug] = rec
    return out


def check_records(before, after, records):
    """The card's W-L equals the hero sentence plus the new finals. No frozen loss total."""
    for rel, blob in after.items():
        if not rel.endswith(".html") or blob == before.get(rel):
            continue
        text = blob.decode("utf-8")
        m = BLOCK_RE.search("\n" + text) or BLOCK_RE.search(text)
        # BLOCK_RE expects a leading newline. Search the inserted form.
        m = BLOCK_RE.search(text if text.startswith("\n") else "\n" + text)
        if not m:
            if rel in records:
                raise PatchError(32, "missing scores card on %s" % rel)
            continue
        got = parse_data_rec(m.group(0))
        # A page lists records only for teams whose games are on that page.
        # Every record it does list must match the derived record.
        for slug, rec in got.items():
            exp = records.get(slug)
            if not exp:
                raise PatchError(32, "record for %s is not derived from played games" % slug)
            if (rec["w"], rec["l"], rec["cw"], rec["cl"]) != (exp["w"], exp["l"], exp["cw"], exp["cl"]):
                raise PatchError(32, "record %s %s != %s" % (slug, rec, exp))


def patch(site_files, schedule, teams, stamp):
    games = []
    held = []
    for g in finals(schedule):
        kind = classify_game(g, site_files, teams)
        if kind == "held":
            held.append(g)
            continue
        if kind == "shown":
            continue
        g = dict(g)
        g["_kind"] = kind
        games.append(g)
    delta = record_delta(site_files, games, teams)
    teams_by_slug = {t["slug"]: t for t in teams.values()}
    records = expected_records(site_files, delta, teams_by_slug)
    # Only publish a record line for a team we could derive. Drop delta entries with no hero.
    page_games = pages_for(games, teams, site_files)
    # Pages that currently carry a card must be revisited so a caught-up score removes it.
    for rel, blob in site_files.items():
        if rel.endswith(".html") and 'data-kt-fast="1"' in blob.decode("utf-8", "replace"):
            page_games.setdefault(rel, [])
    out = dict(site_files)
    for rel, glist in page_games.items():
        # Stable order: the finals() order, filtered.
        ids = {str(g["id"]) for g in glist}
        ordered = [g for g in games if str(g["id"]) in ids]
        slugs = []
        for g in ordered:
            if g.get("_kind") != "new":
                continue
            for side in (str(g["home"]), str(g["away"])):
                t = teams.get(side)
                if t and t["slug"] in records and t["slug"] not in slugs:
                    slugs.append(t["slug"])
        recs = {s: records[s] for s in slugs}
        block = render_block_full(ordered, recs, teams, teams_by_slug, stamp) if (ordered or recs) else ""
        new = place(decode(out, rel), block)
        out[rel] = new.encode("utf-8")
    return out, games, held, records


def write_files(site, before, after):
    for rel, blob in after.items():
        if before.get(rel) == blob:
            continue
        path = os.path.join(site, rel.replace("/", os.sep))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "wb") as f:
            f.write(blob)
        os.replace(tmp, path)


def write_zip(site_files, dest):
    tmp = dest + ".tmp"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        for rel in sorted(site_files):
            info = zipfile.ZipInfo(rel, (2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            z.writestr(info, site_files[rel])
    os.replace(tmp, dest)


def chain_ok(state, live_id, canonical):
    """True when canonical is the recorded live deploy and every deploy since live_id is fast.

    state.json keeps one root: fast_base_id is the full-run deployment the fast
    cards are patched onto. A later fast publish keeps that same root, so the
    chain is the single link fast_base_id == live_id.
    """
    if not isinstance(state, dict):
        return False
    if state.get("live_id") != canonical or canonical == live_id:
        return False
    return bool(state.get("fast_base_id")) and state.get("fast_base_id") == live_id


def yield_line(state, canonical, base_sha):
    if not isinstance(state, dict) or state.get("live_id") != canonical or state.get("live_sha") != base_sha:
        return YIELD_TEXT
    return "ok"


def run_patch(site, tree, stamp, check, out_zip):
    t0 = time.perf_counter()
    teams = load_conf(tree)
    schedule = load_schedule(tree)
    if not stamp:
        logp = os.path.join(tree, "data/out/refresh_log.json")
        if os.path.isfile(logp):
            stamp = json.load(open(logp, encoding="utf-8")).get("refreshed_mt") or ""
        if not stamp:
            stamp = datetime.datetime.now(MT).strftime("%Y-%m-%d %H:%M MT")
    before = read_site(site)
    after, games, held, records = patch(before, schedule, teams, stamp)
    check_allowlist(before, after)
    check_records(before, after, records)
    changed = sorted(rel for rel in after if after[rel] != before.get(rel))
    elapsed = time.perf_counter() - t0
    print("changed=%d" % len(changed))
    print("fp %s" % scores_fp(schedule))
    print("patch_seconds %.4f" % elapsed)
    for rel in changed:
        print("FILE %s" % rel)
    for g in games:
        print("SCORE %s" % describe(g, teams))
    for g in held:
        print("HELD %s winner or 0-0 not applied" % g["id"])
    if not check:
        write_files(site, before, after)
        if out_zip:
            write_zip(after, out_zip)
    return 0 if True else 0


def main(argv):
    p = argparse.ArgumentParser(description="Patch live HTML with final scores only")
    p.add_argument("--site")
    p.add_argument("--tree")
    p.add_argument("--stamp", default="")
    p.add_argument("--check", action="store_true")
    p.add_argument("--out-zip")
    p.add_argument("--fp", help="print the scores fingerprint of this pipeline tree")
    p.add_argument("--chain", action="store_true")
    p.add_argument("--yield-check", action="store_true")
    p.add_argument("--state")
    p.add_argument("--live-id", default="")
    p.add_argument("--canonical", default="")
    p.add_argument("--base-sha", default="")
    a = p.parse_args(argv)
    if a.fp:
        print(scores_fp(load_schedule(a.fp)))
        return 0
    if a.chain or a.yield_check:
        state = json.load(open(a.state, encoding="utf-8"))
        if a.chain:
            ok = chain_ok(state, a.live_id, a.canonical)
            print("chain %s" % ("ok" if ok else "no"))
            return 0 if ok else 20
        print(yield_line(state, a.canonical, a.base_sha))
        return 0
    if not a.site or not a.tree:
        p.error("--site and --tree are required")
    try:
        return run_patch(a.site, a.tree, a.stamp, a.check, a.out_zip)
    except PatchError as e:
        print("FAST_PATCH FAIL(%d): %s" % (e.code, e), file=sys.stderr)
        return e.code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
