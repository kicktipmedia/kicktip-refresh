#!/bin/bash
# Offline tests for the post-deploy live compare and the FREEZE push.
# (a) bytecmp mismatch, then match on retry -> success, no FREEZE
# (b) persistent apex mismatch, pages.dev match -> live base recorded, no FREEZE
# (c) pages.dev mismatch -> FREEZE written, and the workflow FREEZE push succeeds with a dirty worktree
set -uo pipefail
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
fail=0
TMP=$(mktemp -d)
SRV=""
APEX=""; WWW=""; PAGES=""
need() {
  if [ "$1" = 0 ]; then echo "PASS $2"
  else
    echo "FAIL $2"
    fail=1
    echo "--- verify.err ---"; cat "$TMP/verify.err" 2>/dev/null || true
    echo "--- bytecmp ---"; cat "$TMP/bytecmp.txt" 2>/dev/null || true
    echo "--- hits ---"; cat "$TMP/hits.jsonl" 2>/dev/null || true
  fi
}
stop_srv() { if [ -n "$SRV" ]; then kill "$SRV" 2>/dev/null || true; wait "$SRV" 2>/dev/null || true; SRV=""; fi; }
trap 'stop_srv; rm -rf "$TMP"' EXIT

SITE=$TMP/site
mkdir -p "$SITE"
printf 'hello-live' > "$SITE/note.txt"

start_srv() {
  stop_srv
  : > "$TMP/hits.jsonl"
  : > "$TMP/ports"
  python3 - "$SITE" "$TMP/hits.jsonl" "$@" >"$TMP/ports" 2>"$TMP/srv.err" <<'PY' &
import json,sys,threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
site,log=sys.argv[1],sys.argv[2]
body=open(site+"/note.txt","rb").read()
lock=threading.Lock(); hits={}
def make(name, mode):
    class H(BaseHTTPRequestHandler):
        def do_GET(self):
            with lock:
                hits[name]=hits.get(name,0)+1
                n=hits[name]
                open(log,"a").write(json.dumps({"name":name,"path":self.path,"n":n,
                    "cache":self.headers.get("Cache-Control"),"pragma":self.headers.get("Pragma"),
                    "accept":self.headers.get("Accept")})+"\n")
            data=b"STALE" if (mode=="stale" or (mode=="bad-once" and n==1)) else body
            self.send_response(200); self.send_header("Content-Length",str(len(data))); self.end_headers(); self.wfile.write(data)
        def log_message(self,*a):
            pass
    return H
for spec in sys.argv[3:]:
    name,mode=spec.split(":")
    httpd=ThreadingHTTPServer(("127.0.0.1",0), make(name, mode))
    print("%s %d"%(name, httpd.server_address[1]), flush=True)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
threading.Event().wait()
PY
  SRV=$!
  local i
  APEX=""; WWW=""; PAGES=""
  for i in $(seq 1 50); do
    [ "$(grep -c . "$TMP/ports" 2>/dev/null || true)" -ge 3 ] && break
    sleep 0.05
  done
  APEX=$(awk '$1=="apex"{print $2}' "$TMP/ports")
  WWW=$(awk '$1=="www"{print $2}' "$TMP/ports")
  PAGES=$(awk '$1=="pages"{print $2}' "$TMP/ports")
  [ -n "$APEX" ] && [ -n "$WWW" ] && [ -n "$PAGES" ]
}

# run live_verify against the local servers. $1 freeze path, $2 marks
verify() {
  rm -f "$1"
  : > "$TMP/bytecmp.txt"
  VER_OUT=$(KT_LIVE_MARKS="$2" KT_LIVE_HOSTS="http://127.0.0.1:$APEX http://127.0.0.1:$WWW" \
    bash "$ROOT/tools/live_verify.sh" "$SITE" "$TMP/bytecmp.txt" "http://127.0.0.1:$PAGES" "$1" new-deploy-id run1 old-live-id 2>"$TMP/verify.err") && VER_RC=0 || VER_RC=$?
}

headers_ok() {
  python3 - "$TMP/hits.jsonl" <<'PY'
import json,sys
rows=[json.loads(l) for l in open(sys.argv[1]) if l.strip()]
assert rows, "no requests"
cbs=[]
for r in rows:
    assert "cb=" in r["path"], r
    assert (r.get("cache") or "").lower()=="no-cache", r
    assert (r.get("pragma") or "").lower()=="no-cache", r
    assert r.get("accept")=="*/*", r
    cbs.append(r["path"].split("cb=",1)[1])
assert len(set(cbs))==len(cbs), cbs
PY
}

