-- KickTip accounts (phase 2). D1 (SQLite). Run in the D1 console (or `wrangler d1 migrations apply`) BEFORE the first deploy that has sign-in.
-- Stores ONLY: Google account id (sub), email, optional display name, created_at, and the followed teams with their lead-number choice.
CREATE TABLE IF NOT EXISTS users (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  google_sub   TEXT    NOT NULL UNIQUE,
  email        TEXT    NOT NULL,
  display_name TEXT,
  created_at   INTEGER NOT NULL,                 -- unix seconds
  sess_ver     INTEGER NOT NULL DEFAULT 1        -- bump to invalidate every session cookie of this user
);
CREATE TABLE IF NOT EXISTS saved_teams (
  user_id   INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  slug      TEXT    NOT NULL,                    -- validated against the real team list by the Worker
  lead      TEXT    NOT NULL DEFAULT 'p' CHECK (lead IN ('p','c','w','b')),   -- p Make the 12, c Reach CCG, w Win conference, b First-round bye
  position  INTEGER NOT NULL,
  added_at  INTEGER NOT NULL,
  PRIMARY KEY (user_id, slug)
);
CREATE INDEX IF NOT EXISTS saved_teams_user ON saved_teams(user_id, position);
