#!/usr/bin/env python3
"""Write the refresh job report and exit 0 only when the job should stay green.

The workflow calls this instead of letting a raw step failure stand. A green
classification exits 0, so later steps that use failure() do not run, and it
does not set KT_HOLD. It never writes the failed-input hold file. The workflow
writes that hold only when KT_HOLD=1 and the gate recorded an input hash.

The report directory is runs/0-report/. That name sorts before a timestamped
run directory, so `ls -d runs/* | tail -n 1` in the record step still selects
the real run.
"""
import json, os, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import classify_outcome

TAIL_LINES = 40
REPORT_DIR = "0-report"


def _flag(text):
    return str(text).strip().lower() in ("1", "true", "yes")


def _run_dirs(root):
    base = root / "runs"
    if not base.is_dir():
        return []
    found = []
    for p in base.iterdir():
        name = p.name
        if p.is_dir() and len(name) >= 9 and name[:8].isdigit() and name[8] == "-":
            found.append(p)
    return sorted(found, key=lambda p: p.name)


def production_attempted(root):
    """True when this job wrote a non-empty Production deploy log."""
    base = Path(root) / "runs"
    if not base.is_dir():
        return False
    for p in base.glob("*/prod.log"):
        if not p.is_file() or p.parent.name == REPORT_DIR:
            continue
        try:
            if p.stat().st_size > 0:
                return True
        except OSError:
            continue
    return False


def _tail(path, n=TAIL_LINES):
    if not path:
        return ""
    file = Path(path)
    if not file.is_file():
        return ""
    try:
        data = file.read_bytes()
    except OSError:
        return ""
    text = data.decode("utf-8", "replace")
    lines = text.splitlines()
    return "\n".join(lines[-n:])


