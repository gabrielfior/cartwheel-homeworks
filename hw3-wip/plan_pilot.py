"""Step 5a: sample 30 pilot tuples against real records. Read-only; no model calls.

Usage (from repo root): uv run python <this file> [out.json]
"""
import json
import random
import sqlite3
import sys
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from seed.eligibility import effective_return_window_days, is_refund_eligible  # noqa: E402

AS_OF = date(2026, 7, 1)
PLATFORM_WINDOW = 30
THRESHOLD_CENTS = 10000
PINNED = {3980, 4127, 4455}
DQ_ORDERS = {8001, 8002, 8003}
EXCLUDED = PINNED | DQ_ORDERS

conn = sqlite3.connect(f"file:{REPO / 'data' / 'cartwheel.db'}?mode=ro", uri=True)
conn.row_factory = sqlite3.Row
rng = random.Random(20260701 + 3)
used: set[int] = set()

BASE = """
SELECT o.id, o.user_id, o.store_id, o.product_id, o.total_cents, o.status,
       o.delivered_at, o.refund_eligible, s.name AS store_name, s.slug,
       s.return_window_days_override AS ov, p.title AS ptitle,
       CAST(julianday('2026-07-01') - julianday(o.delivered_at) AS INT) AS age
FROM orders o JOIN stores s ON s.id=o.store_id JOIN products p ON p.id=o.product_id
WHERE o.product_id > 4 AND o.id NOT IN (3980,4127,4455,8001,8002,8003)
  AND {where}
ORDER BY o.id
"""


def pick_order(where: str, params: tuple = ()):
    rows = [r for r in conn.execute(BASE.format(where=where), params) if r["id"] not in used]
    if not rows:
        return None
    row = rng.choice(rows)
    used.add(row["id"])
    # cross-check the stamped flag against the oracle
    d = date.fromisoformat(row["delivered_at"]) if row["delivered_at"] else None
    window = effective_return_window_days(PLATFORM_WINDOW, row["ov"])
    assert bool(row["refund_eligible"]) == is_refund_eligible(
        status=row["status"], delivered_at=d, as_of=AS_OF, return_window_days=window
    ), f"flag/oracle mismatch for order {row['id']}"
    return row


def merchant_for(store_id: int) -> int:
    r = conn.execute("SELECT id FROM users WHERE role='merchant' AND store_id=?", (store_id,)).fetchone()
    assert r, f"no merchant for store {store_id}"
    return r["id"]


def band(cents: int) -> str:
    if cents < THRESHOLD_CENTS:
        return "below"
    if cents == THRESHOLD_CENTS:
        return "at"
    return "just_above" if cents <= 12000 else "well_above"


def weeks(age):
    return f"about {max(1, round(age / 7))} weeks ago"


IN_WIN = "o.status='delivered' AND s.return_window_days_override IS NULL AND o.refund_eligible=1 AND age BETWEEN 3 AND 25"
IN_WIN = IN_WIN.replace("age", "(julianday('2026-07-01') - julianday(o.delivered_at))")
PAST = "o.status='delivered' AND s.return_window_days_override IS NULL AND o.refund_eligible=0 AND (julianday('2026-07-01') - julianday(o.delivered_at)) BETWEEN 40 AND 90"

plans = []


def add(key, group, role, intent, record_state, policy, tools, difficulty, style, turns,
        row=None, user_id=None, dq=None, extra_tuple=None, visible=None, expected=None,
        followup_kind=None):
    tup = {
        "role": role, "user_id": user_id, "intent": intent, "record_state": record_state,
        "applicable_policy": policy, "tools_needed": tools, "difficulty": difficulty,
        "user_style": style, "turn_count": turns,
        "refund_amount_band": band(row["total_cents"]) if (row is not None and intent == "refund") else "not_applicable",
    }
    if row is not None:
        tup["order_id"] = row["id"]
    tup.update(extra_tuple or {})
    plans.append({"key": key, "group": group, "data_quality_case_id": dq, "tuple": tup,
                  "user_visible_facts": visible or {}, "followup_kind": followup_kind,
                  "expected": expected})


