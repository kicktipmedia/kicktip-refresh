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
RUN_FULL_TEXT = "Information only. Don't make decisions based on this material."   # revb: CEO-approved wording ("should" is banned); the apostrophe is emitted as &#39; so the string is safe inside JS single quotes   # trim2: the full terms, inside the Terms dropdown
RUN_LEAD_TEXT = "Tapping Run accepts the terms"   # trim2 (What If B4f format): the one visible line under Run
REVIEW_LEAD_TEXT = "Tapping Review accepts the terms"
MID_TEXT = "KickTip is not a betting site"   # only where no other not-a-betting-site line is visible in that state
RUN_SHORT_TEXT = RUN_FULL_TEXT   # trim2: same gate line under Run Rootables again
SIGNIN_TEXT = "By signing in, you accept the terms: information only, not a betting site."   # directly under the official Google button in the sign-in sheet (phase 2)
SAVE_TEXT = ""   # trim1: no per-button terms line by Save; the page banner is the one visible notice       # directly under every My teams Save control (WORDING.md, rungate)
for _s in (SIGNIN_TEXT, SAVE_TEXT, RUN_LEAD_TEXT, REVIEW_LEAD_TEXT, MID_TEXT): assert "'" not in _s and "\\" not in _s and "\n" not in _s
for _s in (BANNER_BOLD, BANNER_REST, TERMS_LINK, TERMS_HREF): assert "'" not in _s and "\\" not in _s and "\n" not in _s
def _e(t): return html.escape(t).replace("&#x27;", "&#39;")   # revb
def _rn(text, cls=""): return f'<p class="rn{cls}">{html.escape(text)} <a href="{TERMS_HREF}">{html.escape(TERMS_LINK)}</a></p>'
def gate_html(lead=RUN_LEAD_TEXT, mid=False):   # trim2: "Tapping Run accepts the terms · Terms ⌄", full terms in a <details> dropdown (works without JS); styles .rtg in assets/kt.css
    m = html.escape(MID_TEXT) + " \u00b7 " if mid else ""
    return (f'<div class="rn rtg"><span class="rtg1">{html.escape(lead)} \u00b7 {m}</span><details class="rtgd"><summary>Terms<span class="w2ch" aria-hidden="true"></span></summary>'
            f'<p>{_e(RUN_FULL_TEXT)} <a href="{TERMS_HREF}">{html.escape(TERMS_LINK)}</a></p></details></div>')
RUN_FULL_HTML = gate_html()
RUN_SHORT_HTML = gate_html()
REVIEW_HTML = f'<p class="rn rvn">{_e(REVIEW_LEAD_TEXT)}. {_e(RUN_FULL_TEXT)} <a href="{TERMS_HREF}">{_e(TERMS_LINK)}</a></p>'   # revb: Review line is always the full version; Run is always the short dropdown
BANNER_HTML = f'<div class="tb" role="note"><div class="w"><b>{html.escape(BANNER_BOLD)}</b> {html.escape(BANNER_REST)}</div></div>'
SAVE_HTML = ""
SIGNIN_HTML = _rn(SIGNIN_TEXT)
