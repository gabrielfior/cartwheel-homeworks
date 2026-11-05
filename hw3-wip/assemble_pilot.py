"""Merge plan + final messages into scenarios/pilot_scenarios.jsonl. Usage: python assemble_pilot.py <out.jsonl>"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).parent
plan = json.loads((HERE / "plan_pilot.json").read_text())
msgs = json.loads((HERE / "final_messages.json").read_text())
assert {p["key"] for p in plan} == set(msgs), "plan and messages differ"

rows = []
for i, p in enumerate(plan, start=1):
    m = msgs[p["key"]]
    rows.append({
        "id": f"pilot-{i:04d}",
        "scenario_group": p["group"],
        "data_quality_case_id": p["data_quality_case_id"],
        "tuple": p["tuple"],
        "opening_message": m["opening_message"],
        "followups": m["followups"],
        "expected": p["expected"],
    })
out = Path(sys.argv[1])
out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
print(f"wrote {len(rows)} scenarios to {out}")
print("key -> id:", ", ".join(f"{p['key']}={r['id']}" for p, r in zip(plan, rows)))
