"""Offline polls refresh tests. No network except one connection-refused to 127.0.0.1:9.

python3 tests/poll_refresh_test.py
Newer week, same-week no-op, older week, timeout, HTTP error, partial list, unmapped team,
one poll good and the other bad. Fixtures only; this does not call ESPN.
"""
import json, os, shutil, subprocess, sys, tempfile, urllib.error
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
import poll_refresh as P

HERE = os.path.dirname(os.path.abspath(__file__))
TREE = os.path.dirname(HERE)
FIX = os.path.join(HERE, "fixtures")
res = {"n": 0, "failures": []}

def ok(name, cond, detail=""):
    res["n"] += 1
    if not cond:
        res["failures"].append("%s %s" % (name, detail))
        print("FAIL", name, str(detail)[:500])

IDS = [(str(i), "team-%d" % i) for i in range(1, 26)]
IDMAP = {t: s for t, s in IDS}

def ranks(bad=None):
    rows = []
    for i, (tid, _s) in enumerate(IDS, start=1):
        if bad == "partial" and i == 25:
            continue
        use, rec, cur = tid, "8-1", i
        if bad == "unmapped" and i == 7:
            use = "999999"
        if bad == "malformed" and i == 4:
            rec = "nope"
        if bad == "bad-rank" and i == 3:
            cur = True
        rows.append({"current": cur, "recordSummary": rec, "team": {"id": use, "location": "Team %d" % i}})
    return rows

def feed(ap_week, coaches_week, ap_pub, coaches_pub, ap_bad=None, coaches_bad=None, drop=None):
    rankings = []
    if drop != "ap":
        rankings.append({"type": "ap", "lastUpdated": ap_pub, "date": ap_pub, "occurrence": {"value": str(ap_week)}, "ranks": ranks(ap_bad)})
    if drop != "coaches":
        rankings.append({"type": "usa", "lastUpdated": coaches_pub, "date": coaches_pub, "occurrence": {"value": str(coaches_week)}, "ranks": ranks(coaches_bad)})
    return {"rankings": rankings}

def page(week, pub, pub2=None):
    merged, changed, logs = P.apply_feed({"polls": {}}, IDMAP, feed(week, week, pub, pub2 or pub))
    ok("fixture page built", changed and merged["polls"]["ap"]["released"] and len(merged["polls"]["ap"]["ranks"]) == 25, logs)
    return merged

LIVE = page(10, "2026-11-01T18:00Z", "2026-11-01T17:00Z")

def test_newer_week():
    got, changed, logs = P.refresh(LIVE, IDMAP, feed=feed(11, 11, "2026-11-08T22:15Z", "2026-11-08T21:08Z"))
    ok("newer week updates both polls", changed and got["polls"]["ap"]["week"] == "11" and got["polls"]["coaches"]["week"] == "11", logs)
    ok("newer week keeps rank shape", got["polls"]["ap"]["ranks"][0] == [1, "team-1", "8-1"] and got["polls"]["ap"]["asof"] == "Nov 8", got["polls"]["ap"])
    ok("newer week log names the move", any("AP Top 25 updated" in s and "week 11" in s for s in logs) and not any(s.startswith("WARNING") for s in logs), logs)

def test_same_week_noop():
    src = page(11, "2026-11-08T22:15Z", "2026-11-08T21:08Z")
    raw = json.dumps(src, separators=(",", ":")).encode()
    got, changed, logs = P.refresh(src, IDMAP, feed=feed(11, 11, "2026-11-08T22:15Z", "2026-11-08T21:08Z"))
    ok("same week same pub is a no-op", not changed and got == src, logs)
    s0, s1, ch, plogs = P.plan(raw, raw)
    ok("same bytes stay the live baseline", not ch and s0 == raw and s1 == raw, plogs)

def test_same_week_newer_pub():
    src = page(11, "2026-11-08T18:00Z", "2026-11-08T21:08Z")
    got, changed, logs = P.refresh(src, IDMAP, feed=feed(11, 11, "2026-11-08T22:15Z", "2026-11-08T21:08Z"))
    ok("same week newer pub updates only AP", changed and got["polls"]["ap"]["pub"] == "2026-11-08T22:15Z" and got["polls"]["coaches"] == src["polls"]["coaches"], logs)

def test_older_week():
    src = page(11, "2026-11-08T22:15Z", "2026-11-08T21:08Z")
    got, changed, logs = P.refresh(src, IDMAP, feed=feed(10, 10, "2026-11-01T22:15Z", "2026-11-01T21:08Z"))
    ok("older week is refused", not changed and got == src, logs)
    ok("older week says so", any("older than live week 11" in s for s in logs), logs)