# schedule: a few tries spread over roughly 2-3 minutes, and the real hosts stay the default
python3 - "$ROOT/tools/live_verify.sh" "$ROOT/tools/auto_refresh.sh" "$ROOT/.github/workflows/refresh.yml" <<'PY'
import re,sys,pathlib
live,auto,wf=map(pathlib.Path,sys.argv[1:])
s=live.read_text()
m=re.search(r'KT_LIVE_MARKS:-([0-9,]+)', s)
marks=[int(x) for x in m.group(1).split(",")]
assert len(marks)>=3 and marks==sorted(marks), marks
span=marks[-1]-marks[0]
assert 120<=span<=180, span
assert "https://kicktipmedia.com https://www.kicktipmedia.com" in s
a=auto.read_text()
v=a.index("live_verify.sh"); r=a.index("record_live.sh")
assert r>v
mid=a[v:r]
# mismatch exits before record_live.sh; an edge-lag warning does not
assert mid.count("fail 22")==2
warn=[line for line in mid.splitlines() if "WARNING" in line and "edge-lag" in line]
assert len(warn)==1 and "fail" not in warn[0], warn
assert "> $R/FREEZE" not in a
assert "state.json.tmp" not in a
text=wf.read_text()
assert "pull --rebase --autostash" in text
assert "pull --rebase &&" not in text
step=text.split("Commit FREEZE if a post-deploy check failed",1)[1].split("run: |\n",1)[1]
body=[]
for line in step.splitlines():
    if line.startswith("          "): body.append(line[10:])
    elif line.strip()=="": continue
    else: break
script="\n".join(body)
assert "pull --rebase --autostash" in script and "pull --rebase &&" not in script
print("structure ok")
PY
need $? "schedule, record-on-success wiring, workflow uses pull --rebase --autostash"

# (a) first GET is stale, the retry matches. pages.dev is stale so a missed retry would FREEZE.
start_srv apex:bad-once www:good pages:stale
need $? "(a) test server"
verify "$TMP/FREEZE" 0,0,0
need $([ "$VER_RC" = 0 ] && [ "$VER_OUT" = ok ] && [ ! -e "$TMP/FREEZE" ]; echo $?) "(a) retry matches: exit 0 tag ok, no FREEZE (rc=$VER_RC tag=$VER_OUT)"
python3 - "$TMP/hits.jsonl" "$TMP/bytecmp.txt" "$TMP/verify.err" <<'PY'
import json,sys
rows=[json.loads(l) for l in open(sys.argv[1]) if l.strip()]
apex=[r for r in rows if r["name"]=="apex"]
www=[r for r in rows if r["name"]=="www"]
pages=[r for r in rows if r["name"]=="pages"]
assert [r["n"] for r in apex]==[1,2], apex
assert len(www)==1 and not pages, (www, pages)
log=open(sys.argv[2]).read(); err=open(sys.argv[3]).read()
assert log.find("mismatch 1")!=-1 and log.find("mismatch 0")>log.find("mismatch 1"), log
assert "mismatch try 1" in err and "checking" not in err, err
PY
need $? "(a) stale then match on retry; pages.dev not consulted"
headers_ok
need $? "(a) retries send a fresh cb= and no-cache headers"
stop_srv

# a clean first try returns immediately (does not sleep into the next mark) and does not FREEZE
start_srv apex:good www:good pages:stale
need $? "first-try server"
rm -f "$TMP/FREEZE"; : > "$TMP/bytecmp.txt"
VER_OUT=$(timeout 5 env KT_LIVE_MARKS=0,30 KT_LIVE_HOSTS="http://127.0.0.1:$APEX http://127.0.0.1:$WWW" \
  bash "$ROOT/tools/live_verify.sh" "$SITE" "$TMP/bytecmp.txt" "http://127.0.0.1:$PAGES" "$TMP/FREEZE" new-deploy-id run1 old-live-id 2>"$TMP/verify.err") && VER_RC=0 || VER_RC=$?
