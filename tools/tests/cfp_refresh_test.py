"""Offline CFP rankings tests. No network except one connection-refused to 127.0.0.1:9.

python3 tools/tests/cfp_refresh_test.py
Parsing the official table, the ESPN fallback, a failed read, an older release,
and a shell step that still exits 0.
"""
import datetime as dt, json, os, shutil, subprocess, sys, tempfile, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "tree", "src"))
import cfp_refresh as C
import poll_refresh as P

FIX = os.path.join(HERE, "fixtures")
TODAY = dt.date(2026, 11, 11)
URL = "https://collegefootballplayoff.com/news/2026/11/10/rankings"
res = {"n": 0, "failures": []}

def ok(name, cond, detail=""):
    res["n"] += 1
    if not cond:
        res["failures"].append("%s %s" % (name, detail))
        print("FAIL", name, str(detail)[:600])

def page(cfp=None, week="11"):
    ranks = [[i, "team-%d" % i, "8-1"] for i in range(1, 26)]
    polls = {
        "ap": {"name": "AP Top 25", "released": True, "week": week, "asof": "Nov 8", "pub": "2026-11-08T22:15Z", "ranks": ranks},
        "coaches": {"name": "Coaches Poll", "released": True, "week": week, "asof": "Nov 8", "pub": "2026-11-08T21:08Z", "ranks": ranks},
    }
    if cfp is not None:
        polls["cfp"] = cfp
    return {"polls": polls}

