#!/usr/bin/env python3
"""Offline tests for the fast scores path. python3 only; no network.

Covers a new final, a score correction, derived records, a second run with the
same scores, sim bytes left identical, the guard yield, the full-run rebase,
and publish_base --fast keeping results_fp.
"""
import hashlib, json, os, shutil, subprocess, sys, tempfile, textwrap, time, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import fast_patch
import classify_outcome

fail = 0

def check(ok, msg):
    global fail
    print("PASS" if ok else "FAIL", msg)
    if not ok:
        fail = 1

def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")

def pred_teams():
    teams = {}
    for slug in ("utah", "arizona", "byu", "baylor", "san-diego-state", "utah-state"):
        teams[slug] = {"n": slug, "p": 2.0, "b": 4.0 / 6, "w": 10.0 / 6, "c": 20.0 / 6}
    return {"teams": teams}

def conf():
    rows = {
        "Utah Utes": ("254", "Utah", "big12"),
        "Arizona Wildcats": ("12", "Arizona", "big12"),
        "BYU Cougars": ("252", "BYU", "big12"),
        "Baylor Bears": ("239", "Baylor", "big12"),
        "San Diego State Aztecs": ("21", "San Diego State", "pac12"),
        "Utah State Aggies": ("328", "Utah State", "pac12"),
    }
    return {name: {"id": i, "loc": loc, "sd": loc, "conf": c} for name, (i, loc, c) in rows.items()}

def game(gid, home, away, hn, an, hs, as_, week, date, conf=True):
    return dict(id=gid, week=week, date=date, home=home, away=away, hn=hn, an=an,
                hs=hs, as_=as_, done=True, neutral=False, espn_conf=conf, status="STATUS_FINAL", live=None)

def page(slug, hero, extra=""):
    return textwrap.dedent("""\
        <!doctype html>
        <a class="skip" href="#main">Skip to content</a>
        <header class="hd">header</header>
        <main id="main" data-page="team" data-team="%s">
        <section class="hero"><p>%s</p>
        %s
        </section>
        </main>
        <p>Game results last pulled <span class="kt-asof" data-asof="2026-11-14 01:00">Nov 14, 1:00 AM MT</span>. Chances recalculated from them <span class="kt-asof" data-asof="2026-11-14 01:00">Nov 14, 1:00 AM MT</span>.</p>
        </body></html>
        """) % (slug, hero, extra)

NOV14 = [
    game("401856864", "12", "254", "Arizona Wildcats", "Utah Utes", 39, 40, 11, "2026-11-15T03:30Z"),
    game("401860915", "21", "328", "San Diego State Aztecs", "Utah State Aggies", 30, 13, 11, "2026-11-15T02:30Z"),
    game("401856858", "252", "239", "BYU Cougars", "Baylor Bears", 28, 7, 11, "2026-11-15T00:00Z"),
]

def build_tree(root, schedule):
    write(root / "tree/data/ref/conf_2026.json", json.dumps(conf()))
    write(root / "tree/data/store/schedule.json", json.dumps(schedule))
    write(root / "tree/data/out/refresh_log.json", json.dumps({"refreshed_mt": "2026-11-14 00:21 MT", "errors": []}))

def build_site(root):
    site = root / "site"
    heroes = {
        "utah": "Conference record 6-0, overall 9-0. Currently 1 of 16 in the Big 12 order (conference win percentage).",
        "arizona": "Conference record 4-3, overall 6-3. Currently 4 of 16 in the Big 12 order (conference win percentage).",
        "byu": "Conference record 5-1, overall 8-1. Currently 2 of 16 in the Big 12 order (conference win percentage).",
        "baylor": "Conference record 3-3, overall 5-4. Currently 8 of 16 in the Big 12 order (conference win percentage).",
        "san-diego-state": "Conference record 4-2, overall 6-3. Currently 2 of 8 in the Pac-12 order (conference win percentage).",
        "utah-state": "Conference record 3-3, overall 5-4. Currently 4 of 8 in the Pac-12 order (conference win percentage).",
    }
    card = '<div class="gcl"><article class="gc" data-id="401856864" data-gk="arizona~utah">Utah win chance 61%</article></div>'
    for slug, hero in heroes.items():
        extra = card if slug in ("utah", "arizona") else ""
        write(site / "team" / slug / "index.html", page(slug, hero, extra))
    conf_body = '<table><tbody><tr><td class="n">1</td><td><a class="tl" href="/team/utah/">Utah</a></td><td class="n">6-0</td><td class="n">9-0</td></tr></tbody></table>'
    write(site / "conference/big-12/index.html", page("big-12", "Big 12", conf_body + card))
    write(site / "conference/pac-12/index.html", page("pac-12", "Pac-12", ""))
    write(site / "index.html", page("home", "Home"))
    write(site / "games/index.html", page("games", "Games", card))
    write(site / "data/pred-teams.json", json.dumps(pred_teams(), separators=(",", ":")))
    bundle = {"as_of": "2026-11-14 01:00 MT", "played": [[1, 2, 10, 7, 1]], "model": {"s": [1.5, 0.25], "hfa": 1.8}, "games": [{"id": "401856864"}]}
    write(site / "data/sim-bundle.json", json.dumps(bundle, separators=(",", ":")))
    write(site / "data/whatif/index.json", '{"as_of":"2026-11-14 01:00 MT","sentinel":1}\n')
    write(site / "_worker.js", "// worker sentinel\n")
    return site

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

