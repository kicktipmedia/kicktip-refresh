"""Schema validator for the official-rules title-game simulator rules (src/ccg_rules_step1.py + optional src/ccg_rules_step2.py). Run: python3 tests/ccg_rules_check.py"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
import ccg_rules
rules = ccg_rules.load(); errs = ccg_rules.validate(rules)
for e in errs: print("FAIL", e)
print(f"ccg rules: {len(rules)} conferences ({', '.join(sorted(rules))}), {len(errs)} problems")
sys.exit(1 if errs else 0)
