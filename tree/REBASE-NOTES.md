# REBASE-NOTES (p2d = My teams / account / privacy / header, rebased on LIVE sim5, deploy b7a38ffd)

Base for the overlay: live sim5 tree (`/workspace/kicktip-sim5`, zip sha c46845a4c550). p2d changes NOTHING in:
`src/assets/ccgsim.js`, `src/assets/ccgsim-ui.js`, `src/assets/ccgsim.css`, `src/ccgsim_data.py`, `tests/ccgsim_browser.py` (all byte-identical to sim5; verify with `cmp`).
Built `assets/ccgsim*.js|css` in the zip are byte-identical to the live sim5 files too (only their `?v=` tokens on pages depend on those bytes).

## What touches the 10 simulator pages (`/conference/<c>/simulator/`), and only that
All 10 are produced by `sim_page()` -> `page()` in `src/build.py`. p2d adds nothing to `sim_page()` itself. The simulator pages get these p2d changes ONLY through shared code:

1. `NAV` tuple (build.py ~l.133): inserts `("My teams", "/#my-teams")` before Method. Shows in the header nav of every page.
2. `page()` (~l.165-177): appends `bracket-fit` (only ptype=="playoff", so NOT the simulators), and for EVERY page appends `<script src=/assets/myteams.js defer>`, `<script src=/assets/account.js defer>` and the `myteams.css` link. This is the account/header hook set. Nothing else is injected into `<head>`/body of a simulator page.
3. Footer (`FOOT`, ~l.191-193): adds `<a href="/privacy/">Privacy</a>` after "Full disclaimer".
4. `apply_header.apply(SITE)` at the end of the build (header kit, unchanged since header3b + p2c): rewrites header markup on all 167 pages incl. the 10 simulators (adds hdr.css/hdr.js links, Menu button, Ask pill).
5. `hero_html(..., after="")` new optional arg (only the team page passes it). No effect on simulators.

Everything else in build.py (privacy_page(), `_mj`/`_aj` asset substitution, `_worker.js` / `_routes.json` writers, robots `Disallow: /api/`, method/disclaimer wording) never touches a simulator page.

## sim5 build.py hunks that p2d keeps untouched (so a rebase has no conflict there)
`SIM_FAV_LABEL`, the `sim_page` docstring and its `src_extra`. A sim6 rebase should only conflict, if at all, inside the `page()` function (hunk 2) if sim6 also edits the script/extra lines; resolve by keeping both sets of script tags.

## Hash tokens
`hash_assets()` gives `?v=` tokens by content, so a sim6 change to ccgsim.* changes only those tokens; p2d adds none for ccgsim.*.

## Non-ccgsim shared files that differ from live sim5 (expected; both are header-kit/My teams hooks from p2b/p2c, not simulator code)
`assets/kt.js` (comment reword + 3-line account hook), `assets/hdr.js` (Menu/Ask/account Esc handling), `robots.txt` (+`Disallow: /api/`), `sitemap.xml` (+/privacy/). New files: `_worker.js`, `_routes.json`, `assets/account.js`, `assets/myteams.js`, `assets/myteams.css`, `privacy/index.html`. All 166 existing pages change (header, footer Privacy link, hooks); method/disclaimer also get the storage wording.

## p2e (rebased on sim6b; Oct 25)
Sources: sim6 `ccgsim.js`/`ccgsim-ui.js` + sim6b's `ccgsim.css` (taken from the sim6b zip), `tests/ccgsim_browser.py` from sim6. `build.py` = 3-way merge (ours p2d, base sim5, theirs sim6), clean; sim6's hunks are the `sim_page` script line (adds lg.js) and `SIM_FAV_LABEL`/`src_extra` wording. p2d's only simulator-page hooks remain the `page()`/NAV/footer/apply_header ones listed above. Built ccgsim.js, ccgsim-ui.js and ccgsim.css are byte-identical to the sim6b zip (css ?v=79ade217cc).
