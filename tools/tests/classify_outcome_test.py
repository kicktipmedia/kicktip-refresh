#!/usr/bin/env python3
"""Feed every refresh exit and run type into the job classifier.

Asserts green or red, and hold or no hold. Also checks the reporter writes
FAIL(code) plus the log tail, does not write the failed-input hold, and that
the workflow wires hold/halt/retry to that decision.
"""
import json, os, subprocess, sys, tempfile, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import classify_outcome
import report_outcome

fail = 0

def check(ok, msg):
    global fail
    if ok:
        print("PASS", msg)
    else:
        print("FAIL", msg)
        fail = 1

def expect(code, ref, event, target, attempted, kind, job, hold, commit_freeze=None):
    got = classify_outcome.classify(code, ref, event, target, attempted, kind)
    label = "kind=%s exit=%s ref=%s event=%s target=%s prod=%s" % (kind, code, ref, event, target, attempted)
    check(got["job"] == job and got["hold"] is hold, "%s -> job %s hold %s (got %s %s)" % (label, job, hold, got["job"], got["hold"]))
    if commit_freeze is not None:
        check(got["commit_freeze"] is commit_freeze, "%s commit_freeze %s (got %s)" % (label, commit_freeze, got["commit_freeze"]))
    return got

# Production on any ref: schedule, production target, or an empty target.
PROD = [
    ("main", "schedule", "production"),
    ("main", "schedule", ""),
    ("main", "schedule", "none"),
    ("main", "workflow_dispatch", "production"),
    ("main", "workflow_dispatch", ""),
    ("refs/heads/main", "schedule", "production"),
    ("cursor/cfp-top25-8c29", "workflow_dispatch", "production"),
    ("cursor/cfp-top25-8c29", "workflow_dispatch", ""),
    ("cursor/cfp-top25-8c29", "schedule", "production"),
    ("feature", "workflow_dispatch", "production"),
]
# Test runs are only none/preview dispatches that did not write a Production log.
TEST = [
    ("main", "workflow_dispatch", "none"),
    ("main", "workflow_dispatch", "preview"),
    ("main", "workflow_dispatch", "NONE"),
    ("cursor/cfp-top25-8c29", "workflow_dispatch", "none"),
    ("cursor/cfp-top25-8c29", "workflow_dispatch", "preview"),
    ("feature", "workflow_dispatch", "preview"),
]

REAL = [11, 12, 14, 15, 16, 17, 20, 21, 22]
GREEN_TRANSIENT = [10, 13]
UNKNOWN = [1, 2, 19, 23, 99, None, "nope"]

def expect_production(code, ref, event, target, attempted, kind="exit"):
    if kind == "install" or code == 0 or code in (10, 13) or (code == 18 and not attempted):
        expect(code, ref, event, target, attempted, kind, "green", False, False)
    else:
        expect(code, ref, event, target, attempted, kind, "red", True, code == 22)

for ref, event, target in PROD:
    for attempted in (False, True):
        expect_production(0, ref, event, target, attempted)
        for code in GREEN_TRANSIENT:
            expect_production(code, ref, event, target, attempted)
        expect_production(18, ref, event, target, attempted)
        for code in REAL:
            expect_production(code, ref, event, target, attempted)
        for code in UNKNOWN:
            expect_production(code, ref, event, target, attempted)
        for code in (0, 12, 18, 22, 100, None):
            expect_production(code, ref, event, target, attempted, "install")

for ref, event, target in TEST:
    for code in [0, 10, 11, 12, 13, 14, 15, 16, 17, 18, 20, 21, 22, 1, 2, 19, 99, None]:
        if code == 0:
            expect(code, ref, event, target, False, "exit", "green", False, False)
        else:
            expect(code, ref, event, target, False, "exit", "green", False, code == 22)
        # A non-empty Production log makes the same dispatch a Production run.
        expect_production(code, ref, event, target, True)
    expect(100, ref, event, target, False, "install", "green", False, False)
    expect(100, ref, event, target, True, "install", "green", False, False)