need $([ "$VER_RC" = 0 ] && [ "$VER_OUT" = ok ] && [ ! -e "$TMP/FREEZE" ]; echo $?) "first try match stops (no 30s wait, no FREEZE) rc=$VER_RC tag=$VER_OUT"
stop_srv

# (b) apex never matches; pages.dev does. Record the live base the way a successful run does.
start_srv apex:stale www:stale pages:good
need $? "(b) test server"
verify "$TMP/FREEZE" 0,0,0
need $([ "$VER_RC" = 0 ] && [ "$VER_OUT" = edge-lag ] && [ ! -e "$TMP/FREEZE" ]; echo $?) "(b) edge-lag: exit 0, no FREEZE (rc=$VER_RC tag=$VER_OUT)"
python3 - "$TMP/hits.jsonl" "$TMP/verify.err" <<'PY'
import json,sys
rows=[json.loads(l) for l in open(sys.argv[1]) if l.strip()]
apex=[r for r in rows if r["name"]=="apex"]
pages=[r for r in rows if r["name"]=="pages"]
assert len(apex)==3 and [r["n"] for r in apex]==[1,2,3], apex
assert len(pages)==1, pages
assert "checking" in open(sys.argv[2]).read()
PY
need $? "(b) three apex mismatches, then one pages.dev match"
headers_ok
need $? "(b) pages.dev check is cache-busted too"
R=$TMP/rec
mkdir -p "$R/runs/t1/deploy" "$R/pipeline/snap/site"
printf 'zip-bytes' > "$R/runs/t1/kicktip-site.zip"
printf '%s\n' '{"live_id":"old-live-id","live_sha":"oldsha"}' > "$R/state.json"
KT_ROOT=$R RD=$R/runs/t1 NEW_ID=new-deploy-id NEW_SHA=newsha ASOF="2026-11-09 15:44 MT" \
  FP1=fp DONE=685 LFP1=lfp LEP1=1794264219 SNAP=$R/pipeline/snap LIVE_ID=old-live-id RUN=t1 KT_RELATIVE=1 \
  bash "$ROOT/tools/record_live.sh"
need $? "(b) record_live.sh"
python3 - "$R" <<'PY'
import json,sys
R=sys.argv[1]
s=json.load(open(R+"/state.json"))
assert s["live_id"]=="new-deploy-id", s.get("live_id")
assert s["live_sha"]=="newsha"
assert s["zip_path"]=="runs/t1/kicktip-site.zip", s.get("zip_path")
assert s["site_dir"]=="runs/t1/deploy"
assert s["s0_pipeline_site"]=="pipeline/snap/site"
assert s["rollback_id"]=="old-live-id"
assert s["as_of"]=="2026-11-09 15:44 MT"
assert s["results_fp"]=="fp" and s["lines_fp"]=="lfp"
assert s["completed"]==685 and s["lines_epoch"]==1794264219 and s["run"]=="t1"
prev=json.load(open(R+"/state.prev.json"))
assert prev["live_id"]=="old-live-id" and prev["live_sha"]=="oldsha"
r=json.load(open(R+"/runs/t1/result.json"))
assert "live_id" in r and r["exit"]==0 and r["live_id"]=="new-deploy-id" and r["sha"]=="newsha"
assert r["zip"].endswith("/runs/t1/kicktip-site.zip"), r["zip"]
assert r["s0"].endswith("/pipeline/snap/site")
assert r["completed"]==685 and r["lines_epoch"]==1794264219
PY
need $? "(b) state live_id / live_sha / base zip recorded, rollback kept"
stop_srv

