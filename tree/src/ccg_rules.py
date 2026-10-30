"""Merge the step 1 and step 2 rules files, validate, and write data/ccg-rules.json. Used by build.py and tests/ccg_rules_check.py."""
import os, sys, json, importlib
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
KINDS = {"h2h": {}, "h2h_group": {"mode": ("pct_else_beat_all", "pct_only", "beat_all", "pct_else_beat_lost", "beat_or_lost")},
         "common_pct": {}, "common_ordered": {"opp_ties": ("collective", "collective_strict", "h2h_then_combine")},
         "ordered_any": {"opp_ties": ("collective", "collective_strict", "h2h_then_combine")}, "opp_conf_pct": {}, "wins12": {}, "overall_pct": {}, "fbs_pct": {},
         "div_pct": {}, "ordered_div": {"opp_ties": ("collective", "collective_strict", "h2h_then_combine")}, "common_nondiv": {}, "external": {"name": None, "take": ("all", 1, None), "optional": (True, False, None)}, "random": {"name": None}}
CODES = ("acc", "big10", "big12", "sec", "American", "usa", "midam", "mwest", "pac12", "belt")
FMT = ("top2", "div"); TIE = ("equal", "unequal_one_win", "acc_unequal"); ELIM = ("continue", "restart"); HOST = ("neutral", "higher_seed", "higher_pct")

def load():
    """-> dict code -> rules entry (step 1 + step 2 when that file exists)."""
    out = {}
    for mod in ("ccg_rules_step1", "ccg_rules_step2"):
        if not os.path.exists(os.path.join(ROOT, "src", mod + ".py")): continue
        m = importlib.import_module(mod)
        for k, v in m.RULES.items():
            if k in out: raise ValueError(f"{k} defined twice")
            out[k] = v
    return out

def check_steps(code, key, steps, errs, fmt):
    if not isinstance(steps, list) or not steps: errs.append(f"{code}.{key}: needs a non-empty list"); return
    for n, s in enumerate(steps, 1):
        p = f"{code}.{key}[{n}]"
        if not isinstance(s, dict) or s.get("k") not in KINDS: errs.append(f"{p}: unknown kind {s.get('k') if isinstance(s, dict) else s!r}"); continue
        if not (isinstance(s.get("t"), str) and len(s["t"]) > 8): errs.append(f"{p}: needs plain-words text t")
        for param, allowed in KINDS[s["k"]].items():
            if allowed is None:
                if not (isinstance(s.get(param), str) and s[param]): errs.append(f"{p}: needs {param}")
            elif s.get(param) not in allowed: errs.append(f"{p}: {param} must be one of {allowed}")
        low = (s.get("t", "") + s.get("name", "")).lower()
        for bad in ("kicktip", "rating we", "bet", "odds", "spread", "prediction"):
            if bad in low.split() or (bad == "kicktip" and bad in low): errs.append(f"{p}: forbidden wording {bad!r}")
        if s["k"] in ("div_pct", "ordered_div", "common_nondiv") and fmt != "div": errs.append(f"{p}: {s['k']} is only for fmt div")
    if steps[-1]["k"] not in ("external", "random"): errs.append(f"{code}.{key}: should end with an external or random step")

def validate(rules):
    errs = []
    for code, r in rules.items():
        if code not in CODES: errs.append(f"{code}: unknown conference code"); continue
        for f in ("name", "fmt", "doc", "ccg", "games_per_team", "tie_group", "elim", "two", "multi", "notes"):
            if f not in r: errs.append(f"{code}: missing {f}")
        if errs and errs[-1].startswith(code + ": missing"): continue
        if r["fmt"] not in FMT: errs.append(f"{code}: fmt")
        if r["tie_group"] not in TIE: errs.append(f"{code}: tie_group")
        if r["elim"] not in ELIM: errs.append(f"{code}: elim")
        d = r["doc"]
        for f in ("title", "url", "version", "checked"):
            if not isinstance(d.get(f), str) or not d[f]: errs.append(f"{code}.doc.{f}")
        if not str(d.get("url", "")).startswith("https://"): errs.append(f"{code}.doc.url must be https")
        c = r["ccg"]
        for f in ("date", "when", "site", "host"):
            if not isinstance(c.get(f), str): errs.append(f"{code}.ccg.{f}")
        if c.get("host") not in HOST: errs.append(f"{code}.ccg.host")
        if not isinstance(r["games_per_team"], int): errs.append(f"{code}.games_per_team")
        for key in ("two", "multi") + (("host",) if "host" in r else ()) + (("pre",) if "pre" in r else ()): check_steps(code, key, r[key], errs, r["fmt"])
        if "alt" in r:
            al = r["alt"]
            for f in ("a", "b", "box"):
                if not (isinstance(al.get(f), str) and len(al[f]) > 20): errs.append(f"{code}.alt.{f}: needs plain-words text")
            if not isinstance(al.get("patch"), dict) or not al["patch"]: errs.append(f"{code}.alt.patch: needs the replaced rules fields")
            else:
                for k, v in al["patch"].items():
                    if k not in ("two", "multi", "two_second"): errs.append(f"{code}.alt.patch.{k}: only two, multi, two_second")
                    else: check_steps(code, "alt." + k, v, errs, r["fmt"])
        if r["fmt"] == "div":
            dv = r.get("divisions")
            if not (isinstance(dv, dict) and len(dv) == 2): errs.append(f"{code}.divisions needs two divisions")
        if not isinstance(r["notes"], list) or not all(isinstance(x, str) for x in r["notes"]): errs.append(f"{code}.notes")
        try: json.dumps(r)
        except TypeError as e: errs.append(f"{code}: not JSON-serializable: {e}")
    return errs

def write(path=None):
    rules = load(); errs = validate(rules)
    if errs: raise SystemExit("ccg rules invalid:\n  " + "\n  ".join(errs))
    path = path or f"{ROOT}/data/ccg-rules.json"
    json.dump(dict(codes=sorted(rules), rules=rules), open(path, "w"), indent=1, ensure_ascii=False)
    return rules
if __name__ == "__main__":
    r = write(); print("ok:", sorted(r))