# --- patch: three Nov 14 finals ---
t0 = time.perf_counter()
work = Path(tempfile.mkdtemp(prefix="kt-fast-"))
build_tree(work, NOV14)
site = build_site(work)
before = {p.relative_to(site).as_posix(): sha(p) for p in site.rglob("*") if p.is_file()}
proc = subprocess.run([sys.executable, str(ROOT / "tools/fast_patch.py"), "--site", str(site), "--tree", str(work / "tree"),
                       "--stamp", "2026-11-14 00:21 MT"], capture_output=True, text=True)
patch_s = time.perf_counter() - t0
out = proc.stdout
check(proc.returncode == 0, "patch exits 0 (rc=%s %s)" % (proc.returncode, proc.stderr[-300:]))
check("SCORE 401856864 Utah 40-39 at Arizona" in out, "Utah 40-39 at Arizona")
check("SCORE 401860915 San Diego State 30-13 vs Utah State" in out, "San Diego State 30-13 vs Utah State")
check("SCORE 401856858 BYU 28-7 vs Baylor" in out, "BYU 28-7 vs Baylor")
check("patch_seconds" in out, "patch reports its own timing")
utah = (site / "team/utah/index.html").read_text(encoding="utf-8")
check('data-kt-fast="1"' in utah and "Scores updated Nov 14, 12:21 AM MT." in utah, "scores card and stamp")
check("<b>Final</b>" in utah and "Utah</a> 40" in utah and "Arizona</a> 39" in utah, "final tag and score on the Utah page")
check("utah=10-0,7-0" in utah and "arizona=6-4,4-4" in utah, "records are the hero plus the new final")
check("Conference record 6-0, overall 9-0." in utah, "hero sentence left for the next full merge")
check('data-asof="2026-11-14 01:00"' in utah and utah.count("kt-asof") == 2, "model stamps untouched")
check("Utah win chance 61%" in utah, "sim win-chance bytes kept")
check('data-id="401856864"' in utah and "display:none" in utah, "stale card is hidden, not rewritten")
check(fast_patch.strip_block(utah) == fast_patch.strip_block(page(
    "utah",
    "Conference record 6-0, overall 9-0. Currently 1 of 16 in the Big 12 order (conference win percentage).",
    '<div class="gcl"><article class="gc" data-id="401856864" data-gk="arizona~utah">Utah win chance 61%</article></div>')),
    "removing the card restores the Utah page byte for byte")
conf_html = (site / "conference/big-12/index.html").read_text(encoding="utf-8")
check("<td class=\"n\">6-0</td><td class=\"n\">9-0</td>" in conf_html, "conference standings cells unchanged")
check(sha(site / "data/sim-bundle.json") == before["data/sim-bundle.json"], "sim-bundle.json byte-identical")
check(sha(site / "data/pred-teams.json") == before["data/pred-teams.json"], "pred-teams.json byte-identical")
check(sha(site / "data/whatif/index.json") == before["data/whatif/index.json"], "what-if byte-identical")
check(sha(site / "_worker.js") == before["_worker.js"], "_worker.js byte-identical")
sums, n = fast_patch.pred_sums((site / "data/pred-teams.json").read_bytes())
check(sums == {"p": 12.0, "b": 4.0, "w": 10.0, "c": 20.0}, "pred-teams sums 12/4/10/20 (%s)" % sums)

