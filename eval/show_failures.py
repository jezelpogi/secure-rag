"""Print failed questions and retrieval misses from an eval results file.

Usage (from the project root):
    python eval/show_failures.py                 # latest results file
    python eval/show_failures.py rbac_redact     # latest file whose name contains this text
"""
import json
import sys
from pathlib import Path

RESULTS = Path(__file__).resolve().parent / "results"
label = sys.argv[1] if len(sys.argv) > 1 else ""
files = sorted(RESULTS.glob(f"*{label}*.json"))
if not files:
    sys.exit("No matching results files found.")

path = files[-1]
data = json.loads(path.read_text(encoding="utf-8"))
print(f"{path.name}\nconfig: {data['config']}\n")

for r in data["rows"]:
    retrieval_miss = r.get("retrieval_hit") is False
    if not r["passed"] or retrieval_miss:
        print(f"{r['id']} [{r['type']} / {r.get('skill', '-')}] role={r['user_role']}")
        print(f"  Q:         {r['question']}")
        print(f"  gold:      {r['gold_answer']} ({r['gold_doc']})")
        print(f"  system:    {r['system_answer'][:300]!r}")
        print(f"  retrieved: {r.get('retrieved_docs')}")
        print(f"  judge:     {r['reason']}")
        print(f"  passed={r['passed']}  retrieval_miss={retrieval_miss}\n")