def main():
    html = open(os.path.join(FIX, "cfp_2026_11_10_table.html"), encoding="utf-8").read()
    names = C.load_names()
    official, err = C.parse_official_html(html, URL, names)
    ok("official table parses", official and err is None, err)
    ok("official date is Nov 10", official and official["date"] == "2026-11-10" and official["asof"] == "Nov 10", official)
    by = {row[1]: row for row in official["ranks"]} if official else {}
    ok("Utah is 2, BYU is 10, Arizona is 23", by.get("utah") == [2, "utah", "9-0"] and by.get("byu") == [10, "byu", "7-2"] and by.get("arizona") == [23, "arizona", "7-2"], by)
    ok("25 unique places", official and [r[0] for r in official["ranks"]] == list(range(1, 26)))
    seed, seed_err = C.load_seed(C.SEED_PATH, names, TODAY)
    ok("saved release matches the official table", seed and seed["ranks"] == official["ranks"] and seed["date"] == "2026-11-10", seed_err)

    short = html.replace("<tr>\n\t\t\t<td class=\"text-center\"><strong>25</strong></td>", "<tr>\n\t\t\t<td class=\"text-center\"><strong>99</strong></td>", 1)
    bad, why = C.parse_official_html(short, URL, names)
    ok("a broken rank is refused", bad is None and why, why)
    dropped = "\n".join(line for line in html.splitlines() if "<strong>25</strong>" not in line)
    bad, why = C.parse_official_html(dropped, URL, names)
    ok("a 24-team table is refused", bad is None and why and "partial" in why, why)
    ok("an unknown team name is refused", C.parse_official_html(html, URL, {"Georgia": "georgia"})[0] is None)

    ids = {str(i): "team-%d" % i for i in range(1, 26)}
    ranks = [{"current": i, "recordSummary": "8-1", "team": {"id": str(i), "location": "Team %d" % i}} for i in range(1, 26)]
    espn, espn_err = C.parse_espn_ranking({"type": "cfp", "lastUpdated": "2026-11-18T04:00Z", "ranks": ranks}, ids)
    ok("ESPN block parses to the Denver day", espn and espn_err is None and espn["date"] == "2026-11-17" and espn["origin"] == "espn", (espn_err, espn))
    empty, empty_err = C.cfp_from_feed({"rankings": [{"type": "ap", "ranks": ranks}]}, ids)
    ok("a feed with no CFP poll is empty, not an error", empty is None and empty_err == "empty", empty_err)

    live = page()
    got, changed, logs = C.apply(live, names, ids, official=official, espn_poll=espn, espn_err=None)
    ok("a later ESPN release wins when the official page is older", changed and got["polls"]["cfp"]["date"] == "2026-11-17" and got["polls"]["cfp"]["origin"] == "espn", logs)
    ok("AP and Coaches stay put when only CFP changes", got["polls"]["ap"] == live["polls"]["ap"] and got["polls"]["coaches"] == live["polls"]["coaches"])
    tied, tie_err = C.parse_espn_ranking({"type": "cfp", "lastUpdated": "2026-11-11T05:46Z", "ranks": [
        {"current": i, "recordSummary": "9-0", "team": {"id": str(i)}} for i in range(1, 26)
    ]}, ids)
    ok("same-day ESPN stamp is Nov 10 in Denver", tied and tied["date"] == "2026-11-10", (tie_err, tied))
    got, changed, logs = C.apply(live, names, ids, official=official, espn_poll=tied)
    ok("the official page wins a same-day tie", changed and got["polls"]["cfp"]["origin"] == "cfp" and got["polls"]["cfp"]["ranks"][1] == [2, "utah", "9-0"], logs)

    held = page(cfp=dict(official, date="2026-11-17", asof="Nov 17"))
    got, changed, logs = C.apply(held, names, ids, official=official)
    ok("an older official release is refused", not changed and got is held, logs)
    ok("the refusal names the dates", any("older than live 2026-11-17" in s for s in logs), logs)

    got, changed, logs = C.apply(held, names, ids, official_err="timeout", espn_err="HTTP 503", seed=seed)
    ok("a failed read keeps a newer live release", not changed and got is held and any("keeping the last good" in s for s in logs), logs)
    fresh = page()
    got, changed, logs = C.apply(fresh, names, ids, official_err="timeout", espn_err="timeout", seed=seed)
    ok("a failed read with nothing stored uses the saved release", changed and got["polls"]["cfp"]["date"] == "2026-11-10" and got["polls"]["ap"]["week"] == "11", logs)
    got, changed, logs = C.apply(fresh, names, ids, official_err="empty", espn_err="empty", seed=seed)
    ok("no committee poll is a no-op and does not use the saved release", not changed and "cfp" not in got["polls"] and any("not released" in s for s in logs), logs)
    stale_seed = dict(seed, date="2026-01-01", asof="Jan 1")
    got, changed, logs = C.apply(page(cfp=official), names, ids, official_err="timeout", espn_err="timeout", seed=stale_seed)
    ok("a saved release older than the live one is not written", not changed and got["polls"]["cfp"]["date"] == "2026-11-10", logs)
    # age window is applied by load_seed; a January file on Nov 11 is outside 120 days
    old_path = os.path.join(tempfile.mkdtemp(prefix="kt-cfp-"), "old.json")
    old_doc = json.load(open(C.SEED_PATH, encoding="utf-8"))
    old_doc["date"] = "2026-01-01"
    old_doc["source"] = "https://collegefootballplayoff.com/news/2026/01/01/rankings"
    json.dump(old_doc, open(old_path, "w"))
    aged, aged_err = C.load_seed(old_path, names, TODAY)
    ok("a saved release older than 120 days is not loaded", aged is None and "window" in (aged_err or ""), aged_err)

    src = {"rankings": [{"type": "cfp", "lastUpdated": "2026-11-11T05:46Z", "occurrence": {"value": "11"}, "ranks": [
        {"current": row[0], "recordSummary": row[2], "team": {"id": str(200 + row[0]), "location": "X"}} for row in official["ranks"]
    ]}]}
    # ids won't match those invented ids: the fallback must refuse rather than guess
    refused, why = C.cfp_from_feed(src, names and {str(v): k for k, v in {}})
    ok("an unmapped ESPN id refuses the whole poll", refused is None and "unmapped" in (why or ""), why)

    feed, errn = C.fetch_json("http://127.0.0.1:9/rankings", timeout=2) if False else (None, None)
    try:
        C.fetch_text("http://127.0.0.1:9/rankings", timeout=2)
        ok("unreachable host raises", False)
    except Exception as e:
        ok("unreachable host classifies", C.classify(e) == "unreachable", e)

    # AP can move while CFP fails. The CFP failure does not roll the AP change back.
    newer_ap = page(week="12")
    newer_ap["polls"]["ap"]["pub"] = "2026-11-15T22:15Z"
    newer_ap["polls"]["ap"]["asof"] = "Nov 15"
    failed, changed, logs = C.apply(newer_ap, names, ids, official_err="timeout", espn_err="timeout", seed=None, seed_err="saved release unreadable")
    ok("CFP failure leaves the AP update in place", not changed and failed["polls"]["ap"]["week"] == "12" and any("keeping the last good" in s for s in logs), logs)

    js = open(os.path.join(FIX, "home_top25.js"), encoding="utf-8").read()
    patched, perr = C.patch_home_js(js)
    ok("home script patch applies", perr is None and patched != js and "function cfpBit(" in patched, perr)
    again, perr2 = C.patch_home_js(patched)
    ok("home script patch is stable", again == patched and perr2 is None, perr2)
    ok("patched script names CFP next to Coaches", "cfpBit(ps, slug)" in patched and "CFP, " in patched and "['ap', 'coaches', 'cfp']" in patched)
    pipe = open(os.path.join(ROOT, "tree", "src", "assets", "top25.js"), encoding="utf-8").read()
    untouched, why = C.patch_home_js(pipe)
    ok("pipeline top25.js is not rewritten", untouched == pipe and why == "not the home Top 25 script", why)
    css = open(os.path.join(FIX, "home_top25.css"), encoding="utf-8").read()
    css2, cerr = C.patch_home_css(css)
    ok("subtitle can wrap", cerr is None and "white-space:normal;overflow:visible" in css2 and "nowrap" not in css2.split(".t25h .h25-sb{")[1].split("}")[0], cerr)
    tmpjs = os.path.join(tempfile.mkdtemp(prefix="kt-cfp-js-"), "top25.js")
    open(tmpjs, "w", encoding="utf-8").write(patched)
    chk = subprocess.run(["node", "--check", tmpjs], capture_output=True, text=True)
    ok("patched script parses", chk.returncode == 0, chk.stderr)

    shown = json.load(open(os.path.join(ROOT, "tree", "tests", "fixtures", "polls_week11.json"), encoding="utf-8"))
    shown["polls"]["cfp"] = official
    ok("Utah row text", P.cell(shown, "utah") == "AP 2 \u00b7 Coaches 2 \u00b7 CFP 2", P.cell(shown, "utah"))
    ok("BYU row text", P.cell(shown, "byu") == "AP 12 \u00b7 Coaches 12 \u00b7 CFP 10", P.cell(shown, "byu"))
    ok("Arizona row text", P.cell(shown, "arizona") == "AP 22 \u00b7 Coaches 21 \u00b7 CFP 23", P.cell(shown, "arizona"))
    ok("a team outside the CFP 25 gets a dash", P.cell(shown, "louisville") == "AP NR \u00b7 Coaches NR \u00b7 CFP \u2014", P.cell(shown, "louisville"))
    ok("as-of label", P.asof_line(shown) == "AP poll as of Nov 8. Coaches poll as of Nov 8. CFP, Nov 10.", P.asof_line(shown))
    ok("no CFP poll leaves the as-of sentence unchanged", P.asof_line(live) == "AP poll as of Nov 8. Coaches poll as of Nov 8.")

    # Shell step: a forced failure still exits 0 and does not report a change when the live file is already current.
    tmp = tempfile.mkdtemp(prefix="kt-cfp-step-")
    try:
        zpath = os.path.join(tmp, "site.zip")
        body = json.dumps(page(cfp=seed)).encode()
        with zipfile.ZipFile(zpath, "w") as z:
            z.writestr("data/polls.json", body)
        outp = os.path.join(tmp, "out.txt")
        env = dict(os.environ)
        env.update(KT_ROOT=ROOT, KT_POLLS_ZIP=zpath, KT_POLLS_FAIL="http", KT_CFP_FAIL="timeout",
                   GITHUB_OUTPUT=outp, GITHUB_STEP_SUMMARY=os.path.join(tmp, "sum.txt"))
        r = subprocess.run(["bash", os.path.join(ROOT, "tools", "polls_step.sh")], cwd=ROOT, env=env, capture_output=True, text=True)
        text = open(outp, encoding="utf-8").read() if os.path.exists(outp) else ""
        ok("poll step exits 0 when CFP and the polls read fail", r.returncode == 0, r.stdout + r.stderr)
        ok("a failed CFP read does not report a change", "polls_changed=0" in text, text + r.stdout)
        ok("the step log keeps the last good rankings", "keeping the last good" in (r.stdout + r.stderr), r.stdout[-800:])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("cfp_refresh_test: %d checks, %d failures" % (res["n"], len(res["failures"])))
    return 1 if res["failures"] else 0

if __name__ == "__main__":
    sys.exit(main())