# idempotent, including a later clock
snap = {p.relative_to(site).as_posix(): p.read_bytes() for p in site.rglob("*") if p.is_file()}
proc = subprocess.run([sys.executable, str(ROOT / "tools/fast_patch.py"), "--site", str(site), "--tree", str(work / "tree"),
                       "--stamp", "2026-11-14 00:27 MT", "--check"], capture_output=True, text=True)
same = all(p.read_bytes() == snap[p.relative_to(site).as_posix()] for p in site.rglob("*") if p.is_file())
check(proc.returncode == 0 and "changed=0" in proc.stdout and same, "second run on the same scores is a no-op (changed clock)")

# merge keeps the card and takes the pipeline's new hero and stamp
s0_text = fast_patch.strip_block(utah)
live = utah
s1 = s0_text.replace("Conference record 6-0, overall 9-0.", "Conference record 7-0, overall 10-0.")
s1 = s1.replace('data-asof="2026-11-14 01:00">Nov 14, 1:00 AM MT', 'data-asof="2026-11-16 08:03">Nov 16, 8:03 AM MT')
td = Path(tempfile.mkdtemp(prefix="kt-merge-"))
(td / "a").write_text(s0_text, encoding="utf-8")
(td / "l").write_text(live, encoding="utf-8")
(td / "b").write_text(s1, encoding="utf-8")
merged = subprocess.run(["git", "merge-file", "-p", "--diff3", "-L", "live", "-L", "s0", "-L", "s1",
                         str(td / "l"), str(td / "a"), str(td / "b")], capture_output=True, text=True)
check(merged.returncode == 0 and "<<<<<<" not in merged.stdout and "kt-fast" in merged.stdout
      and "Conference record 7-0, overall 10-0." in merged.stdout and "2026-11-16 08:03" in merged.stdout,
      "merge-file keeps the scores card and applies the pipeline update (rc=%s)" % merged.returncode)

# score correction: same winner, new total. Hero record does not move. Old row stays.
corr = Path(tempfile.mkdtemp(prefix="kt-corr-"))
build_tree(corr, [game("401000001", "12", "254", "Arizona Wildcats", "Utah Utes", 24, 34, 10, "2026-11-08T03:00Z")])
# previous official row says Utah won 35-24 (away). Correction is 34-24.
old_row = '<tr><td>Sat Nov 7</td><td><a class="tl" href="/team/arizona/">Arizona</a><span class="note">Away</span></td><td><b>Final</b> &middot; W 35-24</td></tr>'
write(corr / "site/team/utah/index.html", page("utah", "Conference record 6-0, overall 9-0.", old_row))
write(corr / "site/team/arizona/index.html", page("arizona", "Conference record 4-3, overall 6-3.",
    '<tr><td>Sat Nov 7</td><td><a class="tl" href="/team/utah/">Utah</a><span class="note">Home</span></td><td><b>Final</b> &middot; L 24-35</td></tr>'))
write(corr / "site/index.html", page("home", "Home"))
write(corr / "site/data/pred-teams.json", json.dumps(pred_teams(), separators=(",", ":")))
write(corr / "site/data/sim-bundle.json", '{"as_of":"2026-11-14 01:00 MT","played":[[7,2,35,24,10]],"model":{"s":[1]}}\n')
proc = subprocess.run([sys.executable, str(ROOT / "tools/fast_patch.py"), "--site", str(corr / "site"), "--tree", str(corr / "tree"),
                       "--stamp", "2026-11-14 00:21 MT"], capture_output=True, text=True)
fixed = (corr / "site/team/utah/index.html").read_text(encoding="utf-8")
check(proc.returncode == 0 and "W 35-24" in fixed and "34" in fixed and "corrected score" in fixed, "score correction shows 34 and keeps the old row")
check("Conference record 6-0, overall 9-0." in fixed and "data-rec=" not in fixed, "a same-winner correction does not move the record")
check("played" in (corr / "site/data/sim-bundle.json").read_text(encoding="utf-8") and "[7,2,35,24,10]" in (corr / "site/data/sim-bundle.json").read_text(encoding="utf-8"),
      "played row not rewritten")

# winner flip is held
held = Path(tempfile.mkdtemp(prefix="kt-held-"))
build_tree(held, [game("401000001", "12", "254", "Arizona Wildcats", "Utah Utes", 35, 24, 10, "2026-11-08T03:00Z")])
write(held / "site/team/utah/index.html", page("utah", "Conference record 6-0, overall 9-0.", old_row))
write(held / "site/team/arizona/index.html", page("arizona", "Conference record 4-3, overall 6-3.", ""))
write(held / "site/data/pred-teams.json", json.dumps(pred_teams(), separators=(",", ":")))
raw = (held / "site/team/utah/index.html").read_bytes()
proc = subprocess.run([sys.executable, str(ROOT / "tools/fast_patch.py"), "--site", str(held / "site"), "--tree", str(held / "tree"),
                       "--stamp", "2026-11-14 00:21 MT", "--check"], capture_output=True, text=True)