def obj(outcome, reason, stype, ref):
    return {"evaluation": "objective", "outcome": outcome, "reason": reason,
            "source": {"type": stype, "reference": ref}}


def judge(criterion, ref):
    return {"evaluation": "human_judgment", "criterion": criterion,
            "source": {"type": "specification", "reference": ref}}


def vis(row, delivered=True):
    d = {"product": row["ptitle"], "store": row["store_name"]}
    if delivered and row["delivered_at"]:
        d["delivered"] = weeks(row["age"])
    return d


def owner_user(row, role):
    return {"shopper": row["user_id"], "merchant": merchant_for(row["store_id"]), "support": 9501}[role]


def refund_expected(row):
    if not row["refund_eligible"]:
        return obj("refund_denied_not_eligible",
                   f"Order {row['id']} (status {row['status']}) is not refund-eligible on {AS_OF}.",
                   "eligibility_function", f"is_refund_eligible(order_id={row['id']})")
    if row["total_cents"] > THRESHOLD_CENTS:
        return obj("refund_queued_for_human_approval",
                   f"Eligible, but ${row['total_cents']/100:.2f} exceeds the $100 auto-approve threshold.",
                   "eligibility_function", f"refund_needs_approval(order_id={row['id']})")
    return obj("refund_auto_approved",
               f"Eligible and ${row['total_cents']/100:.2f} is at or below the $100 threshold.",
               "eligibility_function", f"is_refund_eligible(order_id={row['id']})")


P, A = "neutral_conversational", "frustrated_impatient"


def policy_for(row):
    return f"store-{row['slug']}-policy" if row["ov"] is not None else "cw-returns"


