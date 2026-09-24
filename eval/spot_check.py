"""Print a random sample of graded rows to spot-check the LLM judge by hand.

Usage (from the project root):
    python eval/spot_check.py                       # 10 rows from the latest results file
    python eval/spot_check.py v3_rbac_redact 12     # 12 rows from the latest file matching that text
"""
import json
import random
import sys
from pathlib import Path

RESULTS = Path(__file__).resolve().parent / "results"
label = sys.argv[1] if len(sys.argv) > 1 else ""
count = int(sys.argv[2]) if len(sys.argv) > 2 else 10

files = sorted(RESULTS.glob(f"*{label}*.json"))
if not files:
    sys.exit("No matching results files found.")

data = json.loads(files[-1].read_text(encoding="utf-8"))
# Only rows graded by the LLM judge; the PII-leak rows are checked by plain code.
rows = [r for r in data["rows"] if r["type"] != "pii_leak"]
sample = random.sample(rows, min(count, len(rows)))

print(f"{files[-1].name}: {len(sample)} of {len(rows)} judge-graded rows\n")
for r in sample:
    print(f"{r['id']} [{r['type']}] role={r['user_role']}")
    print(f"  Q:       {r['question']}")
    print(f"  gold:    {r['gold_answer']}")
    print(f"  system:  {r['system_answer'][:400]!r}")
    print(f"  verdict: {'PASS' if r['passed'] else 'FAIL'} | {r['reason']}\n")