check(proc.returncode == 0 and "changed=0" in proc.stdout and "HELD 401000001" in proc.stdout and (held / "site/team/utah/index.html").read_bytes() == raw,
      "a winner flip is held and the page is unchanged")

# allowlist: played-only JSON is allowed; an as-of or pred-teams change is not
b = json.dumps({"as_of": "t", "played": [[1, 2, 3, 4, 5]], "model": {"s": [1]}}).encode()
a = json.dumps({"as_of": "t", "played": [[1, 2, 9, 4, 5]], "model": {"s": [1]}}).encode()
check(fast_patch.json_allowed("data/sim-bundle.json", b, a), "played-only JSON diff is allowlisted")
a2 = json.dumps({"as_of": "other", "played": [[1, 2, 3, 4, 5]], "model": {"s": [1]}}).encode()
check(not fast_patch.json_allowed("data/sim-bundle.json", b, a2), "as_of JSON diff is rejected")
top_b = json.dumps({"asof": "Nov 14", "teams": [["utah", 9, 0, 1.5]]}).encode()
top_a = json.dumps({"asof": "Nov 14", "teams": [["utah", 10, 0, 1.5]]}).encode()
check(fast_patch.json_allowed("data/pred-top25.json", top_b, top_a), "pred-top25 win/loss diff is allowlisted")
try:
    bad_before = {"data/pred-teams.json": b'{"teams":{"a":{"p":12,"b":4,"w":10,"c":20}}}', "_worker.js": b"same"}
    bad_after = {"data/pred-teams.json": b'{"teams":{"a":{"p":11,"b":4,"w":10,"c":20}}}', "_worker.js": b"same"}
    fast_patch.check_allowlist(bad_before, bad_after)
    check(False, "pred-teams change must raise")
except fast_patch.PatchError as e:
    check(e.code == 31, "pred-teams change is exit 31 (%s)" % e)

check(fast_patch.chain_ok({"live_id": "fast1", "fast_base_id": "full0"}, "full0", "fast1"), "fast chain matches the full-run root")
check(not fast_patch.chain_ok({"live_id": "other", "fast_base_id": "someone"}, "full0", "other"), "a non-fast deploy is not a chain")
check(fast_patch.yield_line({"live_id": "L", "live_sha": "abc"}, "L", "abc") == "ok", "guard ok when the base is unchanged")
check(fast_patch.yield_line({"live_id": "L", "live_sha": "abc"}, "OTHER", "abc").startswith("yield:"), "guard yields when canonical moved")

# guard yield with mock curl and git
gmock = Path(tempfile.mkdtemp(prefix="kt-guard-"))
state = {"live_id": "live-1", "live_sha": "abc", "fast_base_id": ""}
(gmock / "state.json").write_text(json.dumps(state), encoding="utf-8")
(gmock / "curl").write_text("#!/bin/bash\npython3 -c 'import json;print(json.dumps({\"result\":{\"canonical_deployment\":{\"id\":\"other-deploy\"}}}))'\n", encoding="utf-8")
(gmock / "git").write_text("#!/bin/bash\nif [ \"$1\" = show ]; then cat \"%s/state.json\"; exit 0; fi\nexit 0\n" % gmock, encoding="utf-8")
os.chmod(gmock / "curl", 0o755)
os.chmod(gmock / "git", 0o755)
gy = subprocess.run(["bash", str(ROOT / "tools/fast_guard.sh"), "--base-sha", "abc"], capture_output=True, text=True,
                    env=dict(os.environ, KT_CURL=str(gmock / "curl"), KT_GIT=str(gmock / "git"), CLOUDFLARE_API_TOKEN="t"))
check(gy.returncode == 0 and gy.stdout.strip() == "yield: another deploy landed; next tick retries",
      "guard yield path (mock curl/git): %r rc=%s" % (gy.stdout.strip(), gy.returncode))