# Literal rows from the runbook table, so a swapped rule fails even if the loops agree with each other.
rows = [
    (0, "main", "schedule", "production", False, "exit", "green", False),
    (10, "main", "schedule", "production", False, "exit", "green", False),
    (11, "main", "schedule", "production", False, "exit", "red", True),
    (12, "main", "workflow_dispatch", "production", False, "exit", "red", True),
    (12, "cursor/cfp-top25-8c29", "workflow_dispatch", "none", False, "exit", "green", False),
    (12, "cursor/cfp-top25-8c29", "workflow_dispatch", "preview", False, "exit", "green", False),
    (11, "cursor/cfp-top25-8c29", "workflow_dispatch", "production", False, "exit", "red", True),
    (12, "cursor/cfp-top25-8c29", "workflow_dispatch", "production", False, "exit", "red", True),
    (16, "cursor/cfp-top25-8c29", "workflow_dispatch", "production", False, "exit", "red", True),
    (21, "cursor/cfp-top25-8c29", "workflow_dispatch", "production", True, "exit", "red", True),
    (22, "cursor/cfp-top25-8c29", "workflow_dispatch", "production", True, "exit", "red", True),
    (99, "cursor/cfp-top25-8c29", "workflow_dispatch", "production", False, "exit", "red", True),
    (12, "cursor/cfp-top25-8c29", "workflow_dispatch", "", False, "exit", "red", True),
    (16, "feature", "workflow_dispatch", "", False, "exit", "red", True),
    (13, "main", "schedule", "production", False, "exit", "green", False),
    (14, "main", "schedule", "production", False, "exit", "red", True),
    (15, "main", "schedule", "production", False, "exit", "red", True),
    (16, "main", "workflow_dispatch", "none", False, "exit", "green", False),
    (16, "main", "schedule", "production", False, "exit", "red", True),
    (17, "main", "schedule", "production", False, "exit", "red", True),
    (18, "main", "schedule", "production", False, "exit", "green", False),
    (18, "main", "schedule", "production", True, "exit", "red", True),
    (18, "main", "workflow_dispatch", "preview", False, "exit", "green", False),
    (18, "main", "workflow_dispatch", "preview", True, "exit", "red", True),
    (20, "main", "schedule", "production", False, "exit", "red", True),
    (21, "main", "schedule", "production", True, "exit", "red", True),
    (22, "main", "schedule", "production", True, "exit", "red", True),
    (22, "feature", "workflow_dispatch", "production", True, "exit", "red", True),
    (99, "main", "schedule", "production", False, "exit", "red", True),
    (99, "feature", "schedule", "production", False, "exit", "red", True),
    (12, "main", "schedule", "none", False, "exit", "red", True),
    (1, "main", "schedule", "production", False, "install", "green", False),
]
for row in rows:
    expect(*row)

check(classify_outcome.is_test_run("", "schedule", "production") is False, "schedule is not a test run")
check(classify_outcome.is_test_run("main", "schedule", "none") is False, "schedule ignores a none target")
check(classify_outcome.is_test_run("cursor/cfp-top25-8c29", "workflow_dispatch", "production") is False, "non-main production dispatch is Production")
check(classify_outcome.is_test_run("cursor/cfp-top25-8c29", "workflow_dispatch", "") is False, "non-main empty target is Production")
check(classify_outcome.is_test_run("cursor/cfp-top25-8c29", "workflow_dispatch", "none") is True, "non-main none target is a test run")
check(classify_outcome.is_test_run("main", "workflow_dispatch", "preview", True) is False, "a Production deploy log is Production even on preview")
got22 = classify_outcome.classify(22, "feature", "workflow_dispatch", "none", False, "exit")
check(got22["commit_freeze"] is True and got22["job"] == "green" and got22["hold"] is False, "none-target exit 22 stays green, no hold, still commits FREEZE")
got22p = classify_outcome.classify(22, "feature", "workflow_dispatch", "production", True, "exit")
check(got22p["commit_freeze"] is True and got22p["job"] == "red" and got22p["hold"] is True, "branch production exit 22 is red, hold, commits FREEZE")
got22m = classify_outcome.classify(22, "main", "schedule", "production", True, "exit")
check(got22m["commit_freeze"] is True and got22m["job"] == "red" and got22m["hold"] is True, "main exit 22 is red, hold, commits FREEZE")

# CLI
proc = subprocess.run(
    [sys.executable, str(ROOT / "tools/classify_outcome.py"),
     "--exit", "13", "--ref-name", "main", "--event", "schedule", "--deploy-target", "production",
     "--production-attempted", "0"],
    capture_output=True, text=True, check=False)
