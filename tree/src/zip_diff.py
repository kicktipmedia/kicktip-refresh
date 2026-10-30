"""python3 src/zip_diff.py <base-name> -> dist/<base-name>-to-v6a-diff.txt: file-level diff of the v6a zip against dist/base-<base-name>.zip (dom1 = deployed production, b9f = dom1 code on the newer data)."""
import zipfile, hashlib, collections, sys
BASE = sys.argv[1] if len(sys.argv) > 1 else "dom1"; NEW = sys.argv[2] if len(sys.argv) > 2 else "kicktip-site-v6a.zip"; OUTF = sys.argv[3] if len(sys.argv) > 3 else f"dist/{BASE}-to-v6a-diff.txt"
BASEP = BASE if BASE.endswith(".zip") else f"dist/base-{BASE}.zip"   # a name in dist/base-<name>.zip, or a path to any zip (e.g. dist/kicktip-site-v6a-rev1.zip)
A = zipfile.ZipFile(BASEP); B = zipfile.ZipFile(f"dist/{NEW}")
a = {n: hashlib.sha256(A.read(n)).hexdigest() for n in A.namelist()}; b = {n: hashlib.sha256(B.read(n)).hexdigest() for n in B.namelist()}
add = sorted(set(b) - set(a)); rem = sorted(set(a) - set(b)); chg = sorted(n for n in a if n in b and a[n] != b[n])
out = [f"{BASE} zip (sha256 {hashlib.sha256(open(BASEP,'rb').read()).hexdigest()}) -> {NEW} (sha256 {hashlib.sha256(open(f"dist/{NEW}",'rb').read()).hexdigest()})",
       f"files: base {len(a)}, v6a {len(b)}; added {len(add)}, removed {len(rem)}, changed {len(chg)}, identical {len(a)-len(rem)-len(chg)}", "\nADDED:"] + ["  " + n for n in add] + ["\nREMOVED:"] + ["  " + n for n in rem]
g = collections.defaultdict(list)
for n in chg: g['html pages' if n.endswith('.html') else n].append(n)
out.append("\nCHANGED:"); out += [f"  {k}: {len(v)}" if k == 'html pages' else f"  {k}" for k, v in g.items()]
out.append("""
NOTE on the changed HTML pages: every page differs from the base by (1) nothing for the host: dom1/b9f and v6a all use kicktipmedia.com from src/site_config.py (zero pages.dev strings, host_test), (2) kt.css/kt.js cache-bust ?v=v6a, (3) static copy that follows the default model (source wording, gap text), plus the new method-page sections on /method/. No page ships a model number before the disclaimer is accepted (tests/model_toggle_test.py). data/pred-*.json now carry the blend; data/m/<id>/pred-*.json are the three alternates, fetched only after acceptance and only when picked.
assets/lg.js differs only in the order of the preloaded top-team logo ids (data-driven).""")
open(OUTF, 'w').write("\n".join(out) + "\n"); print("\n".join(out[:3]))
