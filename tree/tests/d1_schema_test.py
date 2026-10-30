"""D1 schema test: apply src/d1/*.sql to real SQLite (D1 is SQLite) and run the Worker's own SQL strings against it. Run: python3 tests/d1_schema_test.py (needs node)."""
import glob, json, os, sqlite3, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# load the Worker from a temp .mjs copy (the file is _worker.js with no package.json)
tmp = "/tmp/ktw_schema.mjs"; open(tmp, "w").write(open(f"{ROOT}/build/site/_worker.js").read())
sql = json.loads(subprocess.check_output(["node", "-e", f"import('file://{tmp}').then(m=>console.log(JSON.stringify(m.default._t.SQL)))"]))
p = f = 0
def ok(c, m):
    global p, f
    if c: p += 1
    else: f += 1; print("FAIL", m)
db = sqlite3.connect(":memory:"); db.execute("PRAGMA foreign_keys=ON")
mig = sorted(glob.glob(f"{ROOT}/src/d1/*.sql")); ok(len(mig) == 3, "three migrations")
for m in mig + mig: db.executescript(open(m).read())   # applied twice: IF NOT EXISTS makes re-running safe
tables = {r[0] for r in db.execute("select name from sqlite_master where type='table' and name not like 'sqlite_%'")}
ok(tables == {"users", "saved_teams", "rate_limits", "email_tokens"}, f"tables {tables}")
cols = [r[1] for r in db.execute("pragma table_info(users)")]; ok(cols == ["id", "google_sub", "email", "display_name", "created_at", "sess_ver"], f"users columns {cols} (only sub, email, name, created_at + session version)")
ok([r[1] for r in db.execute("pragma table_info(saved_teams)")] == ["user_id", "slug", "lead", "position", "added_at"], "saved_teams columns")
u = db.execute(sql["upsertUser"], ("sub1", "a@example.com", "A", 100)).fetchone(); ok(u == (1, 1), f"upsert insert returns id, sess_ver {u}")
u2 = db.execute(sql["upsertUser"], ("sub1", "b@example.com", None, 200)).fetchone(); ok(u2 == (1, 1), "upsert on same sub keeps id")
row = db.execute(sql["userById"], (1,)).fetchone(); ok(row == (1, "b@example.com", None, 1), f"userById after update {row}")
ok(db.execute("select created_at from users").fetchone()[0] == 100, "created_at is not overwritten on re-sign-in")
db.execute(sql["bumpSess"], (1,)); ok(db.execute(sql["userById"], (1,)).fetchone()[3] == 2, "D2: bumpSess raises sess_ver 1 -> 2 on real SQLite (logout revokes)")
ok(db.execute(sql["bumpSess"], (999,)).rowcount == 0, "D2: bumpSess on a missing user touches nothing")
db.execute(sql["upsertUser"], ("sub1", "b@example.com", None, 300)); ok(db.execute(sql["userById"], (1,)).fetchone()[3] == 2, "D2: a later sign-in keeps the bumped sess_ver (old cookies stay dead)")
db.execute(sql["addTeam"], (1, "utah", "w", 1, 5)); db.execute(sql["addTeam"], (1, "byu", "p", 0, 5))
ok([tuple(r) for r in db.execute(sql["teams"], (1,))] == [("byu", "p"), ("utah", "w")], "teams ordered by position")
try: db.execute(sql["addTeam"], (1, "utah", "p", 3, 5)); ok(False, "duplicate slug must fail")
except sqlite3.IntegrityError: ok(True, "duplicate slug rejected")
try: db.execute(sql["addTeam"], (1, "ucla", "z", 3, 5)); ok(False, "bad lead must fail")
except sqlite3.IntegrityError: ok(True, "lead CHECK rejects unknown codes")
try: db.execute(sql["addTeam"], (99, "ucla", "p", 3, 5)); ok(False, "orphan team must fail")
except sqlite3.IntegrityError: ok(True, "foreign key rejects a team with no user")
db.execute(sql["clearTeams"], (1,)); ok(db.execute("select count(*) from saved_teams").fetchone()[0] == 0, "clearTeams")
db.execute(sql["addTeam"], (1, "utah", "w", 0, 5)); db.execute(sql["deleteUser"], (1,))
ok(db.execute("select count(*) from users").fetchone()[0] == 0 and db.execute("select count(*) from saved_teams").fetchone()[0] == 0, "deleting the user cascades to saved teams")
ns = [db.execute(sql["rate"], ("k", 7, 999)).fetchone()[0] for _ in range(3)]; ok(ns == [1, 2, 3], f"rate counter {ns}")
ok(db.execute(sql["rate"], ("k", 8, 999)).fetchone()[0] == 1, "new window starts at 1")
db.execute(sql["sweep"], (1000,)); ok(db.execute("select count(*) from rate_limits").fetchone()[0] == 0, "sweep removes expired windows")
rl = [r[1] for r in db.execute("pragma table_info(rate_limits)")]; ok(rl == ["k", "w", "n", "exp"], "rate_limits stores only a keyed hash, window, count, expiry")
ok([r[1] for r in db.execute("pragma table_info(email_tokens)")] == ["token_hash", "email", "created_at", "expires_at", "used_at"], "email_tokens (phase 3 table): hashed token, email, created_at, expires_at, used_at")
db.execute("insert into email_tokens values('h','a@example.com',1,1209601,null)"); ok(db.execute("update email_tokens set used_at=5 where token_hash='h' and used_at is null").rowcount == 1 and db.execute("update email_tokens set used_at=6 where token_hash='h' and used_at is null").rowcount == 0, "single use: the second consume matches no row")
print(f"d1_schema_test: {p} pass, {f} fail"); sys.exit(1 if f else 0)
