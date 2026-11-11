"""Pick 15 scenarios for review point 3 and render HW3_SUPPORT_REVIEW.md."""
import json
from pathlib import Path

rows = [json.loads(l) for l in open("scenarios/support_scenarios.jsonl")]
by = {r["id"]: r for r in rows}
picked = []

def take(pred, why):
    for r in rows:
        if r["id"] not in {p[0]["id"] for p in picked} and pred(r):
            picked.append((r, why)); return
    raise SystemExit(f"no match for {why}")

T = lambda r: r["tuple"]
# every damaged record
for case in ["dq-order-missing-delivery-date", "dq-order-reversed-dates", "dq-order-store-mismatch",
             "dq-product-duplicate-title", "dq-product-invalid-price", "dq-product-missing-title"]:
    take(lambda r, c=case: r["data_quality_case_id"] == c, f"damaged record {case}")
# every intent, coverage group, rotating roles
roles = iter(["shopper", "merchant", "support", "shopper", "merchant", "support", "shopper"])
for intent in ["order_status", "refund", "cancellation", "policy_question", "product_search", "dispute", "out_of_scope"]:
    ro = next(roles)
    take(lambda r, i=intent, ro=ro: r["scenario_group"] == "coverage" and T(r)["intent"] == i and T(r)["role"] == ro,
         f"coverage {intent} ({ro})")
# threshold / store override / longest
take(lambda r: r["scenario_group"] == "challenge" and not r["data_quality_case_id"] and T(r).get("refund_amount_band") in ("just_above", "at"), "refund threshold boundary")
longest = max(rows, key=lambda r: len(r["opening_message"]) + sum(map(len, r["followups"])))
if longest["id"] not in {p[0]["id"] for p in picked}:
    picked.append((longest, "longest conversation"))

out = ["# HW3 review point 3: support scenario sample", "",
       "Read each opening and follow-up. Check: realistic language, follow-ups make sense without seeing the agent's reply, expected metadata matches the record.",
       "Decide per scenario: **accept / revise / reject** (add a reason; for revise, say what to change). I write `scenarios/support_review.jsonl` from your decisions.", ""]
for n, (r, why) in enumerate(picked, 1):
    t = r["tuple"]
    out += [f"## {n}. {r['id']} — {why}", "",
            f"- group: {r['scenario_group']} | dq: {r['data_quality_case_id']} | role: {t['role']} (user {t['user_id']}) | intent: {t['intent']} | style: {t['user_style']} | turns: {t['turn_count']}",
            f"- record_state: {t['record_state']} | policy: {t['applicable_policy']} | difficulty: {t['difficulty']} | band: {t.get('refund_amount_band')}",
            f"- order/product: {t.get('order_id', t.get('product_id', '-'))}", "",
            f"**Opening:** {r['opening_message']}"]
    out += [f"**Follow-up {i}:** {f}" for i, f in enumerate(r["followups"], 1)]
    e = r["expected"]
    out += ["", f"**Expected:** `{e.get('outcome', e.get('criterion', ''))}` ({e['evaluation']}) — {e.get('reason', e.get('criterion', ''))}",
            f"**Source:** {e['source']['type']} / {e['source']['reference']}", "",
            "**Your decision:** TODO (accept / revise / reject) — reason:", ""]
Path("HW3_SUPPORT_REVIEW.md").write_text("\n".join(out))
print(len(picked), [p[0]["id"] for p in picked])