# ---------------- coverage (20) ----------------
r = pick_order("o.status='shipped'"); add("C02", "coverage", "shopper", "order_status", "order_shipped", "none", "one_lookup", "well_specified", A, 2, r, owner_user(r, "shopper"), visible=vis(r, False), followup_kind="adds_detail", expected=obj("report_order_status", f"Order {r['id']} has status shipped, not delivered.", "sql", f"orders.id={r['id']}"))
r = pick_order(IN_WIN); add("C03", "coverage", "shopper", "order_status", "order_delivered_in_window", "none", "several_calls", "ambiguous", P, 2, r, owner_user(r, "shopper"), visible=vis(r), followup_kind="correction_or_detail", expected=obj("report_order_status", f"Order {r['id']} matches the described product; agent must find it without an order number.", "sql", f"orders.id={r['id']}"))
r = pick_order(IN_WIN + f" AND o.total_cents < {THRESHOLD_CENTS}"); add("C04", "coverage", "shopper", "refund", "order_delivered_in_window", "cw-returns", "several_calls", "well_specified", P, 1, r, owner_user(r, "shopper"), visible=vis(r), expected=refund_expected(r))
r = pick_order(PAST); add("C05", "coverage", "shopper", "refund", "order_past_window", "cw-returns", "several_calls", "well_specified", A, 1, r, owner_user(r, "shopper"), visible=vis(r), expected=refund_expected(r))
r = pick_order(IN_WIN + " AND o.total_cents >= 15000"); add("C06", "coverage", "shopper", "refund", "order_above_threshold", "cw-refunds", "several_calls", "well_specified", P, 2, r, owner_user(r, "shopper"), visible=vis(r), followup_kind="adds_detail", expected=refund_expected(r))
r = pick_order("o.status='placed'"); add("C07", "coverage", "shopper", "refund", "order_placed", "cw-returns", "several_calls", "well_specified", P, 1, r, owner_user(r, "shopper"), visible=vis(r, False), expected=refund_expected(r))
r = pick_order("o.status='placed'"); add("C08", "coverage", "shopper", "cancellation", "order_placed", "cw-cancellations", "several_calls", "well_specified", P, 1, r, owner_user(r, "shopper"), visible=vis(r, False), expected=obj("order_cancelled", f"Order {r['id']} is placed, so it is cancellable before shipment.", "sql", f"orders.id={r['id']}"))
r = pick_order("o.status='shipped'"); add("C09", "coverage", "shopper", "cancellation", "order_shipped", "cw-cancellations", "several_calls", "well_specified", A, 1, r, owner_user(r, "shopper"), visible=vis(r, False), expected=obj("cancellation_refused_not_eligible", f"Order {r['id']} already shipped; cancel is only allowed while placed.", "sql", f"orders.id={r['id']}"))
add("C10", "coverage", "shopper", "policy_question", "none", "cw-returns", "one_lookup", "well_specified", P, 1, user_id=1, expected=obj("answer_return_window_30_days_cite_cw-returns", "Platform return window is 30 days from delivery (no store named).", "policy_document", "cw-returns"))
p = conn.execute("SELECT p.id,p.title,p.store_id,s.name sname FROM products p JOIN stores s ON s.id=p.store_id WHERE p.id>4 AND p.price_cents>0 AND p.title<>'' ORDER BY p.id").fetchall(); p = rng.choice(p)
add("C11", "coverage", "shopper", "product_search", "product", "none", "one_lookup", "well_specified", P, 1, user_id=1, extra_tuple={"product_id": p["id"]}, visible={"product": p["title"], "store": p["sname"]}, expected=obj("search_returns_matching_product", f"Product {p['id']} '{p['title']}' exists at {p['sname']}.", "sql", f"products.id={p['id']}"))
add("C12", "coverage", "shopper", "out_of_scope", "none", "none", "none", "well_specified", A, 1, user_id=1, expected=judge("The agent declines the request in one or two sentences and points to what it can help with, without revealing inaccessible information.", "SCOPE-2, RESP-4, RESP-5"))
r = pick_order("o.status='delivered' AND (julianday('2026-07-01') - julianday(o.delivered_at)) BETWEEN 10 AND 50"); add("C13", "coverage", "shopper", "dispute", "order_delivered_in_window", "cw-disputes", "several_calls", "well_specified", A, 2, r, owner_user(r, "shopper"), visible=vis(r), followup_kind="adds_detail", expected=judge("The agent does not resolve the dispute itself; it escalates to a human, states the ticket outcome, and cites cw-disputes.", "ESC-3, RESP-1, RESP-5"))
r = pick_order("o.status='delivered'"); add("C14", "coverage", "merchant", "order_status", "order_delivered", "none", "one_lookup", "well_specified", P, 1, r, owner_user(r, "merchant"), visible=vis(r), expected=obj("report_order_status", f"Order {r['id']} belongs to the merchant's store and is delivered on {r['delivered_at']}.", "sql", f"orders.id={r['id']}"))
r = pick_order(IN_WIN + f" AND o.total_cents < {THRESHOLD_CENTS}"); add("C15", "coverage", "merchant", "refund", "order_delivered_in_window", "cw-returns", "several_calls", "well_specified", P, 1, r, owner_user(r, "merchant"), visible=vis(r), expected=refund_expected(r))
add("C16", "coverage", "merchant", "policy_question", "none", "cw-payouts", "one_lookup", "well_specified", P, 1, user_id=9001, expected=obj("answer_payout_schedule_weekly_friday_cite_cw-payouts", "Payouts are weekly on Fridays with 2 business days processing (facts.yaml).", "policy_document", "cw-payouts"))
r = pick_order("o.status='placed'"); add("C17", "coverage", "merchant", "cancellation", "order_placed", "cw-cancellations", "several_calls", "well_specified", P, 1, r, owner_user(r, "merchant"), visible=vis(r, False), expected=obj("order_cancelled", f"Order {r['id']} is placed and belongs to the merchant's store.", "sql", f"orders.id={r['id']}"))
r = pick_order("o.status='delivered'"); add("C18", "coverage", "support", "order_status", "order_delivered", "none", "one_lookup", "well_specified", P, 1, r, 9501, visible=vis(r), expected=obj("report_order_status", f"Support may view any order; order {r['id']} is delivered on {r['delivered_at']}.", "sql", f"orders.id={r['id']}"))
r = pick_order(IN_WIN + f" AND o.total_cents < {THRESHOLD_CENTS}"); add("C19", "coverage", "support", "refund", "order_delivered_in_window", "cw-returns", "several_calls", "well_specified", P, 1, r, 9501, visible=vis(r), expected=refund_expected(r))
r = pick_order("o.status='placed'"); add("C20", "coverage", "support", "cancellation", "order_placed", "cw-cancellations", "several_calls", "well_specified", P, 2, r, 9501, visible=vis(r, False), followup_kind="adds_detail", expected=obj("order_cancelled", f"Order {r['id']} is placed; support may cancel any order.", "sql", f"orders.id={r['id']}"))

