Migrations apply in file order. The Worker's SQL (src/worker/worker.js `SQL`) is the only SQL that ever runs; tests/d1_schema_test.py runs every one of those statements against these migrations in a real SQLite.
To roll back everything: `DROP TABLE saved_teams; DROP TABLE users; DROP TABLE rate_limits; DROP TABLE email_tokens;` (this deletes all accounts).
0003_email_tokens.sql is the phase 3 (email link) table; nothing reads it in phases 1-2.