doc = json.loads(proc.stdout)
check(proc.returncode == 0 and doc["job"] == "green" and doc["hold"] is False and doc["class"] == "transient-fetch",
      "CLI exit 13 on main schedule is green with no hold")

def run_report(args, env, root):
    e = os.environ.copy()
    e.update(env)
    e["KT_ROOT"] = str(root)
    return subprocess.run([sys.executable, str(ROOT / "tools/report_outcome.py")] + args,
                          capture_output=True, text=True, check=False, env=e)

def fresh():
    d = Path(tempfile.mkdtemp(prefix="kt-outcome-"))
    (d / "summary.md").write_text("", encoding="utf-8")
    (d / "env.txt").write_text("", encoding="utf-8")
    (d / "output.txt").write_text("", encoding="utf-8")
    env = {
        "GITHUB_STEP_SUMMARY": str(d / "summary.md"),
        "GITHUB_ENV": str(d / "env.txt"),
        "GITHUB_OUTPUT": str(d / "output.txt"),
        "KT_REF_NAME": "main",
        "GITHUB_EVENT_NAME": "schedule",
        "KT_DEPLOY_TARGET": "production",
    }
    return d, env

# Main production exit 17: red, hold requested, FAIL line and log tail, no hold file.
d, env = fresh()
log = d / "run.log"
log.write_text("model line\nSUITE_DONE fail=2\nunique-tail-suite\n", encoding="utf-8")
proc = run_report(["--exit", "17", "--step", "Refresh", "--log", str(log), "--reason", "suite subset failed"], env, d)
summary = (d / "summary.md").read_text(encoding="utf-8")
result = json.loads((d / "runs/0-report/result.json").read_text(encoding="utf-8"))
outcome = (d / "runs/0-report/outcome.log").read_text(encoding="utf-8")
env_txt = (d / "env.txt").read_text(encoding="utf-8")
check(proc.returncode == 17, "reporter exit 17 on main returns 17 (rc=%s)" % proc.returncode)
check("FAIL(17): suite subset failed" in summary and "FAIL(17): suite subset failed" in outcome, "summary and outcome log show FAIL(17)")
check("unique-tail-suite" in summary and result["log_tail"].endswith("unique-tail-suite") and "unique-tail-suite" in outcome,
      "summary, result.json, and outcome log show the log tail")
check(result["job"] == "red" and result["hold"] is True and "KT_HOLD=1" in env_txt and "KT_HALT=" not in env_txt,
      "exit 17 sets KT_HOLD and does not halt")
check(not (d / "hold/failed").exists(), "reporter does not write hold/failed on a red exit")

# Test-run exit 12 (stale branch sha): green, no hold, halt, FAIL(12) and the sha line.
d, env = fresh()
env["KT_REF_NAME"] = "cursor/cfp-top25-8c29"
env["GITHUB_EVENT_NAME"] = "workflow_dispatch"
env["KT_DEPLOY_TARGET"] = "none"
log = d / "fetch.log"
log.write_text("base zip sha abc != state.live_sha def\n", encoding="utf-8")
proc = run_report(["--exit", "12", "--step", "Fetch base (live zip + S0) and check sha", "--log", str(log)], env, d)
summary = (d / "summary.md").read_text(encoding="utf-8")
result = json.loads((d / "runs/0-report/result.json").read_text(encoding="utf-8"))
env_txt = (d / "env.txt").read_text(encoding="utf-8")
check(proc.returncode == 0, "stale-branch exit 12 returns 0 (rc=%s)" % proc.returncode)
check("FAIL(12):" in summary and "state.live_sha" in summary and "state.live_sha" in result["log_tail"],
      "stale-branch report shows FAIL(12) and the sha line")
check(result["job"] == "green" and result["hold"] is False and "KT_HOLD=" not in env_txt and "KT_HALT=1" in env_txt,
      "stale-branch exit 12 is green, no hold, halted")
check(not (d / "hold/failed").exists(), "stale-branch report does not write hold/failed")

# Main exit 13 and exit 10: green, no hold. Exit 10 has no auto_refresh result.json; the log line is the reason.
d, env = fresh()
run = d / "runs/20261111-120000"
run.mkdir(parents=True)
(run / "run.log").write_text("[2026-11-11] another run holds the lock; exiting\n", encoding="utf-8")
proc = run_report(["--exit", "10", "--step", "Refresh"], env, d)
result = json.loads((d / "runs/0-report/result.json").read_text(encoding="utf-8"))
check(proc.returncode == 0 and result["hold"] is False and "FAIL(10):" in result["fail"] and "holds the lock" in result["log_tail"],
      "exit 10 is green, no hold, FAIL(10) and the lock line")