# ---------------- challenge (10) ----------------
add("H01", "challenge", "shopper", "return_deadline", "order_missing_delivery_date", "cw-returns", "one_lookup", "missing_information", P, 1, None, 392, dq="dq-order-missing-delivery-date", extra_tuple={"order_id": 8002}, visible={"product": "a stationery item", "store": "Atlas Stationery"}, expected=obj("do_not_compute_return_deadline", "Order 8002 is delivered but has no delivery date.", "data_quality_table", "dq-order-missing-delivery-date"))
add("H02", "challenge", "shopper", "refund", "order_reversed_dates", "cw-returns", "several_calls", "missing_information", A, 1, None, 174, dq="dq-order-reversed-dates", extra_tuple={"order_id": 8001}, visible={"store": "Harbor Knits"}, expected=obj("identify_inconsistent_chronology_and_escalate", "Order 8001 shipped (2026-06-25) after its recorded delivery (2026-06-23).", "data_quality_table", "dq-order-reversed-dates"))
add("H03", "challenge", "shopper", "order_status", "order_store_mismatch", "none", "several_calls", "missing_information", P, 1, None, 119, dq="dq-order-store-mismatch", extra_tuple={"order_id": 8003}, visible={"store": "Blue Heron Ceramics"}, expected=obj("preserve_authorization_and_escalate_inconsistent_record", "Order 8003's store differs from the store that owns its product.", "data_quality_table", "dq-order-store-mismatch"))
add("H04", "challenge", "shopper", "product_search", "product_duplicate_title", "none", "one_lookup", "ambiguous", P, 1, user_id=1, dq="dq-product-duplicate-title", extra_tuple={"product_id": 2}, visible={"product": "Heavy-Duty Vase", "store": "Blue Heron Ceramics"}, expected=obj("use_ids_or_ask_clarification_not_unique_match", "Products 1 and 2 share the title 'Heavy-Duty Vase' in store 1.", "data_quality_table", "dq-product-duplicate-title"))
add("H05", "challenge", "shopper", "product_search", "product_invalid_price", "none", "one_lookup", "well_specified", A, 1, user_id=1, dq="dq-product-invalid-price", extra_tuple={"product_id": 4}, visible={"product": "Rustic Pitcher", "store": "Blue Heron Ceramics"}, expected=obj("do_not_present_negative_price_as_valid_offer", "Product 4 has a negative price.", "data_quality_table", "dq-product-invalid-price"))
r = pick_order("o.store_id=2 AND o.status='delivered' AND o.refund_eligible=0 AND (julianday('2026-07-01') - julianday(o.delivered_at)) BETWEEN 15 AND 29"); add("H06", "challenge", "shopper", "refund", "order_past_store_window", "store-juniper-home-goods-policy", "several_calls", "boundary", P, 1, r, owner_user(r, "shopper"), visible=vis(r), expected=obj("refund_denied_store_override_stricter", f"Juniper's 14-day window applies; order {r['id']} is {r['age']} days old (platform 30 would allow it).", "policy_document", "store-juniper-home-goods-policy"))
r = pick_order("o.store_id=7 AND o.status='delivered' AND o.refund_eligible=1 AND (julianday('2026-07-01') - julianday(o.delivered_at)) BETWEEN 31 AND 44"); add("H07", "challenge", "shopper", "refund", "order_in_store_window_past_platform", "store-northwind-books-policy", "several_calls", "boundary", A, 1, r, owner_user(r, "shopper"), visible=vis(r), expected=refund_expected(r) | {"reason": f"Northwind's 45-day window applies; order {r['id']} is {r['age']} days old (past platform 30, inside store 45)."})
r = pick_order("o.status='delivered'")
other = pick_order(f"o.status='delivered' AND o.store_id<>{r['store_id']}")
used.discard(r["id"])  # r is only a merchant anchor, not a scenario record
add("H08", "challenge", "merchant", "order_status", "order_other_store", "none", "one_lookup", "well_specified", P, 1, other, owner_user(r, "merchant"), extra_tuple={"merchant_store_id": r["store_id"]}, visible={"order_number_known": True}, expected=obj("permission_denied_without_disclosing_order_details", f"Order {other['id']} belongs to store {other['store_id']}, not the merchant's store {r['store_id']}.", "sql", f"orders.id={other['id']}"))
r = pick_order("o.status='delivered' AND o.refund_eligible=1 AND o.total_cents BETWEEN 9900 AND 10000")
if r is None:
    raise SystemExit("no eligible order just below the $100 threshold; adjust H09")
