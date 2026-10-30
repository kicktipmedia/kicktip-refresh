"""python3 tests/zipdiff.py base.zip new.zip > diff.txt   (file-level zip diff, like the earlier rev diffs)"""
import sys, zipfile, hashlib, re, difflib
def load(p):
    z = zipfile.ZipFile(p); return {i.filename: z.read(i.filename) for i in z.infolist() if not i.is_dir()}
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
a, b = load(sys.argv[1]), load(sys.argv[2])
add = sorted(set(b) - set(a)); rem = sorted(set(a) - set(b)); ch = sorted(k for k in a if k in b and a[k] != b[k]); same = len(a) - len(rem) - len(ch)
print(f"{sys.argv[1]} (sha256 {sha(sys.argv[1])}) -> {sys.argv[2]} (sha256 {sha(sys.argv[2])})\nfiles: base {len(a)}, new {len(b)}; added {len(add)}, removed {len(rem)}, changed {len(ch)}, identical {same}\n\nADDED:"); [print("  " + k) for k in add]; print("\nREMOVED:"); [print("  " + k) for k in rem]
html = [k for k in ch if k.endswith(".html")]; print(f"\nCHANGED:\n  html pages: {len(html)}"); [print("  " + k) for k in ch if not k.endswith(".html")]
print("\nHTML CHANGE KINDS (normalised line diffs, count of pages):")
kinds = {}; NORM = lambda t: re.sub(r"\?v=(v6a|chip1|chip2)", "?v=X", t); only_bust = [k for k in html if NORM(a[k].decode()) == NORM(b[k].decode())]
print(f"  pages whose ONLY change is the asset cache-bust token (?v=chip1 -> ?v=chip2): {len(only_bust)} of {len(html)}")
for k in html:
    la, lb = NORM(a[k].decode()).split("\n"), NORM(b[k].decode()).split("\n")
    for d in difflib.unified_diff(la, lb, lineterm="", n=0):
        if d[:1] in "+-" and not d.startswith(("+++", "---")): kinds.setdefault(re.sub(r"\s+", " ", d)[:200], set()).add(k)
for d, ks in sorted(kinds.items(), key=lambda x: -len(x[1]))[:12]: print(f"  {len(ks):4d} pages  {d}")
print("\nJSON CHANGE SUMMARY: pred-teams.json files that gained a chip key 'm':")
for k in ch:
    if k.endswith("pred-teams.json"): print(f"  {k}: chips {sum('m' in v for v in __import__('json').loads(b[k])['teams'].values())}")
