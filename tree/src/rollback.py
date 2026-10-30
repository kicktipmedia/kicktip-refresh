"""Rollback convention: before replacing anything live, snapshot it to rollback/<YYYYMMDD-HHMM>-<label>/ with a MANIFEST.json (sha256 per file + note).
  python3 src/rollback.py save <dir-to-snapshot> <label> "note"     # e.g. the currently live site folder or the last build/site
  python3 src/rollback.py list
Restoring = copy the snapshot folder's contents back (listed in the manifest) and redeploy. Never delete rollback folders."""
import os, sys, json, shutil, hashlib, datetime as dt
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); RB = f"{ROOT}/rollback"

def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()

def save(src, label, note=""):
    dst = f"{RB}/{dt.datetime.now().strftime('%Y%m%d-%H%M')}-{label}"
    shutil.copytree(src, dst + "/files")
    files = {os.path.relpath(os.path.join(d, f), dst + "/files"): sha(os.path.join(d, f)) for d, _, fs in os.walk(dst + "/files") for f in fs}
    json.dump(dict(created=dt.datetime.now().isoformat(timespec="seconds") + " MT", source=src, note=note, files=files), open(dst + "/MANIFEST.json", "w"), indent=1)
    print("saved", dst, len(files), "files")

if __name__ == "__main__":
    if sys.argv[1:2] == ["save"]: save(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else "")
    else:
        for d in sorted(os.listdir(RB)): print(d)