def _reason_from_runs(root):
    for d in reversed(_run_dirs(root)):
        result = d / "result.json"
        if not result.is_file():
            continue
        try:
            doc = json.loads(result.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        reason = doc.get("reason")
        if reason:
            return str(reason)
    return ""


def _latest_log(root):
    for d in reversed(_run_dirs(root)):
        log = d / "run.log"
        if log.is_file():
            return log
    return None


def _fail_code(kind, code):
    if kind == "install":
        return "install"
    if code is None:
        return "unknown"
    return str(code)


def _parse_args(argv):
    exit_text = None
    kind = "exit"
    log = ""
    reason = ""
    step = "refresh"
    detect = False
    attempted = None
    i = 0
    while i < len(argv):
        a = argv[i]
        def need():
            if i + 1 >= len(argv):
                raise SystemExit("missing value for %s" % a)
            return argv[i + 1]
        if a == "--exit":
            exit_text = need(); i += 2
        elif a == "--kind":
            kind = need(); i += 2
        elif a == "--log":
            log = need(); i += 2
        elif a == "--reason":
            reason = need(); i += 2
        elif a == "--step":
            step = need(); i += 2
        elif a == "--production-attempted":
            attempted = _flag(need()); i += 2
        elif a == "--detect-production":
            detect = True; i += 1
        else:
            raise SystemExit("unknown arg %s" % a)
    if exit_text is None:
        raise SystemExit("--exit is required")
    return exit_text, kind, log, reason, step, detect, attempted


def report(exit_text, kind, ref_name, event_name, deploy_target, production_attempted_flag, step, reason, log_text):
    """Build the classification and the on-disk report bodies. Does not touch the hold."""
    kind = (kind or "exit").strip().lower()
    code = classify_outcome.parse_exit(exit_text)
    decision = classify_outcome.classify(code, ref_name, event_name, deploy_target, production_attempted_flag, kind)
    shown = _fail_code(kind, code)
    why = (reason or "").strip() or "(no reason recorded)"
    fail = "FAIL(%s): %s" % (shown, why)
    tail = log_text if log_text is not None else ""
    job_word = "green" if decision["job"] == "green" else "red"
    if decision["job"] == "green":
        mail = "This job stays green, so GitHub does not email."
    else:
        mail = "This job fails, so GitHub emails the account owner."
    hold_word = "yes" if decision["hold"] else "no"
    fence = tail.replace("```", "'''")
    summary = "\n".join([
        "### Refresh outcome: %s" % job_word,
        "",
        mail,
        "",
        "- Step: %s" % step,
        "- Class: %s" % decision["class"],
        "- Exit: %s" % shown,
        "- Hold: %s" % hold_word,
        "- Ref: `%s`  Event: `%s`  Target: `%s`" % (ref_name or "", event_name or "", deploy_target or ""),
        "- Production attempted: %s" % ("yes" if production_attempted_flag else "no"),
        "",
        fail,
        "",
        "Log tail:",
        "",
        "```",
        fence,
        "```",
        "",
    ])
    body = {
        "step": step,
        "exit": shown,
        "command_exit": code,
        "fail": fail,
        "reason": why,
        "job": decision["job"],
        "hold": decision["hold"],
        "commit_freeze": decision["commit_freeze"],
        "class": decision["class"],
        "ref": ref_name or "",
        "event": event_name or "",
        "deploy_target": deploy_target or "",
        "production_attempted": bool(production_attempted_flag),
        "log_tail": tail,
    }
    log_body = fail + "\n\n" + tail + ("\n" if tail and not tail.endswith("\n") else "")
    halt = decision["job"] == "green" and not (kind == "exit" and code == 0)
    return decision, summary, body, log_body, halt


def _append_env(path, lines):
    if not path or not lines:
        return
    with open(path, "a", encoding="utf-8") as f:
        for line in lines:
            f.write(line + "\n")


def main(argv):
    exit_text, kind, log, reason, step, detect, attempted = _parse_args(argv)
    root = Path(os.environ.get("KT_ROOT") or Path(__file__).resolve().parent.parent)
    ref = os.environ.get("KT_REF_NAME") or os.environ.get("GITHUB_REF_NAME") or ""
    event = os.environ.get("GITHUB_EVENT_NAME") or ""
    target = os.environ.get("KT_DEPLOY_TARGET")
    if target is None or target == "":
        target = "production"
    if attempted is None:
        attempted = production_attempted(root) if detect else False
    if not reason:
        reason = _reason_from_runs(root)
    log_path = Path(log) if log else _latest_log(root)
    tail = _tail(log_path) if log_path else ""
    if not reason:
        last = ""
        for line in tail.splitlines():
            if line.strip():
                last = line.strip()
        reason = last or ("command exit %s" % exit_text)
    decision, summary, body, log_body, halt = report(
        exit_text, kind, ref, event, target, attempted, step, reason, tail)
    out_dir = root / "runs" / REPORT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    result_path = out_dir / "result.json"
    tmp = out_dir / "result.json.tmp"
    tmp.write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, result_path)
    (out_dir / "outcome.log").write_text(log_body if log_body.endswith("\n") else log_body + "\n", encoding="utf-8")
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY") or ""
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as f:
            f.write(summary)
    print(body["fail"])
    print("job %s class %s hold %s" % (decision["job"], decision["class"], "yes" if decision["hold"] else "no"))
    env_lines = []
    if decision["hold"]:
        env_lines.append("KT_HOLD=1")
    if halt:
        env_lines.append("KT_HALT=1")
    if decision["commit_freeze"]:
        env_lines.append("KT_COMMIT_FREEZE=1")
    _append_env(os.environ.get("GITHUB_ENV") or "", env_lines)
    output_lines = [
        "job=%s" % decision["job"],
        "hold=%s" % ("1" if decision["hold"] else "0"),
        "halt=%s" % ("1" if halt else "0"),
        "commit_freeze=%s" % ("1" if decision["commit_freeze"] else "0"),
        "class=%s" % decision["class"],
    ]
    _append_env(os.environ.get("GITHUB_OUTPUT") or "", output_lines)
    if decision["job"] == "green":
        return 0
    code = body["command_exit"]
    if isinstance(code, int) and code != 0:
        return code
    return 1


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except SystemExit as e:
        if isinstance(e.code, int):
            raise
        print(str(e), file=sys.stderr)
        sys.exit(2)
    except Exception as e:
        print("report_outcome failed: %s" % e, file=sys.stderr)
        sys.exit(1)
