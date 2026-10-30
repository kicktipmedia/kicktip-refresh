"""The three selectable KickTip models (v6a rev2: KickTip blend + Elo-style + Efficiency; the MSM rating is NOT selectable, raw MSM is never offered; it stays inside the blend and drives the committee proxy) (plain data, no imports). Order = order in the toggle. The first entry is the DEFAULT model shown to everyone.
Used by calibrate.py (which writes data/out/models/<id>.json), sim.py (DEFAULT_MODEL), run_all.py (per-model outputs), build.py (gated per-model prediction files)
and the toggle in assets/kt.js (names and blurbs below are copied into data/pred-models.json by build.py, so the page text has one source).
No third-party rating names anywhere in this file (charter / BUILD-SPEC)."""
MODELS = [
    dict(id="blend", component="blend", name="KickTip blend", btn="KickTip blend", default=True,
         short="Default estimate. KickTip's own mix of several rating ideas.",
         blurb="Our default. KickTip's own version, inspired by widely used rating systems: it combines the MSM rating, an Elo-style rating, an efficiency rating and last season's final strength, with weights learned only from earlier games."),
    dict(id="elo", component="elo_cal", name="Elo-style", btn="Elo-style", default=False,
         short="Alternate estimate. A rating that moves after every game.",
         blurb="KickTip's own version, inspired by widely used rating systems: a rating that moves after every game, with bigger moves for bigger upsets and bigger margins."),
    dict(id="eff", component="eff_cal", name="Efficiency", btn="Efficiency", default=False,
         short="Alternate estimate. Based on points scored and allowed per game.",
         blurb="KickTip's own version, inspired by widely used rating systems: a rating built from how many points a team scores and allows per game, adjusted for opponent."),
]
DEFAULT_ID = MODELS[0]["id"]
BY_ID = {m["id"]: m for m in MODELS}

STORE_KEY = "kicktip_model"   # localStorage key for the visitor's pick (value = an alternate id; the default is stored as NO key). Written by assets/kt.js only when the visitor picks a model (read-only otherwise; stale values are ignored, never rewritten).
ALT_IDS = [m["id"] for m in MODELS[1:]]
