"""Local static server for build/site that applies the _headers file (CSP etc.) and Cloudflare-style clean URLs. Not used in production."""
import http.server, os, sys, re, threading
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def start(site=None, port=0, log=None):
    site = site or f"{ROOT}/build/site"
    hdr = open(f"{site}/_headers").read() if os.path.exists(f"{site}/_headers") else ""
    blocks = {}; cur = None
    for line in hdr.splitlines():
        if line and not line.startswith(" "): cur = line.strip(); blocks[cur] = []
        elif line.strip() and cur: k, v = line.strip().split(": ", 1); blocks[cur].append((k, v))
    class H(http.server.SimpleHTTPRequestHandler):
        def __init__(s, *a, **k): super().__init__(*a, directory=site, **k)
        def log_message(s, *a): pass
        def end_headers(s):
            p = s.path.split("?")[0]
            for pat, hs in blocks.items():
                if pat == "/*" or (pat.endswith("/*") and p.startswith(pat[:-1])):
                    for k, v in hs: s.send_header(k, v)
            super().end_headers()
        def send_error(s, code, message=None, explain=None):
            if code == 404 and os.path.exists(f"{site}/404.html"):
                b = open(f"{site}/404.html", "rb").read(); s.send_response(404); s.send_header("Content-Type", "text/html; charset=utf-8"); s.send_header("Content-Length", str(len(b))); s.end_headers(); s.wfile.write(b)
            else: super().send_error(code, message, explain)
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", port), H); threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}"
