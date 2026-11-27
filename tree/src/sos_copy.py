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
The patch is idempotent: an already-patched file is returned unchanged. A file whose anchors moved is left as is
(err set); the suite's no-"None" check then stops the publish instead of shipping raw "None"."""
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


def patch_js(text):
    """Return (new_text, err). err is None on success or when already patched."""
    if MARK in text:
        return text, None
    for old, _ in PAIRS:
        if text.count(old) != 1:
            return text, "anchor not found exactly once: %r" % old.strip()[:50]
    for old, new in PAIRS:
        text = text.replace(old, new)
    return text, None


def patch_text(rel, text):
    return patch_js(text)[0] if rel == REL else text


def patch_site(site):
    """Patch the merged site in place. Never raises; returns notes."""
    notes = []
    try:
        path = os.path.join(site, REL)
        if not os.path.isfile(path):
            notes.append("sos copy: skipped, %s missing" % REL)
        else:
            text = open(path, encoding="utf-8").read()
            new, err = patch_js(text)
            if err:
                notes.append("WARNING sos copy: skipped, %s" % err)
            elif new != text:
                tmp = path + ".tmp"
                with open(tmp, "w", encoding="utf-8") as f:
                    f.write(new)
                os.replace(tmp, path)
                notes.append("sos copy: updated %s" % REL)
    except Exception as e:
        notes.append("WARNING sos copy: patch failed (%s)" % e)
    for line in notes:
        print(line)
    return notes


if __name__ == "__main__":
    patch_site(sys.argv[1])
