-- Phase 3 (email-link sign-in, approved by the CEO to follow Google sign-in). The table is created now so the schema is ready; NO route reads or writes it in phases 1-2.
-- A token is 32 random bytes shown to the person once (in the emailed link); only its SHA-256 is stored. Single use (used_at), expires EMAIL_LINK_TTL_SECONDS (900 s = 15 minutes) after created_at. The one constant lives in src/site_config.py (injected into _worker.js).
CREATE TABLE IF NOT EXISTS email_tokens (
  token_hash TEXT    PRIMARY KEY,                -- hex SHA-256 of the token; the token itself is never stored
  email      TEXT    NOT NULL,                   -- lower-cased address the link was sent to
  created_at INTEGER NOT NULL,                   -- unix seconds
  expires_at INTEGER NOT NULL,                   -- created_at + EMAIL_LINK_TTL_SECONDS (15 minutes)
  used_at    INTEGER                             -- NULL until the POST /api/auth/email/verify that consumes it
);
CREATE INDEX IF NOT EXISTS email_tokens_exp ON email_tokens(expires_at);