(gmock / "state.json").write_text(json.dumps({"live_id": "live-1", "live_sha": "abc"}), encoding="utf-8")
(gmock / "curl").write_text("#!/bin/bash\npython3 -c 'import json;print(json.dumps({\"result\":{\"canonical_deployment\":{\"id\":\"live-1\"}}}))'\n", encoding="utf-8")
okg = subprocess.run(["bash", str(ROOT / "tools/fast_guard.sh"), "--base-sha", "abc"], capture_output=True, text=True,
                     env=dict(os.environ, KT_CURL=str(gmock / "curl"), KT_GIT=str(gmock / "git"), CLOUDFLARE_API_TOKEN="t"))
check(okg.returncode == 0 and okg.stdout.strip() == "ok", "guard ok path (mock curl/git)")

# full-run rebase with mock curl, git, wrangler, apply, suite
reb = Path(tempfile.mkdtemp(prefix="kt-rebase-"))
build_tree(reb, NOV14)
base_site = reb / "base-site"
# The zip the fast deploy already published: scores not yet in the hero, so the overlay still adds the card.
build_site(reb)
shutil.move(str(reb / "site"), str(base_site))
zpath = reb / "base.zip"
with zipfile.ZipFile(zpath, "w") as z:
    for p in base_site.rglob("*"):
        if p.is_file():
            z.write(p, p.relative_to(base_site).as_posix())
zsha = hashlib.sha256(zpath.read_bytes()).hexdigest()
(reb / "remote-state.json").write_text(json.dumps({
    "live_id": "fast-deploy", "live_sha": zsha, "fast_base_id": "full-run",
    "results_fp": "keep-me", "as_of": "2026-11-14 01:00 MT"}), encoding="utf-8")
bin_dir = reb / "bin"
bin_dir.mkdir()
(bin_dir / "curl").write_text("#!/bin/bash\npython3 -c 'import json;print(json.dumps({\"result\":{\"canonical_deployment\":{\"id\":\"fast-deploy\"}}}))'\n", encoding="utf-8")
(bin_dir / "git").write_text("#!/bin/bash\nif [ \"$1\" = show ]; then cat \"%s/remote-state.json\"; exit 0; fi\nexit 0\n" % reb, encoding="utf-8")
(bin_dir / "wrangler").write_text("#!/bin/bash\necho https://abcdef01.kicktip.pages.dev\n", encoding="utf-8")
(bin_dir / "bytecmp").write_text("#!/bin/bash\nexit 0\n", encoding="utf-8")
(bin_dir / "suite").write_text("#!/bin/bash\necho SUITE_DONE fail=0\n", encoding="utf-8")
(bin_dir / "refresh").write_text("#!/bin/bash\nexit 0\n", encoding="utf-8")
apply = bin_dir / "apply"
apply.write_text(textwrap.dedent("""\
    #!/bin/bash
    OUT=""; SITE=""
    while [ $# -gt 0 ]; do
      case $1 in --out) OUT=$2; shift 2;; --site-out) SITE=$2; shift 2;; *) shift;; esac
    done
    rm -rf "$SITE"; mkdir -p "$SITE"
    cp -a "%s/." "$SITE/"
    rm -f "$OUT"
    (cd "$SITE" && python3 -c 'import os,zipfile,sys
    z=zipfile.ZipFile(sys.argv[1],"w");
    [z.write(os.path.join(r,f), os.path.relpath(os.path.join(r,f), sys.argv[2])) for r,ds,fs in os.walk(sys.argv[2]) for f in fs]' "$OUT" "$SITE")
    """) % base_site, encoding="utf-8")
for p in bin_dir.iterdir():
    os.chmod(p, 0o755)
rd = reb / "run"
rd.mkdir()
(rd / "s0").mkdir()
(rd / "s1").mkdir()
env = dict(os.environ, KT_CURL=str(bin_dir / "curl"), KT_GIT=str(bin_dir / "git"), KT_WRANGLER=str(bin_dir / "wrangler"),
           KT_BYTECMP=str(bin_dir / "bytecmp"), KT_SUITE=str(bin_dir / "suite"), KT_REFRESH=str(bin_dir / "refresh"),
           KT_APPLY=str(apply), KT_REBASE_ZIP=str(zpath), KT_SUMS_MIN="1", CLOUDFLARE_API_TOKEN="t")
rb = subprocess.run(["bash", str(ROOT / "tools/fast_rebase.sh"), "--canonical", "fast-deploy", "--live-id", "full-run",
                     "--run-dir", str(rd), "--tree", str(reb / "tree"), "--s0", str(rd / "s0"), "--s1", str(rd / "s1")],
                    capture_output=True, text=True, env=env)
