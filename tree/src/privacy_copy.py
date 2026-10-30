"""ONE place for the /privacy/ page copy and the two cookie lines. Source: Creative's PRIVACY-COPY.md (sha 40c2bed37fb8), used verbatim except where this file says otherwise (the storage and cookie tables are completed from the real keys in the build; see STORAGE_ROWS / COOKIE_ROWS).
Config lives in src/site_config.py (PRIVACY_CONTACT_EMAIL, PRIVACY_UPDATED, PHASE3_EMAIL_LINK, EMAIL_LINK_TTL_SECONDS). Pure functions only (no data, no I/O) so tests/privacy_test.py can render every mode.
Processor names (Google, Resend, Amazon SES, Cloudflare) are allowed on /privacy/ only; the cookie lines below are the only place Google is named in /method/ and /disclaimer/. No apostrophes or backslashes in the cookie lines (copied into JS string literals)."""
import html

COOKIE_LONG = "No cookies unless you sign in. Signing in sets one session cookie, plus a sign-in check cookie that is deleted within ten minutes. No third-party requests until you tap Sign in with Google."
COOKIE_SHORT = "No cookies unless you sign in (a session cookie, plus a ten-minute sign-in check cookie). No third-party requests until you tap Sign in."
OLD_COOKIE_LINE = "No cookies unless you sign in (one session cookie then). No third-party requests until you open the sign-in sheet."   # retired; tests assert it is gone
for _s in (COOKIE_LONG, COOKIE_SHORT): assert "'" not in _s and "\\" not in _s

INTRO = "KickTip is information only, not a betting site. Here is what we collect, why, and how to delete it. We do not sell your data, we show no ads, and we run no analytics."
H_STORE = "What stays in your browser"
H_NOSIGN, H_GOOGLE, H_EMAIL, H_COOKIES, H_OTHERS, H_NOT, H_SAFE, H_DELETE, H_Q = (
    "If you do not sign in", "If you sign in with Google", "If you sign in with an email link", "Cookies", "Who else touches your data",
    "What we do not do", "Keeping you safe", "Delete it", "Questions")
QUESTIONS_NONE = "KickTip does not have a privacy inbox. You can see, change and delete everything we keep about you yourself from My teams and the account menu."   # default: PRIVACY_CONTACT_EMAIL empty (sha 888f7aa89c8c wording)
QUESTIONS_REST = "You can also see, change and delete everything we keep about you yourself from My teams and the account menu."                              # with an address (sha 0dfdf2668896 wording)

# ---- storage tables: every key the shipped build can write (checked against the built JS and _worker.js by tests/privacy_test.py). Nothing else is stored. ----
# (setting, what is saved (key), when it is saved)
STORAGE_ROWS = (
    ("Model choice", "the model you picked, one word (key kicktip_model)", "only after you pick a model other than the default; choosing the default removes it"),
    ("Bracket view", "\"fit\" or \"rounds\" (key kt-bracket-view)", "only after you choose Fit to screen or By round; Full bracket, the default, saves nothing"),
    ("Saved teams", "the teams you follow, up to 10 on a device (key kicktip_teams)", "only after you tap Save on My teams; Clear on My teams removes them"),
    ("Headline number", "which race number you chose to show first for each saved team (Make the 12, Reach CCG, Win conference or First-round bye) (key kicktip_lead)", "only after you tap Save on My teams, together with your saved teams"),
    ("Signed-in marker", "the first letter of your name or email, so the page can show it without a flash (key kicktip_acct)", "only after you sign in; removed when you sign out"),
    ("Sign-in reminder", "the time you tapped Not now, so we do not offer sign-in again for 14 days (key kicktip_nudge)", "only after you tap Not now on the sign-in sheet"),
)
STORE_AFTER = "These stay on your device. Your model choice, bracket view and the two small sign-in markers are never sent to us. Your saved teams are sent to us only if you sign in and choose to add them to your account."
# (cookie, what it does, how long, when it is set)
COOKIE_ROWS = (
    ("__Host-kt_session", "keeps you signed in on this device", "up to 30 days, or until you sign out", "only after you sign in"),
    ("__Host-kt_oauth", "protects the sign-in from a forged request", "deleted when you return; never longer than ten minutes", "only while you go to Google and back"),
)

def storage_table_html():
    E = html.escape
    rows = "".join(f'<tr><th scope="row" data-l="Setting">{E(a)}</th><td data-l="Saved in your browser">{E(b)}</td><td data-l="When it is saved">{E(c)}</td></tr>' for a, b, c in STORAGE_ROWS)
    return f'<div class="tw pvw"><table class="fld pvt" aria-label="What KickTip saves in your browser"><thead><tr><th scope="col">Setting</th><th scope="col">Saved in your browser</th><th scope="col">When it is saved</th></tr></thead><tbody>{rows}</tbody></table></div>'

