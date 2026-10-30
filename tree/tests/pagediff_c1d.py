import os, re, sys, hashlib
R = "/workspace/kicktip-c1d/before-site"; B = "/workspace/kicktip-c1d/build/site"
CSS = re.compile(r'<link rel="stylesheet" href="/assets/chat\.css\?v=c1c">')
PILL = re.compile(r'<button type="button" id="kpill" class="askpill" aria-haspopup="dialog" aria-expanded="false" hidden><i aria-hidden="true">\?</i>Ask KickTip: what if\.\.\.</button>')
JS = re.compile(r'<script src="/assets/chat\.js\?v=c1c" defer></script>')
src = open("/workspace/kicktip-c1d/src/build.py").read()
am = re.search(r"ASK_METHOD = \((.*?)\)\n", src, re.S).group(1)
ASKM = eval("(" + am + ")")
files = lambda root: {os.path.relpath(os.path.join(d, f), root) for d, _, fs in os.walk(root) for f in fs}
fr, fb = files(R), files(B)
only_r = sorted(fr - fb); only_b = sorted(fb - fr); both = sorted(fr & fb)
changed = [f for f in both if open(f"{R}/{f}", "rb").read() != open(f"{B}/{f}", "rb").read()]
out = []; pages_ok = 0; bad = []
html = [f for f in changed if f.endswith(".html") and f != "method/index.html"]
for f in html:
    b = open(f"{B}/{f}").read(); r = open(f"{R}/{f}").read()
    nb = [len(x.findall(b)) for x in (CSS, PILL, JS)]
    s = JS.sub("", PILL.sub("", CSS.sub("", b, 1), 1), 1)
    if nb == [1, 1, 1] and s == r: pages_ok += 1
    else: bad.append(f)
# method page
m_b = open(f"{B}/method/index.html").read(); m_r = open(f"{R}/method/index.html").read()
_i = m_b.index('<h2 id="ask">'); _j = m_b.index("<h2", _i + 5); method_ok = m_b[:_i] + m_b[_j:] == m_r and ASKM in m_b[_i:_j]
others = [f for f in changed if f not in html and f != "method/index.html"]
out.append("c1r1d vs refresh-1955 (before-site = kicktip-site-refresh-1955-real.zip, sha256 cd0e387db914fcb3ab3416762e538821522546e8b3919f17dacc8ae578764baa, 641 files)  [file-level diff, then page proof]\n")
out.append(f"Files in refresh-1955: {len(fr)}; in c1r1d: {len(fb)}; changed: {len(changed)}; only in refresh-1955 (removed): {len(only_r)}; only in c1r1d (added): {len(only_b)}\n")
out.append("REMOVED files: " + (", ".join(only_r) if only_r else "none") + "\n")
out.append("CHANGED non-page files: " + ", ".join(others) + "\n")
out.append(f"CHANGED pages: {len(html)} (conference/team/playoff pages) + method/index.html\n")
out.append(f"  PROOF: {pages_ok}/{len(html)} changed pages become byte-identical to refresh-1955 after removing exactly three things: the chat.css <link> tag, the #kpill button, the chat.js <script> tag (each present exactly once). Failures: {bad or 'none'}\n")
out.append(f"  method/index.html: byte-identical to refresh-1955 after removing the 'Ask KickTip (what-if questions)' section (one h2 + two paragraphs): {method_ok}\n")
unch = [f for f in both if f not in changed]
out.append(f"UNCHANGED files: {len(unch)} (incl. assets/kt.js, kt.css, lg.js, every data/pred-*.json and data/m/*/ model files, all non-ask pages: {sorted(f for f in unch if f.endswith('.html'))})\n")
out.append("ADDED files (%d):\n" % len(only_b) + "\n".join("  " + f for f in only_b) + "\n")
# _headers
hr = open(f"{R}/_headers").read(); hb = open(f"{B}/_headers").read()
out.append("_headers: " + ("only change is appending '; worker-src \\'self\\'' to the CSP: " + str(hb.replace("; worker-src 'self'", "", 1) == hr)) + "\n")
open("/workspace/kicktip-c1d/dist/c1r1d-vs-refresh1955-diff.txt", "w").write("\n".join(out))
print("".join(out)[:3500]); print("pages_ok", pages_ok, "bad", bad[:3], "method_ok", method_ok)
