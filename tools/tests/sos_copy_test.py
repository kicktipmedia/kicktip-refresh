"""Offline tests for tree/src/sos_copy.py (SOS reader copy patch). python3 tools/tests/sos_copy_test.py
Fixture: assets/tb/schedule_strength.js from live Production c58f2e5f (Nov 27, 2026)."""
import os, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "tree", "src"))
import sos_copy as S
n = bad = 0
def ck(ok, what):
    global n, bad
    n += 1
    if not ok: bad += 1
    print(("PASS " if ok else "FAIL ") + what)
live = open(os.path.join(HERE, "fixtures", "schedule_strength_live_c58f2e5f.js"), encoding="utf-8").read()
p1, e1 = S.patch_js(live)
ck(e1 is None and p1 != live, "live file patches")
ck(S.MARK in p1 and p1.count("sos_copy:") == 2, "copy entries and both render branches patched")
ck('cells.push(COPY.cNone, COPY.cNone)' not in p1, "no render branch still pushes cNone")
p2, e2 = S.patch_js(p1)
ck(e2 is None and p2 == p1, "idempotent: a patched file is unchanged")
ck(S.patch_text(S.REL, live) == p1 and S.patch_text("assets/tb/team_compare.js", live) == live, "patch_text only touches schedule_strength.js")
moved = live.replace('    cNone: "None",\n', '    cNone:"None",\n')
p3, e3 = S.patch_js(moved)
ck(e3 is not None and p3 == moved, "moved anchor: file left as is, error reported")
import re
newcopy = re.findall(r'^    (?:c[A-Z]\w*|row\w*Done): "([^"]*)",$', S.COPY_NEW, re.M)[1:]   # [0] is the untouched cNone anchor line
ck(newcopy == ["No games left", "No FBS games left", "No games played", "No FBS games played", "", "Opponents left", "Opponents played"], "new copy strings: %s" % newcopy)
BANNED = r"\b(should|predict\w*|odds|pick\w*|lines?|bet\w*|wager|parlay|favored|market|None)\b"
ck(not any(re.search(BANNED, c, re.I) for c in newcopy) and not any(re.search(r"\d", c) for c in newcopy), "new copy has no banned words, no None, no digits")
with tempfile.TemporaryDirectory(prefix="sos_", dir=os.environ.get("TMPDIR")) as d:
    f = os.path.join(d, "s.js"); open(f, "w", encoding="utf-8").write(p1)
    ck(subprocess.run(["node", "--check", f]).returncode == 0, "patched file parses (node --check)")
    os.makedirs(os.path.join(d, "site", "assets", "tb")); g = os.path.join(d, "site", S.REL); open(g, "w", encoding="utf-8").write(live)
    S.patch_site(os.path.join(d, "site")); ck(open(g, encoding="utf-8").read() == p1, "patch_site writes the patched file")
    S.patch_site(os.path.join(d, "site")); ck(open(g, encoding="utf-8").read() == p1, "patch_site twice: same bytes")
# team_compare.js
tc = open(os.path.join(HERE, "fixtures", "team_compare_live_c58f2e5f.js"), encoding="utf-8").read()
t1, te = S.patch_tc(tc)
ck(te is None and t1 != tc and S.TC_MARK in t1 and t1.count("sos_copy:") == 1, "team_compare patches (copy + sched row)")
ck('"sched.mean", T[0].sched.mean, T[1].sched.mean, COPY.cNone, COPY.cNone' not in t1, "team_compare sched row no longer falls back to cNone")
ck(S.patch_tc(t1) == (t1, None), "team_compare idempotent")
ck(S.patch_text(S.TC_REL, tc) == t1, "patch_text routes team_compare.js")
moved = tc.replace(S.TC_ROW_OLD, S.TC_ROW_OLD.replace("COPY.cNone, COPY.cNone", "COPY.cNone,COPY.cNone"))
ck(S.patch_tc(moved)[0] == moved and S.patch_tc(moved)[1] is not None, "team_compare moved anchor: left as is, error reported")
tcnew = re.findall(r'^    c\w+: "([^"]*)",$', S.TC_COPY_NEW, re.M)[1:]
ck(tcnew == ["No games left", "No FBS games left"] and not any(re.search(BANNED, c, re.I) or re.search(r"\d", c) for c in tcnew), "team_compare new copy: %s" % tcnew)
with tempfile.TemporaryDirectory(prefix="sos_", dir=os.environ.get("TMPDIR")) as d:
    f = os.path.join(d, "t.js"); open(f, "w", encoding="utf-8").write(t1)
    ck(subprocess.run(["node", "--check", f]).returncode == 0, "patched team_compare parses (node --check)")
print("%d checks, %d failed" % (n, bad)); sys.exit(1 if bad else 0)
