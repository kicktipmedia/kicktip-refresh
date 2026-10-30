# KickTip sticky slim header kit (Creative FINAL spec, sticky-1025/SPEC.md sha 0b33878670d0)

Apply to any KickTip build tree (a `build/site` dir or an extracted zip), in place:

    python3 src/header-kit/apply_header.py <site_dir>              # option P (default)
    python3 src/header-kit/apply_header.py <site_dir> --variant q  # option Q
    python3 src/header-kit/apply_header.py <site_dir> --dry-run    # report only

It is idempotent (second run = same bytes) and needs no build data, so run it LAST, on top of bracket Fit, simulator, My teams, data refreshes, etc.
`src/build.py` also calls it at the end of build() (`KT_HDR=q` builds Q, `KT_HDR=off` skips it).

**Switch P <-> Q:** change `VARIANT = os.environ.get("KT_HDR", "p")` at the top of apply_header.py to `"q"` (one line), or pass `--variant q` / `KT_HDR=q`.

## Files it touches in the site tree
- every `*.html` containing `<header class="hd">` (156 pages today): the header block is replaced (same logo, pill and 4 nav links, plus Menu button + panel for P) and two tags go in `<head>` right after the kt.css link: `hdr.css?v=<hash>` and `hdr.js?v=<hash>` (hash = first 10 hex of sha256, same scheme as the other assets)
- adds `assets/hdr.css`, `assets/hdr.js`
- NOT touched: kt.css, kt.js, chat.js, chat.css (chat.css already uses `.hdp`; all header classes here are `.kh*` so nothing collides), _headers, sitemap.xml, data/, page bodies. No new images (uses the live `assets/brand/icon/kicktip-icon-transparent.png` for the 320px shield).
- `<header class="hd">` stays exactly that string (tests and chat.js look it up by it); the banner `.tb` stays above it in normal flow.

## Contract for other code
- `--kt-bar-h` on `:root` = pinned bar height without safe-area (56px, 64px at 1101+, 52px for Q; `0px` when the bar is not sticky: no JS, or browser without `overflow-x:clip`). Use `top:calc(var(--kt-bar-h,0px) + env(safe-area-inset-top,0px))` (the simulator's scrolled bar does). Fixed bars should use z-index below 7 to sit under the header and its Menu panel; Ask pill 8 / scrim 9 / panel 10 stay above it.
- `.kt-below-bar` = ready-made `position:sticky` with that top, for future sticky-top elements.
- Anchors: elements with an id inside `main`, `footer`, `.src` get `scroll-margin-top = bar + safe-area + 12px`.
