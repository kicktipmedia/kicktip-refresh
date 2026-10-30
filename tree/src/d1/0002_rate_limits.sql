-- Fixed-window counters for the Worker's rate limits (10 sign-in starts per hour per visitor, 60 saves per hour per account, 3 account deletes per day per visitor).
-- k is a keyed hash (HMAC with SESSION_SECRET) of the visitor address or the account id, never a raw address. Rows expire (exp) and are swept on use.
CREATE TABLE IF NOT EXISTS rate_limits (
  k    TEXT    NOT NULL,
  w    INTEGER NOT NULL,       -- window number
  n    INTEGER NOT NULL,
  exp  INTEGER NOT NULL,       -- unix seconds after which the row can be deleted
  PRIMARY KEY (k, w)
);
CREATE INDEX IF NOT EXISTS rate_limits_exp ON rate_limits(exp);