def cookie_table_html():
    E = html.escape
    rows = "".join(f'<tr><th scope="row" data-l="Cookie">{E(a)}</th><td data-l="What it does">{E(b)}</td><td data-l="How long">{E(c)}</td><td data-l="When it is set">{E(d)}</td></tr>' for a, b, c, d in COOKIE_ROWS)
    return f'<div class="tw pvw"><table class="fld pvt" aria-label="The two cookies KickTip can set"><thead><tr><th scope="col">Cookie</th><th scope="col">What it does</th><th scope="col">How long</th><th scope="col">When it is set</th></tr></thead><tbody>{rows}</tbody></table></div>'

def email_link_minutes(ttl_seconds):
    assert ttl_seconds % 60 == 0 and ttl_seconds > 0
    return ttl_seconds // 60

def questions_html(contact):
    contact = (contact or "").strip()
    if not contact: return f"<p>{html.escape(QUESTIONS_NONE)}</p>"
    a = html.escape(contact)
    # The address is visible text inside the one mailto link. The email_off comments are Cloudflare's documented opt-out: Email Address Obfuscation (a zone setting) must not rewrite it into [email protected] + /cdn-cgi/l/email-protection.
    return f'<p>Write to <!--email_off--><a href="mailto:{a}">{a}</a><!--/email_off--> to ask about your data or to have it deleted. {html.escape(QUESTIONS_REST)}</p>'

def privacy_body(contact="", phase3=False, updated="", ttl_seconds=900):
    """-> (hero paragraph, body html). The email-link section, its storage sentence and the Resend / Amazon SES bullet are shown only when phase3 is True."""
    E = html.escape
    p = []
    p.append(f"<p><em>Last updated: {E(updated)}</em></p>")
    p.append(f"<h2>{H_NOSIGN}</h2><p>You can use all of KickTip without an account. Without signing in, we set no cookies and we keep no profile of you. Your model choice and bracket view, if you save them, stay in your own browser on your own device and are never sent to us. Teams you follow stay there too unless you sign in; then they're saved to your account. You can clear what is in your browser any time from My teams or by clearing your browser's site data.</p>")
    p.append(f'<h2>{H_STORE}</h2><p class="ccgdef">CCG = conference championship game</p>{storage_table_html()}<p>{STORE_AFTER}</p>')
    p.append(f"<h2>{H_GOOGLE}</h2><p>We keep your Google account id, your email address, your name if Google shares it, and the teams and headline numbers you save. We use them for one thing: showing your saved teams on every device you sign in on. We ask Google only for your id, email and name. We do not see your Google password, contacts or anything else in your Google account.</p>")
    if phase3:
        p.append(f"<h2>{H_EMAIL}</h2><p>You type your email address and we send you a one-time link. We keep your email address and your saved teams, the same as with Google. To deliver the message, your address is passed to two email services that send it for us, Resend and Amazon SES. They handle it only to deliver the link. The link works once and expires after {email_link_minutes(ttl_seconds)} minutes.</p>")
    p.append(f"<h2>{H_COOKIES}</h2><p>We set no cookies unless you sign in. When you sign in we set one session cookie that keeps you signed in on that device for up to 30 days, until you sign out. While you go to Google and back we also set a sign-in check cookie that protects you from a forged sign-in. It is deleted when you return and never lasts more than ten minutes. Neither cookie is used for advertising or tracking.</p>{cookie_table_html()}")
    li = ["<li>Google, only when you tap Sign in with Google.</li>"]
    if phase3: li.append("<li>Resend and Amazon SES, only if you use an email link.</li>")
    li.append("<li>Our web host and database provider, Cloudflare (our database is Cloudflare D1), which store and deliver the site and your saved teams.</li>")
    p.append(f"<h2>{H_OTHERS}</h2><ul>{''.join(li)}</ul><p>We do not share your information with anyone else.</p>")
    p.append(f"<h2>{H_NOT}</h2><p>We do not sell or rent your data. We show no ads. We run no analytics or tracking. We do not use your information to make predictions about you. Everything on KickTip is information only; make no decision based on this material.</p>")
    p.append(f"<h2>{H_SAFE}</h2><p>To limit abuse we count sign-in attempts and saves using a scrambled form of your connection address. We do not keep the address itself.</p>")
    p.append(f"<h2>{H_DELETE}</h2><p>Open the account menu and choose Delete my account. That removes your account, your email address and every saved team from our server. Signing out ends your sign-in on every device you use and removes the session cookie from this one. Teams saved only on a device stay there until you clear them.</p>")
    p.append(f"<h2>{H_Q}</h2>{questions_html(contact)}")
    p.append('<p>See also: <a href="/disclaimer/">Full disclaimer</a> and <a href="/method/">How we make the numbers</a>.</p>')
    return INTRO, "".join(p)
