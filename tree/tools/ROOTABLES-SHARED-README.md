# rootables-shared (WIP, on HOLD since Oct 31 11:54 PM MT). Do not merge.

## Done (in this branch)
- tools/gen_rootables.js (new): writes ONE file per team, data/rootables/<slug>.json, using the browser's own rootables.js compute(tn,'blend'): max(playoff, reach-conf-championship) swing, own games left off, 1.0 pt threshold, cap 8, plus ktwhy.js why text. It is ASCII-escaped, has --check, and fails if fewer than 130 teams.
- tools/og/og_rows.js: share cards read the shared file. Games, order and gains are identical to the old path for all 138 teams. It fails on a stale as_of.
- tools/og/card3.py and og_cards.py: the mock og-d layout (wide 3 + '+N more', tall 8, why strip, logo discs).
  - Long-why fit: step the font down to 85%, then drop the closing '(...)', then drop the clause before ', so '. No ellipsis.
  - Root-panel outline is behind KT_OG_ROOT_OUTLINE=1 (off). This is UNCONFIRMED.
- tools/bake_static.js: DEF[13] bakes the visible team-page list (RB.panelHtml) from the shared file. Entities only. The old DEF[9] noscript path is kept as a fallback.
- tools/apply_data.py: a gen_rootables step runs before tile-data. The allow-list accepts new data/rootables/*.json.
- tools/build_tile_data.py: the Python Rootables port ('r') is retired.
- src/whatif.py: the index label now uses the real season count (f"{N:,}"), not the hard-coded 10,000.

## Site-side work (not in this repo)
Archive: /workspace/hub/kicktip-rootables-fix/wip/site-rootables-shared-wip.tar.gz (working copy /workspace/rtb/site).
- rootables.js: pure panelHtml/homeRows/shareP. No Run gate. The baked list is hydrated, started games are pruned, and the blend redraws from the shared file.
- pk.js: tile 3 reads the shared file and draws KTRvHome.row.
- rvhome.js, ktwhy.js, kt.css (logo slot centering), polish.css, ktsp.* (rev3.2 pill hide), restamped ?v tokens, 138 team pages re-baked, 276 cards re-rendered.

## HELD / to undo per Jared (Oct 31 11:54 PM MT)
- TEAM PAGE must stay as live, except for logo centering. Before shipping, revert the team page to the live layout:
  - drop Variant A (why on every card), the .rv-root / ROOT FOR outline, and the panelHtml card changes;
  - re-decide the Run tap and terms line with Jared.
  - The shared-file bake can keep feeding the live card markup.
- HOME row design: wait for Creative rev f. rvhome.js row() is the single swap point.
- Share-card layout and outline: unconfirmed (isolated in card3.py and KT_OG_ROOT_OUTLINE).

## Not done
- The check-2 dry run (fresh clone, auto_refresh.sh --no-deploy --force) was stopped at HOLD before it finished.
- Suite not run. Tests for gen_rootables/bake DEF[13] not written.
- No ship zip, no Preview deploy of this state.
