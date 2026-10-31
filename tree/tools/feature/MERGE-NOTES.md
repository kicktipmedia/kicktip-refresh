# merged-v1 (trim rev b + polish rev b + nojs v1) pipeline notes. NOT pushed; rebase onto refreshfix (spreads fix) before use.
Feature build: /workspace/hub/kicktip-merge/build.sh (siteCC + trim2b + polish tools + nojs unbaked merge + merge_fix.py + bake + bump_all).

What apply_data needs so a refresh keeps the merged changes:
1. tools/bake_static.js MUST be this version. DEF[5] changed (trim's "Turn on JavaScript to see the chances..." text) and the
   stamp placement moved (after <div data-vroot>, spreads 'updated'). The nojs-v1 baker would unbake DEF[5] to the old
   "view predictions ... spread numbers" text and fail the home 'top12 stamp' anchor -> revert/exit 3.
2. Step 5a (new): tools/polish_refresh.py re-derives the polish chances-card record line <p class="pc-sub"> from the merged page
   text; without it the record is frozen at feature-build time (apply_polish.py is idempotent by marker and never recomputes).
3. S0 merge base must be regenerated from tree/src with trim's template patch (in this commit: build.py, terms_copy.py,
   method_copy.py, assets/kt.js) so S0/S1 HTML carry the trimmed terms; otherwise merge3 sees feature-only lines as S0!=live
   and data changes on neighbouring tags can conflict (exit 2). Polish/no-JS HTML are applied to the LIVE base only; S0/S1 never
   carry polish markup, which is fine because merge3 only replays S0->S1 data diffs.
4. Static stamps: polish revb's literal stamps are now bk:3 markers (bake owns them); step 5 restamps data-asof, bake rewrites text.
5. state.json/RUNBOOK proof re-baseline after the merged Production deploy (live id, sha, zip path).
