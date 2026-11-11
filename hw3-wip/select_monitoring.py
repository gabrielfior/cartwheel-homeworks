"""Pick 50 stratified scenarios (seeded) -> scenarios/monitoring_scenarios.jsonl: 20 challenge (6 dq + 14 other), 30 coverage."""
import json, random
from collections import Counter
rows=[json.loads(l) for l in open("scenarios/support_scenarios.jsonl")]
rng=random.Random(7); pick={}
def add(pool,n,key):
    # round-robin over key values so every value appears
    groups={}
    for r in pool: groups.setdefault(key(r),[]).append(r)
    for g in groups.values(): rng.shuffle(g)
    order=sorted(groups); i=0
    while n>0 and any(groups.values()):
        g=groups[order[i%len(order)]]; i+=1
        while g and g[-1]["id"] in pick: g.pop()
        if g: pick[g.pop()["id"]]=1; n-=1
dq=[r for r in rows if r["data_quality_case_id"]]
add(dq,6,lambda r:r["data_quality_case_id"])
ch=[r for r in rows if r["scenario_group"]=="challenge" and not r["data_quality_case_id"]]
add(ch,14,lambda r:(r["tuple"]["role"],r["tuple"]["intent"]))
co=[r for r in rows if r["scenario_group"]=="coverage"]
add(co,30,lambda r:(r["tuple"]["intent"],r["tuple"]["role"]))
sel=[r for r in rows if r["id"] in pick]
open("scenarios/monitoring_scenarios.jsonl","w").write("".join(json.dumps(r,ensure_ascii=False)+"\n" for r in sel))
print(len(sel),Counter(r["scenario_group"] for r in sel),Counter(r["tuple"]["role"] for r in sel),Counter(r["tuple"]["intent"] for r in sel),Counter(r["tuple"]["turn_count"] for r in sel),Counter(r["data_quality_case_id"] for r in sel if r["data_quality_case_id"]))
