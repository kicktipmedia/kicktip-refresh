"""ONE place for the run-gate wording (FINAL, Creative's WORDING.md 242613ed7945 / SPEC-rungate.md c7011e1ba9e5, Oct 24, 2026). Edit the strings below, then rebuild (python3 src/build.py); nothing else changes.
BANNER_BOLD + BANNER_REST : the slim graphite banner at the top of EVERY page (first sentence white bold). No link, no dismiss.
RUN_FULL_TEXT / RUN_SHORT_TEXT : the static line under every Run control (FULL under the Ask KickTip composer and the Run Rootables button; SHORT under Run Rootables again).
TERMS_LINK : label of the link in that line (target TERMS_HREF = /disclaimer/, which carries the full terms).
No apostrophes or backslashes (the strings are copied into JS string literals and HTML)."""
import html
TERMS_HREF = "/disclaimer/"
TERMS_LINK = "Full terms"
BANNER_BOLD = "KickTip is not a betting site."
BANNER_REST = "Information only; make no decision based on this material."
BANNER_TEXT = BANNER_BOLD + " " + BANNER_REST
RUN_FULL_TEXT = "By tapping Run, you accept the terms: KickTip is information only, not a betting site, and no decision should be made based on this material."
RUN_SHORT_TEXT = "By tapping Run, you accept the terms: information only, not a betting site."
SIGNIN_TEXT = "By signing in, you accept the terms: information only, not a betting site."   # directly under the official Google button in the sign-in sheet (phase 2)
SAVE_TEXT = "By tapping Save, you accept the terms: information only, not a betting site."       # directly under every My teams Save control (WORDING.md, rungate)
for _s in (SIGNIN_TEXT, SAVE_TEXT): assert "'" not in _s and "\\" not in _s and "\n" not in _s
for _s in (BANNER_BOLD, BANNER_REST, RUN_FULL_TEXT, RUN_SHORT_TEXT, TERMS_LINK, TERMS_HREF): assert "'" not in _s and "\\" not in _s and "\n" not in _s
def _rn(text, cls=""): return f'<p class="rn{cls}">{html.escape(text)} <a href="{TERMS_HREF}">{html.escape(TERMS_LINK)}</a></p>'
RUN_FULL_HTML = _rn(RUN_FULL_TEXT)
RUN_SHORT_HTML = _rn(RUN_SHORT_TEXT, " s")
BANNER_HTML = f'<div class="tb" role="note"><div class="w"><b>{html.escape(BANNER_BOLD)}</b> {html.escape(BANNER_REST)}</div></div>'
SAVE_HTML = _rn(SAVE_TEXT)
SIGNIN_HTML = _rn(SIGNIN_TEXT)