reb_doc = json.loads((rd / "rebase.json").read_text(encoding="utf-8")) if (rd / "rebase.json").is_file() else {}
overlay = (rd / "deploy/team/utah/index.html").read_text(encoding="utf-8") if (rd / "deploy/team/utah/index.html").is_file() else ""
check(rb.returncode == 0 and reb_doc.get("canonical") == "fast-deploy" and "kt-fast" in overlay,
      "full-run rebase path (mock curl/wrangler) rc=%s %s" % (rb.returncode, (rb.stderr or rb.stdout)[-400:]))
check("401856864" in overlay and "Utah win chance 61%" in overlay, "rebase overlay keeps sim bytes and adds the final")
# not a fast chain -> exit 20, wrangler not required
(reb / "remote-state.json").write_text(json.dumps({"live_id": "feature", "live_sha": zsha}), encoding="utf-8")
rb2 = subprocess.run(["bash", str(ROOT / "tools/fast_rebase.sh"), "--canonical", "feature", "--live-id", "full-run",
                      "--run-dir", str(rd), "--tree", str(reb / "tree"), "--s0", str(rd / "s0"), "--s1", str(rd / "s1")],
                     capture_output=True, text=True, env=env)
check(rb2.returncode == 20, "rebase exits 20 when the deploy is not a fast chain (rc=%s)" % rb2.returncode)

# publish_base --fast keeps results_fp and the fast root
pub = Path(tempfile.mkdtemp(prefix="kt-pub-"))
mock = pub / "bin"
mock.mkdir()
(mock / "curl").write_text("#!/bin/bash\npython3 -c 'import json,os;print(json.dumps({\"result\":{\"canonical_deployment\":{\"id\":os.environ[\"MOCK_CANON\"]}}}))'\n", encoding="utf-8")
(mock / "gh").write_text("#!/bin/bash\nexit 0\n", encoding="utf-8")
os.chmod(mock / "curl", 0o755)
os.chmod(mock / "gh", 0o755)
bare = pub / "remote.git"
subprocess.check_call(["git", "init", "-q", "-b", "main", "--bare", str(bare)])
repo = pub / "repo"
subprocess.check_call(["git", "init", "-q", "-b", "main", str(repo)])
subprocess.check_call(["git", "-C", str(repo), "remote", "add", "origin", str(bare)])
# copy the scripts the publisher runs
shutil.copy(ROOT / "tools/publish_base.sh", repo / "publish_base.sh")
os.chmod(repo / "publish_base.sh", 0o755)
state0 = {"live_id": "full-run", "live_sha": "old", "results_fp": "results-stay", "as_of": "2026-11-14 01:00 MT",
          "s0_pipeline_site": "base/s0/site", "lines_fp": "lines-stay", "lines_epoch": 5, "zip_path": "base/kicktip-site.zip"}
(repo / "state.json").write_text(json.dumps(state0, indent=1) + "\n", encoding="utf-8")
(repo / "note.txt").write_text("v1\n", encoding="utf-8")
subprocess.check_call(["git", "-C", str(repo), "add", "state.json", "note.txt"])
subprocess.check_call(["git", "-C", str(repo), "-c", "user.name=kicktipmedia", "-c", "user.email=kicktipmedia@users.noreply.github.com", "commit", "-qm", "init"])
subprocess.check_call(["git", "-C", str(repo), "push", "-q", "-u", "origin", "main"])
z = repo / "ship.zip"
z.write_bytes(b"zip-bytes")
env = dict(os.environ, PATH=str(mock) + os.pathsep + os.environ["PATH"], MOCK_CANON="fast-1", CLOUDFLARE_API_TOKEN="t",
           GIT_AUTHOR_NAME="kicktipmedia", GIT_AUTHOR_EMAIL="kicktipmedia@users.noreply.github.com",
           GIT_COMMITTER_NAME="kicktipmedia", GIT_COMMITTER_EMAIL="kicktipmedia@users.noreply.github.com")
# publish_base.sh lives in tools/ and cds to its parent. Run a copy from a tools/ dir inside the repo.
(repo / "tools").mkdir()
shutil.copy(ROOT / "tools/publish_base.sh", repo / "tools/publish_base.sh")
os.chmod(repo / "tools/publish_base.sh", 0o755)
pub1 = subprocess.run(["bash", "tools/publish_base.sh", str(z), "fast-1", "--fast", "--scores-fp", "fp-fast", "--scores-as-of", "2026-11-14 00:21 MT"],
                      cwd=repo, capture_output=True, text=True, env=env)
