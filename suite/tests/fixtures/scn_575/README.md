Frozen scenario-bank data (live 9:30 AM MT Oct 31 2026, 575 completed results; from Production 9ab846f7 / s0 028b011a).
The scenario banks (qbank_scn_a1, qbank_scn_b, set_scn_b) record exact answers for named games, so they replay on THIS data
with the engine JS of the tree under test. Re-record only when the sim-bundle/ccg-sim/ccg-rules schema changes (then re-run the
bank generators on a new frozen copy and commit both together).