# (c) pages.dev mismatches -> FREEZE, state not recorded, FREEZE push survives a dirty worktree
export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null GIT_TERMINAL_PROMPT=0
G=$TMP/git
mkdir -p "$G"
git init -q -b main --bare "$G/remote.git"
git init -q -b main "$G/a"
git -C "$G/a" remote add origin "$G/remote.git"
printf '%s\n' '{"live_id":"old-live-id"}' > "$G/a/state.json"
printf 'v1\n' > "$G/a/tracked.txt"
git -C "$G/a" add state.json tracked.txt
git -C "$G/a" -c user.name=kicktipmedia -c user.email=kicktipmedia@users.noreply.github.com commit -qm init
git -C "$G/a" push -q -u origin main
git clone -q "$G/remote.git" "$G/b"
printf 'remote-only\n' > "$G/b/other.txt"
git -C "$G/b" add other.txt
git -C "$G/b" -c user.name=kicktipmedia -c user.email=kicktipmedia@users.noreply.github.com commit -qm 'remote commit'
git -C "$G/b" push -q
printf 'dirty\n' >> "$G/a/tracked.txt"
start_srv apex:stale www:stale pages:stale
need $? "(c) test server"
verify "$G/a/FREEZE" 0,0,0
need $([ "$VER_RC" = 22 ] && [ -z "$VER_OUT" ]; echo $?) "(c) pages.dev mismatch exits 22 (rc=$VER_RC)"
FREEZE_BODY=$(cat "$G/a/FREEZE" 2>/dev/null || true)
need $([ "$FREEZE_BODY" = "byte-compare failed after deploy new-deploy-id run run1; rollback to old-live-id" ]; echo $?) "(c) FREEZE written"
python3 - "$G/a/state.json" "$TMP/hits.jsonl" <<'PY'
import json,sys
s=json.load(open(sys.argv[1]))
assert s=={"live_id":"old-live-id"}, s
rows=[json.loads(l) for l in open(sys.argv[2]) if l.strip()]
pages=[r for r in rows if r["name"]=="pages"]
assert len(pages)==1, pages
assert (pages[0].get("cache") or "").lower()=="no-cache"
PY
need $? "(c) live base not recorded; pages.dev was compared"
stop_srv
# the old pull (no --autostash) must still fail here, then the workflow step itself must push
python3 - "$ROOT/.github/workflows/refresh.yml" "$TMP/freeze_step.sh" <<'PY'
import pathlib,sys
text=pathlib.Path(sys.argv[1]).read_text()
step=text.split("Commit FREEZE if a post-deploy check failed",1)[1].split("run: |\n",1)[1]
body=[]
for line in step.splitlines():
    if line.startswith("          "): body.append(line[10:])
    elif line.strip()=="": continue
    else: break
pathlib.Path(sys.argv[2]).write_text("\n".join(body).strip()+"\n")
PY
need $? "(c) extracted FREEZE step"
(
  cd "$G/a"
  neg=$(git pull --rebase 2>&1) && neg_rc=0 || neg_rc=$?
  printf '%s\n' "$neg" > "$TMP/neg.txt"
  printf '%s\n' "$neg_rc" > "$TMP/neg.rc"
)
need $([ "$(cat "$TMP/neg.rc")" != 0 ] && grep -q 'unstaged changes' "$TMP/neg.txt"; echo $?) "(c) pull --rebase without --autostash fails on the dirty tree"
(
  cd "$G/a"
  bash "$TMP/freeze_step.sh" >"$TMP/push.txt" 2>&1
) && push_rc=0 || push_rc=$?
need $push_rc "(c) FREEZE push with --autostash succeeds on the dirty tree"
[ "$(git -C "$G/a" status --porcelain)" = " M tracked.txt" ] && porcelain_ok=0 || porcelain_ok=1
need $porcelain_ok "(c) unstaged edit is still unstaged after the push ($(git -C "$G/a" status --porcelain | tr '\n' ' '))"
git -C "$G/a" diff -- tracked.txt | grep -q '^+dirty$'
need $? "(c) dirty line preserved in the worktree"
git -C "$G/a" log --format=%s origin/main > "$TMP/subjects.txt"
need $([ "$(cat "$TMP/subjects.txt")" = "$(printf '%s\n' 'FREEZE after failed post-deploy check' 'remote commit' init)" ]; echo $?) "(c) FREEZE commit rebased onto the remote and pushed"
git --git-dir="$G/remote.git" show HEAD:FREEZE > "$TMP/remote-freeze.txt"
need $([ "$(cat "$TMP/remote-freeze.txt")" = "$FREEZE_BODY" ]; echo $?) "(c) remote FREEZE matches the file live_verify wrote"
git --git-dir="$G/remote.git" show HEAD:state.json | python3 -c 'import json,sys; assert json.load(sys.stdin)["live_id"]=="old-live-id"'
need $? "(c) pushed tree did not record a new live base"
git -C "$G/a" show HEAD:tracked.txt | grep -qx 'v1'
need $? "(c) the dirty edit was not committed"

echo SUITE_DONE fail=$fail
exit $fail
