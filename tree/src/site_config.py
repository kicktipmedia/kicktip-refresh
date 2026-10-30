"""Single source of truth for the public KickTip host. build.py, tests/audit.py, tests/site_test.py and tests/host_test.py import this.
Changing the host = change this one line, rebuild, run tests/host_test.py. Apex is canonical, no trailing slash; www redirects to the apex at the edge."""
SITE_URL = "https://kicktipmedia.com"
OLD_HOSTS = ("kicktip.pages.dev",)   # strings that must not appear in shipped files (tests/host_test.py), except ALLOWED_OLD_HOST_FILES
ALLOWED_OLD_HOST_FILES = {}          # rel path -> reason; empty for dom1 (the 301 lives at the edge, not in the zip)
MYTEAMS_CAP_LOCAL = 10   # My teams: most teams kept on this device without an account (phase 2 raises it to 50 only for a signed-in visitor, enforced server side)
# ---- /privacy/ page and sign-in copy (Creative's PRIVACY-COPY.md sha 0dfdf2668896; CEO decisions Oct 25) ----
PRIVACY_UPDATED = "October 25, 2026"   # "Last updated" on /privacy/ (publish date, Mountain Time); change when the page text changes
PRIVACY_CONTACT_EMAIL = "support@kicktipmedia.com"             # the ONE place for the privacy contact. Empty (default) = "KickTip does not have a privacy inbox..." text. A value = "Write to <address>" (plain text + mailto link)
PHASE3_EMAIL_LINK = False              # phase 3 flag: True adds the email-link section, its processors and its storage sentence on /privacy/. Off: those lines are absent from the build
EMAIL_LINK_TTL_SECONDS = 900           # the ONE magic-link lifetime (15 minutes, single use; CEO confirmed). Used by the /privacy/ wording and, in phase 3, injected into _worker.js and the 0003 migration comment