def test_older_pub_same_week():
    src = page(11, "2026-11-08T22:15Z", "2026-11-08T21:08Z")
    got, changed, logs = P.refresh(src, IDMAP, feed=feed(11, 11, "2026-11-08T20:00Z", "2026-11-08T19:00Z"))
    ok("older pub on the same week is refused", not changed and got == src, logs)

def test_timeout_and_http():
    src = page(11, "2026-11-08T22:15Z")
    for kind in ("timeout", "HTTP 503", "unreachable"):
        got, changed, logs = P.refresh(src, IDMAP, error=kind)
        ok("%s keeps the last good file" % kind, not changed and got is src and any("WARNING" in s and kind in s and "last good" in s for s in logs), logs)
    got, changed, logs = P.refresh(src, IDMAP, feed={"rankings": "nope"})
    ok("malformed feed keeps the last good file", not changed and got is src and any("malformed" in s and "WARNING" in s for s in logs), logs)
    ok("timeout classifies", P.classify(TimeoutError("timed out")) == "timeout")
    ok("url timeout classifies", P.classify(urllib.error.URLError(TimeoutError())) == "timeout")
    ok("forced timeout classifies", P.classify(P.PollFetchError("timeout")) == "timeout")

def test_localhost_refused():
    feed, err = P.fetch_rankings("http://127.0.0.1:9/rankings", timeout=2, tries=1)
    ok("unreachable host returns no feed", feed is None and err is not None and P.classify(err) == "unreachable", err)

def test_partial_malformed_unmapped():
    src = page(10, "2026-11-01T18:00Z")
    cases = (("partial", "partial list"), ("malformed", "malformed entry"), ("unmapped", "unmapped ESPN team id 999999"), ("bad-rank", "malformed entry"))
    for bad, phrase in cases:
        got, changed, logs = P.refresh(src, IDMAP, feed=feed(11, 11, "2026-11-08T22:15Z", "2026-11-08T21:08Z", ap_bad=bad, coaches_bad=bad))
        ok("%s keeps both polls" % bad, not changed and got == src and sum(1 for s in logs if "rejected" in s and phrase in s) == 2, logs)

def test_one_good_one_bad():
    src = page(10, "2026-11-01T18:00Z", "2026-11-01T17:00Z")
    got, changed, logs = P.refresh(src, IDMAP, feed=feed(12, 12, "2026-11-15T22:15Z", "2026-11-15T21:08Z", coaches_bad="partial"))
    ok("good AP updates while bad Coaches is kept", changed and got["polls"]["ap"]["week"] == "12" and got["polls"]["coaches"] == src["polls"]["coaches"], logs)
    ok("coaches warning is independent", any("Coaches Poll rejected" in s and "partial list" in s for s in logs) and any("AP Top 25 updated" in s for s in logs), logs)
    got, changed, logs = P.refresh(src, IDMAP, feed=feed(12, 11, "2026-11-15T22:15Z", "2026-11-08T21:08Z"))
    ok("different weeks both stay when each is newer than its own live copy", changed and got["polls"]["ap"]["week"] == "12" and got["polls"]["coaches"]["week"] == "11", logs)
    # live already on mixed weeks: an older coaches feed must not wipe the newer AP, and must not rewind coaches
    mixed = got
    again, changed2, logs2 = P.refresh(mixed, IDMAP, feed=feed(12, 9, "2026-11-15T22:15Z", "2026-11-01T21:08Z"))
    ok("older coaches week does not discard the current AP or the last good coaches", not changed2 and again == mixed, logs2)

def test_missing_poll_keeps_the_other():
    src = page(10, "2026-11-01T18:00Z")
    got, changed, logs = P.refresh(src, IDMAP, feed=feed(11, 11, "2026-11-08T22:15Z", "2026-11-08T21:08Z", drop="coaches"))
    ok("missing coaches keeps coaches and updates AP", changed and got["polls"]["ap"]["week"] == "11" and got["polls"]["coaches"] == src["polls"]["coaches"], logs)

def test_plan_does_not_move_backward():
    src = page(11, "2026-11-08T22:15Z", "2026-11-08T21:08Z")
    raw = json.dumps(src, separators=(",", ":"), ensure_ascii=False).encode()
    older = json.loads(raw)
    older["polls"]["ap"] = dict(older["polls"]["ap"], week="9", pub="2026-10-25T18:00Z", asof="Oct 25")
    older["polls"]["coaches"]["ranks"] = older["polls"]["coaches"]["ranks"][:10]
    s0, s1, changed, logs = P.plan(raw, json.dumps(older).encode())
    ok("plan refuses an older week and a partial coaches list", not changed and s0 == raw and s1 == raw, logs)
    newer = json.loads(raw)
    newer["polls"]["ap"] = dict(newer["polls"]["ap"], week="12", pub="2026-11-15T22:15Z", asof="Nov 15")
    s0, s1, changed, logs = P.plan(raw, json.dumps(newer).encode())
    ok("plan takes a newer AP and keeps coaches", changed and s0 == raw and json.loads(s1)["polls"]["ap"]["week"] == "12" and json.loads(s1)["polls"]["coaches"] == src["polls"]["coaches"], logs)