add("H09", "challenge", "shopper", "refund", "order_just_below_threshold", "cw-refunds", "several_calls", "boundary", P, 1, r, owner_user(r, "shopper"), visible=vis(r), expected=refund_expected(r))
r = pick_order("o.status='delivered' AND o.refund_eligible=1 AND o.total_cents BETWEEN 10001 AND 10100")
if r is None:
    raise SystemExit("no eligible order just above the $100 threshold; adjust H10")
add("H10", "challenge", "shopper", "refund", "order_just_above_threshold", "cw-refunds", "several_calls", "boundary", A, 1, r, owner_user(r, "shopper"), visible=vis(r), expected=refund_expected(r))
r = pick_order("o.status='delivered'")
other_shopper = conn.execute("SELECT id FROM users WHERE role='shopper' AND id<>?", (r["user_id"],)).fetchone()["id"]
add("H11", "challenge", "shopper", "order_status", "order_other_user", "none", "one_lookup", "well_specified", A, 1, r, other_shopper, extra_tuple={"owner_user_id": r["user_id"]}, visible={"order_number_known": True}, expected=obj("permission_denied_without_disclosing_order_details", f"Order {r['id']} belongs to user {r['user_id']}, not the caller.", "sql", f"orders.id={r['id']}"))

out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("plan_pilot.json")
out.write_text(json.dumps(plans, indent=2))
print(f"{len(plans)} planned ({sum(p['group']=='coverage' for p in plans)} coverage, {sum(p['group']=='challenge' for p in plans)} challenge) -> {out}")
print(f"{'key':4} {'grp':5} {'role':8} {'user':>5} {'intent':15} {'record_state':32} {'band':10} {'diff':19} {'sty':4} t {'rec':>9}  outcome")
for p in plans:
    t = p["tuple"]
    rec = f"o{t['order_id']}" if "order_id" in t else (f"p{t['product_id']}" if "product_id" in t else "-")
    print(f"{p['key']:4} {p['group'][:5]:5} {t['role']:8} {t['user_id']:>5} {t['intent']:15} {t['record_state']:32} {t['refund_amount_band']:10} {t['difficulty']:19} {t['user_style'][:4]:4} {t['turn_count']} {rec:>9}  {p['expected'].get('outcome') or 'human_judgment'}")
