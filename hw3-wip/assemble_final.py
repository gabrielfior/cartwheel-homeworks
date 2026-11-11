"""Merge plan_final.json + critic_out/*.json into scenarios/support_scenarios.jsonl. Usage: python assemble_final.py <out.jsonl>"""
import json, sys
from pathlib import Path

HERE = Path(__file__).parent
plan = json.loads((HERE / "plan_final.json").read_text())
rows = []
for i, p in enumerate(plan, start=1):
    m = json.loads((HERE / "critic_out" / f"{p['key']}.json").read_text())
    assert len(m["followups"]) == p["tuple"]["turn_count"] - 1, p["key"]
    rows.append({
        "id": f"support-{i:04d}",
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
