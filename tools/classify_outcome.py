#!/usr/bin/env python3
"""Decide whether a refresh workflow exit fails the GitHub job.

auto_refresh.sh exit codes are unchanged. This only decides the job result and
whether the failed-input hold is warranted. See RUNBOOK "Job result and email".

A test run is only a dispatch whose deploy_target is none or preview, and which
did not write a Production deploy log. The git ref does not matter. A production
or empty target is Production on any ref. A schedule is Production. A non-empty
prod deploy log is Production. Test runs are green and never warrant the hold.
Exit 12 from a stale branch stays green only for none or preview.

On a Production run:
  green, no hold: exit 0, 10, 13, 18 when Production was not attempted, and an
  install-tools failure after retries.
  red, hold: 11, 12, 14, 15, 16, 17, 20, 21, 22, 18 when Production was attempted,
  and any other code.
Exit 22 also asks the workflow to commit FREEZE when that file was written.
The hold is still written only when the gate recorded an input hash.
"""
import argparse, json, sys

REAL_EXITS = (11, 12, 14, 15, 16, 17, 20, 21, 22)


def is_test_run(ref_name, event_name, deploy_target, production_attempted=False):
    """True only for a none/preview dispatch that did not deploy to Production.

    ref_name is the checkout ref and does not change the class. A production or
    empty target is Production on every ref. A schedule is Production. A
    non-empty Production deploy log is Production.
    """
    if production_attempted:
        return False
    if (event_name or "").strip() == "schedule":
        return False
    target = (deploy_target or "").strip().lower()
    return target in ("none", "preview")


def classify(exit_code, ref_name, event_name, deploy_target, production_attempted=False, kind="exit"):
    """Return job (green|red), hold, commit_freeze, and class for one outcome.

    exit_code is an int, or None when the code is not a number (unknown).
    kind "install" is the Install tools step after its retries are exhausted.
    production_attempted is true only when a Production deploy log was written.
    """
    kind = (kind or "exit").strip().lower()
    attempted = bool(production_attempted)
    if kind == "install":
        return {"job": "green", "hold": False, "commit_freeze": False, "class": "transient-install"}
    if kind != "exit":
        raise ValueError("kind must be exit or install")
    code = exit_code
    commit_freeze = code == 22
    if code == 0:
        return {"job": "green", "hold": False, "commit_freeze": False, "class": "ok"}
    if is_test_run(ref_name, event_name, deploy_target, attempted):
        return {"job": "green", "hold": False, "commit_freeze": commit_freeze, "class": "test-run"}
    if code == 10:
        return {"job": "green", "hold": False, "commit_freeze": False, "class": "transient-lock"}
    if code == 13:
        return {"job": "green", "hold": False, "commit_freeze": False, "class": "transient-fetch"}
    if code == 18 and not attempted:
        return {"job": "green", "hold": False, "commit_freeze": False, "class": "transient-preview"}
    if code == 18 and attempted:
        return {"job": "red", "hold": True, "commit_freeze": False, "class": "preview-after-production"}
    if code in REAL_EXITS:
        return {"job": "red", "hold": True, "commit_freeze": commit_freeze, "class": "real"}
    return {"job": "red", "hold": True, "commit_freeze": False, "class": "unknown"}


def parse_exit(text):
    if text is None:
        return None
    s = str(text).strip()
    if s == "":
        return None
    try:
        return int(s)
    except ValueError:
        return None


def main(argv):
    p = argparse.ArgumentParser(description="Print the refresh job classification as JSON")
    p.add_argument("--exit", required=True, help="process exit code (integer, or other for unknown)")
    p.add_argument("--kind", default="exit", choices=("exit", "install"))
    p.add_argument("--ref-name", default="")
    p.add_argument("--event", default="")
    p.add_argument("--deploy-target", default="")
    p.add_argument("--production-attempted", default="0")
    args = p.parse_args(argv)
    attempted = str(args.production_attempted).strip().lower() in ("1", "true", "yes")
    out = classify(parse_exit(args.exit), args.ref_name, args.event, args.deploy_target, attempted, args.kind)
    out["exit"] = parse_exit(args.exit)
    out["kind"] = args.kind
    out["test_run"] = is_test_run(args.ref_name, args.event, args.deploy_target, attempted)
    print(json.dumps(out, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