check(not (run / "result.json").exists(), "exit 10 does not invent a result.json inside the real run dir")

d, env = fresh()
run = d / "runs/20261111-120001"
run.mkdir(parents=True)
(run / "result.json").write_text(json.dumps({"run": "20261111-120001", "exit": 13, "reason": "ESPN errors: timeout"}) + "\n", encoding="utf-8")
(run / "run.log").write_text("FAIL(13): ESPN errors: timeout\nunique-espn-tail\n", encoding="utf-8")
proc = run_report(["--exit", "13", "--step", "Refresh"], env, d)
result = json.loads((d / "runs/0-report/result.json").read_text(encoding="utf-8"))
kept = json.loads((run / "result.json").read_text(encoding="utf-8"))
env_txt = (d / "env.txt").read_text(encoding="utf-8")
check(proc.returncode == 0 and result["job"] == "green" and result["hold"] is False and "KT_HOLD=" not in env_txt,
      "exit 13 is green and does not request a hold")
check(result["fail"] == "FAIL(13): ESPN errors: timeout" and "unique-espn-tail" in result["log_tail"],
      "exit 13 report uses the script reason and the log tail")
check(kept["reason"] == "ESPN errors: timeout" and "log_tail" not in kept, "script result.json is left unchanged")

# Exit 18: empty prod.log is not an attempt; a non-empty one is.
d, env = fresh()
prev = d / "runs/20261111-130000"
prev.mkdir(parents=True)
(prev / "prod.log").write_text("", encoding="utf-8")
(prev / "run.log").write_text("preview flake\n", encoding="utf-8")
proc = run_report(["--exit", "18", "--step", "Refresh", "--detect-production", "--reason", "preview deploy"], env, d)
result = json.loads((d / "runs/0-report/result.json").read_text(encoding="utf-8"))
check(proc.returncode == 0 and result["production_attempted"] is False and result["hold"] is False and "FAIL(18):" in result["fail"],
      "exit 18 with an empty prod.log is green and no hold")

d, env = fresh()
prev = d / "runs/20261111-130001"
prev.mkdir(parents=True)
(prev / "prod.log").write_text("deploying production\n", encoding="utf-8")
(prev / "run.log").write_text("after prod\n", encoding="utf-8")
proc = run_report(["--exit", "18", "--step", "Refresh", "--detect-production", "--reason", "preview after prod"], env, d)
result = json.loads((d / "runs/0-report/result.json").read_text(encoding="utf-8"))
env_txt = (d / "env.txt").read_text(encoding="utf-8")
check(proc.returncode == 18 and result["production_attempted"] is True and result["job"] == "red" and "KT_HOLD=1" in env_txt,
      "exit 18 with a Production log is red and requests a hold")

# Install failure: green, no hold, FAIL(install), log tail kept. Explicit flag wins over detection.
d, env = fresh()
log = d / "install.log"
log.write_text("Temporary failure resolving azure.archive.ubuntu.com\nE: Unable to fetch some archives\n", encoding="utf-8")
proc = run_report(["--kind", "install", "--exit", "100", "--step", "Install tools (pinned)", "--log", str(log),
                   "--reason", "Install tools (pinned) failed after 3 tries (apt, DNS, or network)",
                   "--detect-production", "--production-attempted", "1"], env, d)
result = json.loads((d / "runs/0-report/result.json").read_text(encoding="utf-8"))
summary = (d / "summary.md").read_text(encoding="utf-8")
env_txt = (d / "env.txt").read_text(encoding="utf-8")
check(proc.returncode == 0 and result["job"] == "green" and result["hold"] is False and "KT_HOLD=" not in env_txt and "KT_HALT=1" in env_txt,
      "install failure is green, no hold, halted")
check("FAIL(install):" in summary and "Unable to fetch some archives" in summary and "Unable to fetch some archives" in result["log_tail"],
      "install report shows FAIL(install) and the apt tail")
check(not (d / "hold/failed").exists(), "install report does not write hold/failed")

