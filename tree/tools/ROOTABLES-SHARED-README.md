# rootables (rev f, Nov 1) — branch rootables-shared, not merged
Front-end files shipped in the rev f build are snapshotted in kit/rootables-f/ (rootables.js, pk.js, rvhome.js, ktwhy.js, polish.css).
Team page = live card layout + exactly three intended diffs: (1) logos centered in a fixed 52px square (0px offset),
(2) auto-load (no Run tap) with the visible terms line in its place, (3) one <p class="rv-why"><strong>Why:</strong> … under every card's points block
(Creative spec: 8px/8px, 1px #DDE3E6 top rule, 14px/1.4 #121519; 'championship-game' wrapped nowrap; omitted when a game has no why).
bake_static DEF[13] bakes the live ready-state markup (RB.readyHtml) from data/rootables/<slug>.json; client prunes started games only.
Home = rev f rows via rvhome.js row(); pk.js reads the same shared file. Share cards = rev e card3 (ROOT FOR + outline ring as in the rev e mock,
3 games on the wide card) + whole-px logo snap; og_cards reports logo_offset_max_px (0 on both sizes).
gen_rootables: ktwhy optional (why='' when absent). Tests: suite/tests/rootables_shared.js (in tools/suite_subset.sh).