st = json.loads((repo / "state.json").read_text(encoding="utf-8"))
check(pub1.returncode == 0 and st["results_fp"] == "results-stay" and st["as_of"] == "2026-11-14 01:00 MT"
      and st["lines_fp"] == "lines-stay" and st["lines_epoch"] == 5 and st["s0_pipeline_site"] == "base/s0/site"
      and st["scores_fp"] == "fp-fast" and st["scores_as_of"] == "2026-11-14 00:21 MT"
      and st["fast_base_id"] == "full-run" and st["live_id"] == "fast-1",
      "publish_base --fast keeps results_fp (rc=%s %s)" % (pub1.returncode, (pub1.stderr or pub1.stdout)[-300:]))
env["MOCK_CANON"] = "fast-2"
pub2 = subprocess.run(["bash", "tools/publish_base.sh", str(z), "fast-2", "--fast", "--scores-fp", "fp-fast-2", "--scores-as-of", "2026-11-14 00:30 MT"],
                      cwd=repo, capture_output=True, text=True, env=env)
st = json.loads((repo / "state.json").read_text(encoding="utf-8"))
check(pub2.returncode == 0 and st["fast_base_id"] == "full-run" and st["live_id"] == "fast-2" and st["results_fp"] == "results-stay",
      "a second fast publish keeps the full-run root")
env["MOCK_CANON"] = "full-2"
pub3 = subprocess.run(["bash", "tools/publish_base.sh", str(z), "full-2", "--fp", "results-new", "--as-of", "2026-11-16 08:03 MT",
                       "--scores-fp", "fp-full", "--scores-as-of", "2026-11-16 08:03 MT"],
                      cwd=repo, capture_output=True, text=True, env=env)
st = json.loads((repo / "state.json").read_text(encoding="utf-8"))
check(pub3.returncode == 0 and "fast_base_id" not in st and st["scores_fp"] == "fp-full" and st["results_fp"] == "results-new",
      "a full publish clears fast_base_id and sets scores_fp")

# reporter: fast exits, no hold, no FREEZE
d, envr = None, None
def fresh():
    d = Path(tempfile.mkdtemp(prefix="kt-fast-rep-"))
    (d / "summary.md").write_text("", encoding="utf-8")
    (d / "env.txt").write_text("", encoding="utf-8")
    (d / "output.txt").write_text("", encoding="utf-8")
    e = dict(os.environ, GITHUB_STEP_SUMMARY=str(d / "summary.md"), GITHUB_ENV=str(d / "env.txt"),
             GITHUB_OUTPUT=str(d / "output.txt"), KT_ROOT=str(d), KT_REF_NAME="main",
             GITHUB_EVENT_NAME="schedule", KT_DEPLOY_TARGET="production")
    return d, e
d, e = fresh()
r = subprocess.run([sys.executable, str(ROOT / "tools/report_outcome.py"), "--workflow", "fast", "--exit", "11",
                    "--step", "Stop if frozen", "--reason", "FREEZE present"], capture_output=True, text=True, env=e)
env_txt = (d / "env.txt").read_text(encoding="utf-8")
check(r.returncode == 0 and "KT_HOLD" not in env_txt and "KT_COMMIT_FREEZE" not in env_txt and "KT_HALT=1" in env_txt,
      "fast FREEZE is green, no hold, no FREEZE commit")
d, e = fresh()
r = subprocess.run([sys.executable, str(ROOT / "tools/report_outcome.py"), "--workflow", "fast", "--exit", "31",
                    "--step", "Fast scores", "--reason", "allowlist"], capture_output=True, text=True, env=e)
check(r.returncode == 31 and "KT_HOLD" not in (d / "env.txt").read_text(encoding="utf-8"), "fast allowlist is red and does not hold")
d, e = fresh()
r = subprocess.run([sys.executable, str(ROOT / "tools/report_outcome.py"), "--workflow", "fast", "--exit", "22",
                    "--step", "Fast scores", "--reason", "pages.dev mismatch after rollback"], capture_output=True, text=True, env=e)
check(r.returncode == 22 and "KT_COMMIT_FREEZE" not in (d / "env.txt").read_text(encoding="utf-8"), "fast exit 22 is red and does not commit FREEZE")
d, e = fresh()
r = subprocess.run([sys.executable, str(ROOT / "tools/report_outcome.py"), "--workflow", "fast", "--kind", "install", "--exit", "100",
                    "--step", "Install wrangler", "--reason", "dns"], capture_output=True, text=True, env=e)