# Branch + production exit 22 is a real Production failure: red, hold, FREEZE commit.
d, env = fresh()
env["KT_REF_NAME"] = "feature"
env["GITHUB_EVENT_NAME"] = "workflow_dispatch"
env["KT_DEPLOY_TARGET"] = "production"
log = d / "live.log"
log.write_text("byte-compare failed\n", encoding="utf-8")
proc = run_report(["--exit", "22", "--step", "Refresh", "--log", str(log), "--reason", "live byte-compare failed; FREEZE written"], env, d)
env_txt = (d / "env.txt").read_text(encoding="utf-8")
check(proc.returncode == 22 and "KT_COMMIT_FREEZE=1" in env_txt and "KT_HOLD=1" in env_txt and "KT_HALT=" not in env_txt,
      "branch production exit 22 fails the job, requests the hold, and commits FREEZE")
# none/preview still stays green, including exit 22, and does not request the hold.
d, env = fresh()
env["KT_REF_NAME"] = "feature"
env["GITHUB_EVENT_NAME"] = "workflow_dispatch"
env["KT_DEPLOY_TARGET"] = "none"
log = d / "live-none.log"
log.write_text("byte-compare failed\n", encoding="utf-8")
proc = run_report(["--exit", "22", "--step", "Refresh", "--log", str(log), "--reason", "live byte-compare failed; FREEZE written"], env, d)
env_txt = (d / "env.txt").read_text(encoding="utf-8")
check(proc.returncode == 0 and "KT_COMMIT_FREEZE=1" in env_txt and "KT_HOLD=" not in env_txt and "KT_HALT=1" in env_txt,
      "none-target exit 22 exits 0, requests FREEZE commit, no hold")

# 0-report sorts before a timestamped run, so tail picks the real directory.
order = sorted(["0-report", "20261111-122841"])
check(order[-1] == "20261111-122841", "0-report sorts before the run directory")
d, env = fresh()
real = d / "runs/20261111-122841"
real.mkdir(parents=True)
(real / "result.json").write_text('{"exit":0,"live_id":"abc"}\n', encoding="utf-8")
(d / "runs/0-report").mkdir(parents=True)
(d / "runs/0-report/result.json").write_text("{}\n", encoding="utf-8")
listed = subprocess.check_output(["bash", "-c", 'ls -d runs/* | tail -n 1'], cwd=d, text=True).strip()
check(listed.endswith("20261111-122841"), "ls | tail still selects the real run (%s)" % listed)

# Retry: third try succeeds; always-fail stops at 3; backoff is attempt * seconds.
script = ROOT / "tools/retry_cmd.sh"
d, env = fresh()
count = d / "count"
count.write_text("0\n", encoding="utf-8")
log = d / "retry.log"
cmd = "c=$(cat %s); echo $((c+1)) > %s; [ \"$c\" -ge 2 ]" % (count, count)
proc = subprocess.run(["bash", str(script), "--tries", "3", "--backoff", "0", "--log", str(log), "--", "bash", "-c", cmd],
                      capture_output=True, text=True, check=False)
text = log.read_text(encoding="utf-8")
check(proc.returncode == 0 and text.count("attempt ") >= 3 and "attempt 3/3 ok" in text and "sleeping 0s" in text,
      "retry succeeds on the third try (rc=%s)" % proc.returncode)

d, env = fresh()
log = d / "retry-fail.log"
t0 = time.time()
proc = subprocess.run(["bash", str(script), "--tries", "2", "--backoff", "1", "--log", str(log), "--", "bash", "-c", "echo no; exit 7"],
                      capture_output=True, text=True, check=False)
elapsed = time.time() - t0
text = log.read_text(encoding="utf-8")
check(proc.returncode == 7 and "attempt 1/2 rc=7" in text and "attempt 2/2 rc=7" in text and "sleeping 1s before retry" in text
      and "failed after 2 tries rc=7" in text and elapsed >= 1, "retry returns the command exit after backoff (rc=%s elapsed=%.2f)" % (proc.returncode, elapsed))

# The reporter source never writes the hold file.
src = (ROOT / "tools/report_outcome.py").read_text(encoding="utf-8")
check("hold/failed" not in src, "report_outcome.py does not mention hold/failed")