def test_week11_fixture_matches_live_shape():
    ids = P.load_ids()
    live = json.load(open(os.path.join(FIX, "polls_week11.json"), encoding="utf-8"))
    feed = json.load(open(os.path.join(FIX, "espn_rankings_week11.json"), encoding="utf-8"))
    got, changed, logs = P.refresh(live, ids, feed=feed)
    ok("week 11 fixture is a no-op against the live file", not changed and got == live, logs)
    ok("week 11 fixture log is a no-op", any("no-op" in s or "unchanged" in s for s in logs) and not any(s.startswith("WARNING") for s in logs), logs)
    # every ranked id in the fixture maps; this is the same conf file the refresh uses
    missing = []
    for r in feed["rankings"]:
        for row in r["ranks"]:
            if str(row["team"]["id"]) not in ids:
                missing.append(row["team"]["id"])
    ok("fixture teams all map", not missing, missing)
    raw = open(os.path.join(FIX, "polls_week11.json"), "rb").read()
    s0, s1, changed, logs = P.plan(raw, json.dumps(got, separators=(",", ":"), ensure_ascii=False).encode())
    ok("planning the identical week 11 file keeps the original bytes", not changed and s0 == raw and s1 == raw, logs)

def test_degrade_and_cli():
    live = json.load(open(os.path.join(FIX, "polls_week11.json"), encoding="utf-8"))
    base = P.degrade_to_week(live, "10")
    ok("week10 hook rewinds both polls", base["polls"]["ap"]["week"] == "10" and base["polls"]["coaches"]["week"] == "10" and base["polls"]["ap"]["pub"] < live["polls"]["ap"]["pub"], base["polls"]["ap"])
    ok("week10 hook does not edit the live object", live["polls"]["ap"]["week"] == "11")
    got, changed, logs = P.refresh(base, P.load_ids(), feed=json.load(open(os.path.join(FIX, "espn_rankings_week11.json"), encoding="utf-8")))
    ok("week10 baseline picks up week 11", changed and got == live, logs)
    tmp = tempfile.mkdtemp(prefix="kt-polls-")
    try:
        live_p = os.path.join(tmp, "live.json")
        out_p = os.path.join(tmp, "out.json")
        base_p = os.path.join(tmp, "base.json")
        shutil.copy(os.path.join(FIX, "polls_week11.json"), live_p)
        cmd = [sys.executable, os.path.join(TREE, "src", "poll_refresh.py"), "--live", live_p, "--feed", os.path.join(FIX, "espn_rankings_week11.json"), "--out", out_p, "--baseline", "week10", "--baseline-out", base_p]
        r = subprocess.run(cmd, capture_output=True, text=True)
        ok("cli week10 exits 0", r.returncode == 0, r.stdout + r.stderr)
        ok("cli week10 reports an update and a real-live no-op", "POLLS_CHANGED=1" in r.stdout and "against the real live file: no-op" in r.stdout and "simulated baseline week 10" in r.stdout, r.stdout)
        ok("cli week10 writes the week 11 file", os.path.exists(out_p) and json.load(open(out_p)) == live, r.stdout)
        ok("cli week10 writes the rewound baseline", json.load(open(base_p))["polls"]["ap"]["week"] == "10")
        r2 = subprocess.run(cmd + ["--fail", "timeout"], capture_output=True, text=True)
        ok("cli timeout still exits 0", r2.returncode == 0 and "POLLS_CHANGED=0" in r2.stdout and "WARNING" in r2.stdout and "timeout" in r2.stdout, r2.stdout + r2.stderr)
        ok("cli timeout does not apply the baseline hook", "baseline simulation not applied" in r2.stdout, r2.stdout)
        r3 = subprocess.run([sys.executable, os.path.join(TREE, "src", "poll_refresh.py"), "--live", live_p, "--out", os.path.join(tmp, "nope.json"), "--fail", "http"], capture_output=True, text=True)
        ok("cli http error exits 0 and writes nothing", r3.returncode == 0 and "HTTP 503" in r3.stdout and "POLLS_CHANGED=0" in r3.stdout and not os.path.exists(os.path.join(tmp, "nope.json")), r3.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

def test_baked_html_and_inject():
    polls = json.load(open(os.path.join(FIX, "polls_week11.json"), encoding="utf-8"))
    ok("as-of line has no clock and no MT", P.asof_line(polls) == "AP poll as of Nov 8. Coaches poll as of Nov 8.", P.asof_line(polls))
    ok("clock stamp gains MT", P.asof_line({"polls": {"ap": {"released": True, "asof": "Nov 8, 3:15 PM"}, "coaches": {"released": False}}}) == "AP poll as of Nov 8, 3:15 PM MT. Coaches poll: not released yet.")
    ok("utah cell", P.cell(polls, "utah") == "AP 2 \u00b7 Coaches 2")
    tmp = tempfile.mkdtemp(prefix="kt-bake-")
    try:
        os.makedirs(os.path.join(tmp, "data"))
        json.dump(polls, open(os.path.join(tmp, "data", "polls.json"), "w"))
        teams = [[row[1], 1, 0, 0] for row in polls["polls"]["ap"]["ranks"]]
        json.dump({"teams": teams}, open(os.path.join(tmp, "data", "pred-top25.json"), "w"))
        rows = []
        for i, row in enumerate(polls["polls"]["ap"]["ranks"], start=1):
            slug = row[1]
            rows.append('<li><a class="h25-r" href="/team/%s/"><span class="h25-sb">8-1 · %s</span></a></li>' % (slug, P.cell(polls, slug)))
        html = '<section id="top25"><p class="h25-asof" data-t25asof><span>%s</span></p><ol>%s</ol></section>' % (P.asof_line(polls), "".join(rows))
        open(os.path.join(tmp, "index.html"), "w").write(html)
        ok("baked html matches", P.check_baked(tmp) == [], P.check_baked(tmp))
        html2 = html.replace("AP poll as of Nov 8. Coaches poll as of Nov 8.", "AP poll as of Oct 25. Coaches poll as of Oct 25.")
        open(os.path.join(tmp, "index.html"), "w").write(html2)
        bad = P.check_baked(tmp)
        ok("stale as-of is reported", any("as-of" in s for s in bad), bad)
        # inject: pipeline copies are released=false; live is week 11; candidate is week 11 identical -> both sides live bytes
        base, s0, s1 = (os.path.join(tmp, p) for p in ("base", "s0", "s1"))
        for d in (base, s0, s1):
            os.makedirs(os.path.join(d, "data"))
        raw = open(os.path.join(FIX, "polls_week11.json"), "rb").read()
        open(os.path.join(base, "data", "polls.json"), "wb").write(raw)
        false = b'{"polls":{"ap":{"name":"AP Top 25","released":false},"coaches":{"name":"Coaches Poll","released":false}}}'
        for d in (s0, s1):
            open(os.path.join(d, "data", "polls.json"), "wb").write(false)
        P.inject_polls(base, s0, s1, None)
        ok("inject without a candidate pins both sides to the live bytes", open(os.path.join(s0, "data", "polls.json"), "rb").read() == raw and open(os.path.join(s1, "data", "polls.json"), "rb").read() == raw)
        newer = json.loads(raw)
        newer["polls"]["ap"]["week"] = "12"
        newer["polls"]["ap"]["pub"] = "2026-11-15T22:15Z"
        newer["polls"]["ap"]["asof"] = "Nov 15"
        cand = os.path.join(tmp, "cand.json")
        json.dump(newer, open(cand, "w"), separators=(",", ":"))
        P.inject_polls(base, s0, s1, cand)
        s0b = open(os.path.join(s0, "data", "polls.json"), "rb").read()
        s1o = json.load(open(os.path.join(s1, "data", "polls.json"), encoding="utf-8"))
        ok("inject keeps the live file as s0 and the newer AP on s1", s0b == raw and s1o["polls"]["ap"]["week"] == "12" and s1o["polls"]["coaches"]["week"] == "11")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

def test_asof_uses_mountain_date():
    # 2026-11-09 06:30Z is still Nov 8 in Denver (MST, UTC-7). 07:30Z is Nov 9.
    early = page(11, "2026-11-09T06:30Z")
    late = page(11, "2026-11-09T07:30Z")
    ok("asof is the Mountain calendar day", early["polls"]["ap"]["asof"] == "Nov 8" and late["polls"]["ap"]["asof"] == "Nov 9", (early["polls"]["ap"]["asof"], late["polls"]["ap"]["asof"]))

if __name__ == "__main__":
    for fn in (test_newer_week, test_same_week_noop, test_same_week_newer_pub, test_older_week, test_older_pub_same_week,
               test_timeout_and_http, test_localhost_refused, test_partial_malformed_unmapped, test_one_good_one_bad,
               test_missing_poll_keeps_the_other, test_plan_does_not_move_backward, test_week11_fixture_matches_live_shape,
               test_degrade_and_cli, test_baked_html_and_inject, test_asof_uses_mountain_date):
        fn()
    print("poll_refresh_test: %d checks, %d failures" % (res["n"], len(res["failures"])))
    sys.exit(1 if res["failures"] else 0)