check(r.returncode == 0 and "KT_HALT=1" in (d / "env.txt").read_text(encoding="utf-8"), "fast install blip is green")
for code, job in ((0, "green"), (10, "green"), (13, "green"), (18, "green"), (12, "red"), (21, "red"), (32, "red"), (99, "red")):
    got = classify_outcome.classify(code, "main", "schedule", "production", False, "exit", "fast")
    check(got["job"] == job and got["hold"] is False and got["commit_freeze"] is False, "fast exit %s is %s" % (code, job))
check("hold/failed" not in (ROOT / "tools/report_outcome.py").read_text(encoding="utf-8"), "reporter still never writes hold/failed")

# workflow wiring
wf = (ROOT / ".github/workflows/fast-scores.yml").read_text(encoding="utf-8")
check('cron: "*/5 16-23 * * 6"' in wf and 'cron: "*/5 0-7 * * 0"' in wf, "saturday cron is every 5 minutes")
check("vars.KT_FAST == 'on'" in wf and "KT_SCHEDULE" not in wf, "the job runs only when KT_FAST is on")
check("group: kt-fast" in wf and "cancel-in-progress: false" in wf and "queue:" not in wf, "kt-fast does not cancel an in-progress run and a newer tick can replace a pending one")
check("timeout-minutes: 15" in wf and "wrangler@3.114.17" in wf and "key: wrangler-3.114.17" in wf, "15 minute timeout and cached wrangler 3.114.17")
check("pull_request" not in wf and "workflow_dispatch" in wf and "production | preview | none" in wf.replace("\n", " ") or "options: [production, preview, none]" in wf,
      "dispatch targets and no pull_request trigger")
check("FREEZE" in wf and "KT_COMMIT_FREEZE" not in wf and "hold/failed" not in wf, "FREEZE stops the run and is not committed")
check("--workflow fast" in wf and "tools/fast_scores.sh --gate" in wf and "--skip-fetch" in wf, "gate then one deploy, classified as the fast workflow")
check("refresh" not in wf.split("concurrency:", 1)[1].split("permissions:", 1)[0], "the concurrency group is not refresh")

# replay script on a frozen inputs tarball and the base zip
import tarfile
inp = work / "inputs.tgz"
with tarfile.open(inp, "w:gz") as tar:
    for rel in ("data/store/schedule.json", "data/ref/conf_2026.json", "data/out/refresh_log.json"):
        tar.add(work / "tree" / rel, arcname=rel)
# zip the UNPATCHED site. build_site was patched in place; rebuild a clean one.
clean = Path(tempfile.mkdtemp(prefix="kt-clean-"))
build_tree(clean, NOV14)
clean_site = build_site(clean)
cz = clean / "base.zip"
with zipfile.ZipFile(cz, "w") as z:
    for p in clean_site.rglob("*"):
        if p.is_file():
            z.write(p, p.relative_to(clean_site).as_posix())
t_replay = time.perf_counter()
rp = subprocess.run(["bash", str(ROOT / "tools/fast_replay.sh"), str(inp), str(cz)], capture_output=True, text=True)
replay_s = time.perf_counter() - t_replay
check(rp.returncode == 0 and "Utah 40-39 at Arizona" in rp.stdout and "San Diego State 30-13 vs Utah State" in rp.stdout
      and "BYU 28-7 vs Baylor" in rp.stdout and "FILE team/utah/index.html" in rp.stdout,
      "fast_replay.sh prints the Nov 14 score lines (rc=%s)" % rp.returncode)

# local gate timing: fingerprint plus an in-memory check on this fixture
t_gate = time.perf_counter()
fp = fast_patch.scores_fp(json.loads((work / "tree/data/store/schedule.json").read_text(encoding="utf-8")))
files = fast_patch.read_site(str(site))
_after, _games, _held, _recs = fast_patch.patch(files, json.loads((work / "tree/data/store/schedule.json").read_text(encoding="utf-8")),
                                                fast_patch.load_conf(str(work / "tree")), "2026-11-14 00:21 MT")
gate_s = time.perf_counter() - t_gate
print("TIMING patch_first %.3fs replay %.3fs gate_check %.3fs fp %s" % (patch_s, replay_s, gate_s, fp))
check(gate_s < 5 and patch_s < 5, "gate and patch are well under a minute on this fixture")

print("SUITE_DONE fail=%d" % fail)
sys.exit(fail)
