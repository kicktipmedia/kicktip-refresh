#!/usr/bin/env python3
"""sos_copy.py: reader copy for schedule-strength (SOS) rows with no FBS games.

assets/tb/schedule_strength.js ships in the live zip, not in the pipeline build, so a refresh can only change it
through a deterministic text patch of the live file (same pattern as cfp_refresh for assets/top25.js).
apply_data.py runs patch_site() on the merged site and accepts the file only when out == patch_text(base).

Before: a team with no games left rendered "TCU 0 None None" in a conference or national list, and the team card
rendered "Opponents left (0 FBS games) None None".
After:  list row  "TCU | No games left" (or "No FBS games left" when only FCS games remain; played view:
        "No games played" / "No FBS games played"), mean and rank cells empty.
        team card "Opponents left | No games left" (same variants), rank cell empty.
team_compare (assets/tb/team_compare.js), same approach:
Before: "Remaining opponents' average KickTip rating None 52.5" (TCU vs BYU).
After:  "Remaining opponents' average KickTip rating No games left 52.5" ("No FBS games left" when only FCS games remain).

Each patch is idempotent: an already-patched file is returned unchanged. A file whose anchors moved is left as is
(err set, WARNING logged) and the publish goes ahead; the warn-only suite check sos_none_warn then logs
"WARN sos_none: ..." so the raw "None" is visible. Nothing here ever blocks a publish."""
import os, sys

REL = "assets/tb/schedule_strength.js"
MARK = 'cDoneLeft: "No games left",'

COPY_OLD = '    cNone: "None",\n'
COPY_NEW = ('    cNone: "None",\n'
            '    cDoneLeft: "No games left",\n'
            '    cNoFbsLeft: "No FBS games left",\n'
            '    cDonePlayed: "No games played",\n'
            '    cNoFbsPlayed: "No FBS games played",\n'
            '    cBlank: "",\n'
            '    rowLeftDone: "Opponents left",\n'
            '    rowPlayedDone: "Opponents played",\n')

TEAM_OLD = ('          else cells.push(COPY.cNone, COPY.cNone);\n'
            '          rows.push({ cells: cells, src: "facts." + v, vals: vals });\n')
TEAM_NEW = ('          else cells = [v === "remaining" ? COPY.rowLeftDone : COPY.rowPlayedDone, v === "remaining" ? (s.fcs > 0 ? COPY.cNoFbsLeft : COPY.cDoneLeft) : (s.fcs > 0 ? COPY.cNoFbsPlayed : COPY.cDonePlayed), COPY.cBlank];   /* sos_copy: no raw None or 0 for an empty schedule */\n'
            '          rows.push({ cells: cells, src: "facts." + v, vals: vals });\n')

LIST_OLD = ('          else cells.push(COPY.cNone, COPY.cNone);\n'
            '          rows.push({ cells: cells, src: "facts.rows." + k, vals: vals });\n')
LIST_NEW = ('          else { cells[1] = isL ? (x.fcs > 0 ? COPY.cNoFbsLeft : COPY.cDoneLeft) : (x.fcs > 0 ? COPY.cNoFbsPlayed : COPY.cDonePlayed); cells.push(COPY.cBlank, COPY.cBlank); }   /* sos_copy: no raw None or 0 for an empty schedule */\n'
            '          rows.push({ cells: cells, src: "facts.rows." + k, vals: vals });\n')

PAIRS = ((COPY_OLD, COPY_NEW), (TEAM_OLD, TEAM_NEW), (LIST_OLD, LIST_NEW))

# team_compare: only the "Remaining opponents' average KickTip rating" row (sched.mean is null when no FBS games are left)
TC_REL = "assets/tb/team_compare.js"
TC_MARK = 'cNoGamesLeft: "No games left",'
TC_COPY_OLD = '    cNone: "None",\n'
TC_COPY_NEW = ('    cNone: "None",\n'
               '    cNoGamesLeft: "No games left",\n'
               '    cNoFbsLeft: "No FBS games left",\n')
TC_ROW_OLD = '        two(COPY.lOpp, "num1", "sched.mean", T[0].sched.mean, T[1].sched.mean, COPY.cNone, COPY.cNone);\n'
TC_ROW_NEW = ('        two(COPY.lOpp, "num1", "sched.mean", T[0].sched.mean, T[1].sched.mean, T[0].sched.fcs > 0 ? COPY.cNoFbsLeft : COPY.cNoGamesLeft, '
              'T[1].sched.fcs > 0 ? COPY.cNoFbsLeft : COPY.cNoGamesLeft);   /* sos_copy: no raw None for an empty schedule */\n')
TC_PAIRS = ((TC_COPY_OLD, TC_COPY_NEW), (TC_ROW_OLD, TC_ROW_NEW))

FILES = {REL: (MARK, PAIRS), TC_REL: (TC_MARK, TC_PAIRS)}


def _patch(text, mark, pairs):
    if mark in text:
        return text, None
    for old, _ in pairs:
        if text.count(old) != 1:
            return text, "anchor not found exactly once: %r" % old.strip()[:50]
    for old, new in pairs:
        text = text.replace(old, new)
    return text, None


def patch_js(text):
    """schedule_strength.js. Return (new_text, err). err is None on success or when already patched."""
    return _patch(text, MARK, PAIRS)


def patch_tc(text):
    """team_compare.js. Return (new_text, err)."""
    return _patch(text, TC_MARK, TC_PAIRS)


def patch_text(rel, text):
    return _patch(text, *FILES[rel])[0] if rel in FILES else text


def patch_site(site):
    """Patch the merged site in place. Never raises; returns notes."""
    notes = []
    for rel, (mark, pairs) in sorted(FILES.items()):
        try:
            path = os.path.join(site, rel)
            if not os.path.isfile(path):
                notes.append("sos copy: skipped, %s missing" % rel)
                continue
            text = open(path, encoding="utf-8").read()
            new, err = _patch(text, mark, pairs)
            if err:
                notes.append("WARNING sos copy: skipped %s, %s" % (rel, err))
            elif new != text:
                tmp = path + ".tmp"
                with open(tmp, "w", encoding="utf-8") as f:
                    f.write(new)
                os.replace(tmp, path)
                notes.append("sos copy: updated %s" % rel)
        except Exception as e:
            notes.append("WARNING sos copy: patch of %s failed (%s)" % (rel, e))
    for line in notes:
        print(line)
    return notes


if __name__ == "__main__":
    patch_site(sys.argv[1])
