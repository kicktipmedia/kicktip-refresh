#!/bin/bash
# Offline test for tools/publish_base.sh (no network, no Cloudflare, no GitHub): stub gh, a local bare repo as origin, --no-verify.
# Case A (Nov 25, run 45650845621): s0-inputs upload fails after zip + S0 uploaded -> state.json must still be recorded and pushed (exit 0).
# Case B: kicktip-site.zip upload fails -> exit non-zero, nothing committed, state.json unchanged on origin.
# Case C: all uploads ok -> recorded, s0-inputs uploaded after the state push.
# KT_TEST_DIR overrides the scratch dir (it must allow exec; the box /dev/shm is noexec).
set -u
SRC=$(cd "$(dirname "$0")/../.." && pwd); F=0
T=${KT_TEST_DIR:-$(mktemp -d)}; mkdir -p "$T"; rm -rf "$T"/*
chk() { if [ "$2" = "$3" ]; then echo "ok   $1"; else echo "FAIL $1: got '$2' want '$3'"; F=$((F+1)); fi; }
mkdir -p "$T/bin"; cat > "$T/bin/gh" <<'G'
#!/bin/bash
echo "gh $*" >> "$KT_GH_CALLS"
case "$*" in
  "release view base"*) exit 0;;
  *"release upload base"*kicktip-site.zip*) [ "${KT_FAIL:-}" = zip ] && { echo "HTTP 500" >&2; exit 1; }; exit 0;;
  *"release upload base"*s0-inputs.tar.gz*) [ "${KT_FAIL:-}" = s0in ] && { echo "HTTP 500 (https://api.github.com/repos/x/y/releases/assets/792032807)" >&2; exit 1; }; exit 0;;
  *"release upload base"*) exit 0;;
esac
exit 0
G
chmod +x "$T/bin/gh"
setup() {  # $1 = case dir: bare origin with tools/ + state.json naming the OLD deploy, and a working clone
  local D=$T/$1; mkdir -p "$D/seed/tools" "$D/seed/tree/data/store" "$D/seed/tree/data/out" "$D/seed/tree/data/cache/scoreboard" "$D/s0"
  cp "$SRC/tools/publish_base.sh" "$SRC/tools/retry_cmd.sh" "$D/seed/tools/"
  cat > "$D/seed/state.json" <<J
{
 "live_id": "a378bb91-3c0a-4076-98ff-5b1ca2f3003f",
 "live_sha": "0974a241baacd4e3f8ac6cfed18fba15a8ad8a73f160fda557f32a9633f46400",
 "as_of": "2026-11-25 08:03 MT",
 "results_fp": "635ae7148152d9d7",
 "completed": 824,
 "s0_asset": "s0-site.tar.gz",
 "lines_fp": "d47caa467fbd2e80",
 "lines_epoch": 1795618983
}
J
  echo '{}' > "$D/seed/tree/data/store/espn_lines.json"; echo '{}' > "$D/seed/tree/data/out/refresh_log.json"; echo x > "$D/seed/tree/data/cache/scoreboard/a"
  echo '<html>s0</html>' > "$D/s0/index.html"; echo 'zipbytes' > "$D/site.zip"
  git init -q --bare -b main "$D/origin.git"; (cd "$D/seed" && git init -q -b main && git add -A && git -c user.name=t -c user.email=t@t commit -qm seed && git push -q "$D/origin.git" main) || exit 9
  git clone -q "$D/origin.git" "$D/work"
}
run() {  # $1 case dir, $2 failure mode
  local D=$T/$1; echo "new snapshot" >> "$D/work/tree/data/store/espn_lines.json"
  ( cd "$D/work" && PATH="$T/bin:$PATH" KT_GH_CALLS="$D/calls" KT_FAIL="$2" KT_GH_TRIES=2 KT_GH_BACKOFF=0 TMPDIR="$D" \
    bash tools/publish_base.sh "$D/site.zip" 098a0e90-ded9-4e7f-ae33-074394c22214 --no-verify --s0 "$D/s0" --s0-inputs tree \
      --as-of "2026-11-25 09:05 MT" --fp 635ae7148152d9d7 --completed 824 --lines-fp d0951c9f6ae7b06e --lines-epoch 1795622698 ) > "$D/out" 2>&1
}
remote() { git --git-dir="$T/$1/origin.git" show main:state.json | python3 -c "import json,sys;s=json.load(sys.stdin);print(s['live_id'][:8],s.get('live_sha','')[:12],s['as_of'],s.get('rollback_id','-')[:8],s['lines_fp'])"; }
SHA=$(echo 'zipbytes' | sha256sum | cut -c1-12)
setup A; run A s0in; chk "A exit 0 when only s0-inputs upload fails" "$?" 0
chk "A state.json on origin records the new deploy" "$(remote A)" "098a0e90 $SHA 2026-11-25 09:05 MT a378bb91 d0951c9f6ae7b06e"
chk "A warning printed" "$(grep -c '::warning::s0-inputs.tar.gz upload failed; live 098a0e90' $T/A/out)" 1
chk "A store snapshot committed" "$(git --git-dir=$T/A/origin.git show main:tree/data/store/espn_lines.json | tail -n 1)" "new snapshot"
chk "A upload order zip, s0, s0-inputs" "$(grep -o 'upload base [^ ]*' $T/A/calls | sed 's#.*/##' | uniq | tr '\n' ' ')" "kicktip-site.zip s0-site.tar.gz s0-inputs.tar.gz "
setup B; run B zip; rc=$?; chk "B exit non-zero when the zip upload fails" "$([ $rc -ne 0 ] && echo nz)" nz
chk "B origin state.json unchanged" "$(remote B)" "a378bb91 0974a241baac 2026-11-25 08:03 MT - d47caa467fbd2e80"
chk "B no s0-inputs upload attempted" "$(grep -c s0-inputs $T/B/calls)" 0
setup C; run C ""; chk "C exit 0 all ok" "$?" 0
chk "C recorded" "$(remote C)" "098a0e90 $SHA 2026-11-25 09:05 MT a378bb91 d0951c9f6ae7b06e"
R=$(grep -n 'recorded live' $T/C/out | cut -d: -f1); U=$(grep -n 's0-inputs uploaded' $T/C/out | cut -d: -f1)
chk "C s0-inputs uploaded after the state push" "$([ -n "$R" ] && [ -n "$U" ] && [ "$U" -gt "$R" ] && echo after)" after
[ -z "${KT_TEST_DIR:-}" ] && rm -rf "$T"
echo "publish_base_test: $F failed"; exit $F
