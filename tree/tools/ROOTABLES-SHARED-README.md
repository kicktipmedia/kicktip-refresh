# rootables-shared (Nov 1 direction) — not merged, not deployed
Team page: live card layout unchanged. Only changes: (1) logos centered in a fixed 52px square (grid, object-fit:contain; measured 0px offset),
(2) auto-load (no Run tap) with the visible terms line in its place. bake_static DEF[13] bakes the LIVE ready-state markup
(RB.readyHtml) from data/rootables/<slug>.json; the client sees the baked rows and only prunes started games (no redraw).
Share cards (og/card3.py): live layout, outline OFF; logos centered in fixed square boxes; og_cards.py reports logo_offset_max_px (0 on both sizes).
gen_rootables: ktwhy optional (why='' when absent). build_tile_data: unchanged vs main (home is HELD for rev f; home differs only by polish.css ?v).
Tests: suite/tests/rootables_shared.js (gen --check, schema, bake verify/check/idempotent/unbake round-trip, one terms line, no Run tap).
Variant A archived: /workspace/hub/kicktip-rootables-fix/wip/site-rootables-shared-wip.tar.gz.