# Workflow wiring. Hold steps require the classifier flag, not failure() alone.
wf = (ROOT / ".github/workflows/refresh.yml").read_text(encoding="utf-8")
check("KT_DEPLOY_TARGET: ${{ inputs.deploy_target || 'production' }}" in wf, "workflow defaults an empty deploy target to production")
for title in ("Failed-input hold (record this input hash)", "Failed-input hold (save)"):
    step = wf.split("- name: " + title, 1)[1].split("- name:", 1)[0]
    check("failure()" in step and "env.KT_HOLD == '1'" in step and "steps.gate.outputs.inhash != ''" in step,
          "%s requires failure, KT_HOLD, and an input hash" % title)
    check("continue-on-error" not in step or title.endswith("(save)"), "hold record is not continue-on-error")
install = wf.split("- name: Install tools (pinned)", 1)[1].split("- name: Refresh", 1)[0]
check("--tries 3" in install and "--backoff 20" in install and "--kind install" in install and "continue-on-error" not in install,
      "install step retries 3 times then classifies kind install")
check("playwright install --with-deps chromium" in install and "wrangler@3.114.17" in install, "install command is unchanged")
refresh = wf.split("- name: Refresh\n", 1)[1].split("- name: Record new live base", 1)[0]
check("tools/auto_refresh.sh $A" in refresh and "report_outcome.py" in refresh and "--detect-production" in refresh
      and 'echo "shipped=1"' in refresh and "continue-on-error" not in refresh, "refresh step classifies a non-zero exit and marks a real exit 0")
record = wf.split("- name: Record new live base", 1)[1].split("- name: Failed-input hold", 1)[0]
check("steps.refresh.outputs.shipped == '1'" in record and "--exit 22" in record and "publish_base.sh" in record,
      "record step publishes only after a real exit 0 and classifies a publish failure as 22")
check('R=$(ls -d runs/* | tail -n 1)/result.json; cat $R' in record, "record step still reads the latest run result.json")
freeze = wf.split("- name: Commit FREEZE if a post-deploy check failed", 1)[1].split("- name:", 1)[0]
check("failure() || env.KT_COMMIT_FREEZE == '1'" in freeze and "pull --rebase --autostash" in freeze and "pull --rebase &&" not in freeze,
      "FREEZE commit still uses autostash and also runs when the reporter asks")
check('hashFiles(\'runs/0-report/result.json\')' in wf, "log artifact uploads the written report")
for needle in ("Held: inputs", "polls_only=1", "ranks_only=1", "KT_LINES_PULLED=1", "inhash=$INHASH", "KT_SKIP_FETCH=1"):
    check(needle in wf, "gate still decides with %s" % needle)
check("--exit 11" in wf.split("- name: Stop if frozen", 1)[1].split("- uses:", 1)[0], "FREEZE present is reported as exit 11")
check("tools/fetch_base.sh" in wf and "report_outcome.py --exit \"$rc\"" in wf, "fetch base failures go through the reporter")
check("continue-on-error: true" in wf.split("- name: National ranks (fetch", 1)[1].split("- name:", 1)[0], "ranks stay continue-on-error")
cfp_step = wf.split("- name: CFP refresh unit tests", 1)[1].split("- uses:", 1)[0]
check("env.KT_HALT != '1'" in cfp_step and "tools/tests/cfp_refresh_test.py" in cfp_step,
      "CFP unit tests stay in the workflow and halt with the classifier")
polls_step = wf.split("- name: Polls and CFP (last good, never fails)", 1)[1].split("- name:", 1)[0]
check("id: polls" in polls_step and "env.KT_HALT != '1'" in polls_step and "tools/polls_step.sh" in polls_step,
      "Polls and CFP step stays and halts with the classifier")

# auto_refresh.sh exit codes were not retargeted by this change.
auto = (ROOT / "tools/auto_refresh.sh").read_text(encoding="utf-8")
check("fail 22 \"live byte-compare failed; FREEZE written;" in auto and "|| fail 22 \"state.json write failed\"" in auto,
      "auto_refresh.sh still fails 22 on byte-compare and state.json")
check("timeout 80 python3 src/poll_refresh.py" in auto and "--cfp" in auto,
      "auto_refresh.sh still runs the CFP poll read inside the non-blocking polls command")
check("> $R/FREEZE" not in auto, "auto_refresh.sh still does not write FREEZE itself")

print("SUITE_DONE fail=%d" % fail)
sys.exit(fail)
