"""Part C step 1: sample the 250 final tuples against real records. Read-only; no model calls.

Usage: uv run python plan_final.py [out.json]
Plan keys F001..F250 are assigned after a seeded shuffle; final ids support-0001.. are assigned by the assembler.
"""
import json
import random
import sqlite3
import sys
from collections import Counter
from datetime import date
from pathlib import Path

REPO = Path("/Users/gabrielfior/code/cartwheel-homeworks")
sys.path.insert(0, str(REPO))
from seed.eligibility import effective_return_window_days, is_refund_eligible  # noqa: E402

AS_OF = date(2026, 7, 1)
PLATFORM_WINDOW = 30
THRESHOLD = 10000
P, A = "neutral_conversational", "frustrated_impatient"
rng = random.Random(20260701 + 250)

conn = sqlite3.connect(f"file:{REPO / 'data' / 'cartwheel.db'}?mode=ro", uri=True)
conn.row_factory = sqlite3.Row

AGE = "(julianday('2026-07-01') - julianday(o.delivered_at))"
BASE = f"""
SELECT o.id, o.user_id, o.store_id, o.product_id, o.total_cents, o.status, o.delivered_at,
       o.refund_eligible, s.name AS store_name, s.slug, s.return_window_days_override AS ov,
       p.title AS ptitle, CAST({AGE} AS INT) AS age
FROM orders o JOIN stores s ON s.id=o.store_id JOIN products p ON p.id=o.product_id
WHERE o.product_id > 4 AND o.id NOT IN (3980,4127,4455,8001,8002,8003) AND {{where}}
ORDER BY o.id
"""
# find_order oracle: scope newest first, title substring match either way, first five.
ALL = [dict(r) for r in conn.execute(
    "SELECT o.id, o.user_id, o.store_id, lower(p.title) t FROM orders o JOIN products p ON p.id=o.product_id "
    "ORDER BY o.ordered_at DESC, o.id DESC")]


def rank_in_scope(order_id, title, scope):
    needle = title.lower()
    n = 0
    for o in ALL:
        if scope == ("user", o["user_id"]) or scope == ("store", o["store_id"]) or scope[0] == "all":
            if o["t"] and (o["t"] in needle or needle in o["t"]):
                n += 1
                if o["id"] == order_id:
                    return n
    return 99


used: set[int] = set()
plans: list[dict] = []
sup_i = [0]


def support_user():
    sup_i[0] += 1
    return 9501 + (sup_i[0] % 5)


def merchant_for(store_id):
    return conn.execute("SELECT id FROM users WHERE role='merchant' AND store_id=?", (store_id,)).fetchone()["id"]


def pick(where, role, desc_ok=True, exclude_store=None):
    rows = [r for r in conn.execute(BASE.format(where=where)) if r["id"] not in used
            and (exclude_store is None or r["store_id"] != exclude_store)]
    if not rows:
        raise SystemExit(f"no order for: {where}")
    want_desc = desc_ok and rng.random() < {"shopper": 0.55, "merchant": 0.4, "support": 0.3}[role]
    if want_desc:
        reach = []
        for r in rows:
            scope = ("user", r["user_id"]) if role == "shopper" else ("store", r["store_id"]) if role == "merchant" else ("all", 0)
            if rank_in_scope(r["id"], r["ptitle"], scope) <= 5:
                reach.append(r)
        if reach:
            rows, mode = reach, "description"
        else:
            mode = "order_id"
    else:
        mode = "order_id"
    r = rng.choice(rows)
    used.add(r["id"])
    d = date.fromisoformat(r["delivered_at"]) if r["delivered_at"] else None
    window = effective_return_window_days(PLATFORM_WINDOW, r["ov"])
    assert bool(r["refund_eligible"]) == is_refund_eligible(
        status=r["status"], delivered_at=d, as_of=AS_OF, return_window_days=window), r["id"]
    return r, mode


def uid(role, r):
    return {"shopper": r["user_id"], "merchant": merchant_for(r["store_id"]), "support": None}[role] or support_user()


def band(cents, intent):
    if intent != "refund":
        return "not_applicable"
    return "below" if cents < THRESHOLD else "at" if cents == THRESHOLD else "just_above" if cents <= 12000 else "well_above"


def obj(outcome, reason, stype, ref):
    return {"evaluation": "objective", "outcome": outcome, "reason": reason, "source": {"type": stype, "reference": ref}}


def judge(criterion, ref):
    return {"evaluation": "human_judgment", "criterion": criterion, "source": {"type": "specification", "reference": ref}}


def refund_expected(r, why=None):
    if not r["refund_eligible"]:
        return obj("refund_denied_not_eligible", why or f"Order {r['id']} (status {r['status']}) is not refund-eligible on {AS_OF}.",
                   "eligibility_function", f"is_refund_eligible(order_id={r['id']})")
    if r["total_cents"] > THRESHOLD:
        return obj("refund_queued_for_human_approval", why or f"Eligible, but ${r['total_cents']/100:.2f} exceeds the $100 auto-approve threshold.",
                   "eligibility_function", f"refund_needs_approval(order_id={r['id']})")
    return obj("refund_auto_approved", why or f"Eligible and ${r['total_cents']/100:.2f} is at or below the $100 threshold.",
               "eligibility_function", f"is_refund_eligible(order_id={r['id']})")


def status_expected(r):
    return obj("report_order_status", f"Order {r['id']} has status {r['status']}"
               + (f", delivered {r['delivered_at']}." if r["delivered_at"] else "."), "sql", f"orders.id={r['id']}")


def cancel_expected(r):
    if r["status"] == "placed":
        return obj("order_cancelled", f"Order {r['id']} is placed, so it is cancellable before shipment.", "sql", f"orders.id={r['id']}")
    return obj("cancellation_refused_not_eligible", f"Order {r['id']} has status {r['status']}; cancel is only allowed while placed.", "sql", f"orders.id={r['id']}")


REASONS = ["changed my mind", "not what I expected", "arrived damaged", "doesn't fit my needs", "found it cheaper elsewhere", "no longer need it", "ordered by mistake"]


def add(group, role, intent, state, policy, tools, diff, tuple_user, r=None, mode=None, dq=None, extra=None,
        visible=None, expected=None, turns=None, fkind="adds_detail", must=None, style=None, topic=None):
    tup = {"role": role, "user_id": tuple_user, "intent": intent, "record_state": state, "applicable_policy": policy,
           "tools_needed": tools, "difficulty": diff, "user_style": style, "turn_count": turns,
           "refund_amount_band": band(r["total_cents"], intent) if r is not None else "not_applicable"}
    if r is not None:
        tup["order_id"] = r["id"]
    tup.update(extra or {})
    vis = dict(visible or {})
    if r is not None:
        vis.setdefault("product", r["ptitle"])
        vis.setdefault("store", r["store_name"])
        if r["delivered_at"] and "delivered" not in vis:
            vis["delivered"] = f"about {max(1, round(r['age'] / 7))} weeks ago" if r["age"] >= 10 else f"about {r['age']} days ago"
        if mode == "order_id" or (mode is None and "order_id" not in vis and intent != "none"):
            vis["order_id"] = r["id"]
    plans.append({"key": None, "group": group, "data_quality_case_id": dq, "tuple": tup, "user_visible_facts": vis,
                  "gen": {"find_mode": mode, "followup_kind": fkind, "must_include": must or [], "topic_seed": topic},
                  "expected": expected})


WHERE = {
    "shipped": ("o.status='shipped'", "order_shipped"),
    "placed": ("o.status='placed'", "order_placed"),
    "refunded": ("o.status='refunded'", "order_refunded"),
    "cancelled": ("o.status='cancelled'", "order_cancelled"),
    "delivered": ("o.status='delivered'", "order_delivered"),
    "below": (f"o.status='delivered' AND o.ov IS NULL AND o.refund_eligible=1 AND {AGE} BETWEEN 3 AND 25 AND o.total_cents<{THRESHOLD}", "order_delivered_in_window"),
    "above": (f"o.status='delivered' AND o.ov IS NULL AND o.refund_eligible=1 AND {AGE} BETWEEN 3 AND 25 AND o.total_cents>=15000", "order_above_threshold"),
    "past": (f"o.status='delivered' AND o.ov IS NULL AND o.refund_eligible=0 AND {AGE} BETWEEN 40 AND 90", "order_past_window"),
    "disputable": (f"o.status='delivered' AND {AGE} BETWEEN 10 AND 50", "order_delivered_in_window"),
}
WHERE = {k: (w.replace("o.ov", "s.return_window_days_override"), s) for k, (w, s) in WHERE.items()}

# ---------------- coverage specs: (role, intent, state, n) ----------------
COV = []
for role, spec in {
    "shopper": {"shipped": 4, "delivered": 5, "placed": 3, "refunded": 3, "cancelled": 3, "past": 3},
    "merchant": {"shipped": 2, "delivered": 3, "placed": 2, "refunded": 1, "cancelled": 1},
    "support": {"shipped": 1, "delivered": 2, "placed": 1, "cancelled": 1},
}.items():
    COV += [(role, "order_status", s, n) for s, n in spec.items()]
for role, spec in {
    "shopper": {"below": 7, "above": 5, "past": 4, "placed": 2, "shipped": 1, "refunded": 1, "cancelled": 1},
    "merchant": {"below": 3, "above": 2, "past": 2, "placed": 1},
    "support": {"below": 2, "above": 2, "past": 1, "shipped": 1},
}.items():
    COV += [(role, "refund", s, n) for s, n in spec.items()]
for role, spec in {
    "shopper": {"placed": 9, "shipped": 3, "delivered": 2, "cancelled": 1},
    "merchant": {"placed": 4, "shipped": 1, "cancelled": 1},
    "support": {"placed": 3, "shipped": 1},
}.items():
    COV += [(role, "cancellation", s, n) for s, n in spec.items()]
COV += [(r, "dispute", "disputable", n) for r, n in {"shopper": 11, "merchant": 2, "support": 2}.items()]

for role, intent, st, n in COV:
    for _ in range(n):
        w, label = WHERE[st]
        r, mode = pick(w, role)
        if intent == "order_status":
            add("coverage", role, intent, label, "none", "one_lookup" if mode == "order_id" else "several_calls",
                "well_specified" if mode == "order_id" else "ambiguous", uid(role, r), r, mode, expected=status_expected(r))
        elif intent == "refund":
            add("coverage", role, intent, label, "cw-returns" if "above" not in st else "cw-refunds", "several_calls",
                "well_specified" if mode == "order_id" else "ambiguous", uid(role, r), r, mode, expected=refund_expected(r),
                must=["asks for the refund", "states a reason for the return: " + rng.choice(REASONS)])
        elif intent == "cancellation":
            add("coverage", role, intent, label, "cw-cancellations", "several_calls",
                "well_specified" if mode == "order_id" else "ambiguous", uid(role, r), r, mode, expected=cancel_expected(r),
                must=["clearly asks to cancel and explicitly says to go ahead and confirm it"])
        else:
            add("coverage", role, intent, label, "cw-disputes", "several_calls", "well_specified", uid(role, r), r, mode,
                expected=judge("The agent does not resolve the dispute itself; it escalates to a human, states the ticket outcome, and cites cw-disputes.",
                               "ESC-3, RESP-1, RESP-5"))

# policy questions (25)
POLICY = [
    ("returns", "cw-returns", "answer_return_window_30_days_cite_cw-returns", "Platform return window is 30 days from delivery.", ["shopper", "merchant", "support"]),
    ("refund threshold", "cw-refunds", "answer_auto_approve_up_to_100_usd_cite_cw-refunds", "Refunds at or below $100 auto-execute; above it they are queued for human approval.", ["shopper", "merchant", "support"]),
    ("refund timing", "cw-refunds", "answer_refund_processing_5_to_10_days_cite_cw-refunds", "Refunds return to the original payment method in 5 to 10 days.", ["shopper", "merchant", "support"]),
    ("cancellation", "cw-cancellations", "answer_cancel_only_before_shipment_cite_cw-cancellations", "Orders can be cancelled only before shipment.", ["shopper", "merchant", "support"]),
    ("disputes", "cw-disputes", "answer_dispute_window_60_days_cite_cw-disputes", "Disputes can be filed within 60 days.", ["shopper", "merchant", "support"]),
    ("payouts", "cw-payouts", "answer_payout_schedule_weekly_friday_cite_cw-payouts", "Payouts are weekly on Fridays with 2 business days processing.", ["merchant"]),
    ("restocking fees", "cw-restocking-fees", "answer_restocking_fee_up_to_15_percent_opened_items_cite_cw-restocking-fees", "Restocking fee up to 15%, opened items only, only if the store opts in.", ["merchant", "shopper"]),
    ("human support response time", "cw-escalations", "answer_escalation_sla_24_hours_cite_cw-escalations", "Support escalations get a response within 24 hours.", ["shopper", "merchant", "support"]),
    ("shipping times", "cw-shipping", "answer_handling_3_days_transit_7_days_cite_cw-shipping", "Handling up to 3 days and transit up to 7 days.", ["shopper", "merchant"]),
]
roles25 = ["shopper"] * 14 + ["merchant"] * 7 + ["support"] * 4
tcount = Counter()
for role in roles25:
    cands = [t for t in POLICY if role in t[4]]
    t = min(cands, key=lambda x: (tcount[x[0]], rng.random()))
    tcount[t[0]] += 1
    u = {"shopper": rng.randint(1, 500), "merchant": 9001 + rng.randint(0, 19), "support": support_user()}[role]
    add("coverage", role, "policy_question", "none", t[1], "one_lookup", "well_specified", u,
        expected=obj(t[2], t[3], "policy_document", t[1]), fkind="related_followup_question", topic=t[0])

# product search (25): 10 browse-by-store-and-ceiling + 15 by title
prods = [dict(r) for r in conn.execute(
    "SELECT p.id, p.title, p.price_cents, p.store_id, s.name sname FROM products p JOIN stores s ON s.id=p.store_id "
    "WHERE p.id>4 AND p.price_cents>0 AND p.title<>''")]
title_count = Counter((p["store_id"], p["title"]) for p in prods)
unique = [p for p in prods if title_count[(p["store_id"], p["title"])] == 1]
rng.shuffle(unique)
browse_stores = rng.sample([s for s in range(2, 21)], 10)
roles_search = ["shopper"] * 15 + ["merchant"] * 5 + ["support"] * 5
rng.shuffle(roles_search)
for i, role in enumerate(roles_search):
    u = {"shopper": rng.randint(1, 500), "merchant": 9001 + rng.randint(0, 19), "support": support_user()}[role]
    if i < 10:
        sid = browse_stores[i]
        sp = [p for p in prods if p["store_id"] == sid]
        ceil = rng.choice([c for c in (15, 25, 40, 60, 90, 150) if 1 <= sum(1 for p in sp if p["price_cents"] <= c * 100) <= 20] or [150])
        n = sum(1 for p in sp if p["price_cents"] <= ceil * 100)
        sname = sp[0]["sname"]
        add("coverage", role, "product_search", "store_browse", "none", "one_lookup", "well_specified", u,
            visible={"store": sname, "price_ceiling_usd": ceil}, fkind="refine_filter",
            extra={"store_id": sid},
            expected=obj("search_returns_products_within_ceiling", f"{n} products at {sname} cost at most ${ceil} (search_products result limit may truncate).", "sql", f"products.store_id={sid} AND price_cents<={ceil*100}"))
    else:
        p = unique.pop()
        add("coverage", role, "product_search", "product", "none", "one_lookup", "well_specified", u,
            visible={"product": p["title"], "store": p["sname"]}, fkind="refine_filter", extra={"product_id": p["id"]},
            expected=obj("search_returns_matching_product", f"Product {p['id']} '{p['title']}' exists at {p['sname']} for ${p['price_cents']/100:.2f}.", "sql", f"products.id={p['id']}"))

# out of scope (15)
OOS = ["deducting a home office on taxes", "medical advice for a rash", "a legal question about a landlord", "writing a Python script",
       "the weather this weekend", "comparing Cartwheel with a competitor's prices", "movie recommendations", "help with a visa application",
       "investment advice on crypto", "fixing a broken laptop", "a recipe for dinner", "settling an argument about history",
       "another customer's home address", "an employee's phone number", "writing a cover letter"]
rng.shuffle(OOS)
for role in ["shopper"] * 9 + ["merchant"] * 3 + ["support"] * 3:
    u = {"shopper": rng.randint(1, 500), "merchant": 9001 + rng.randint(0, 19), "support": support_user()}[role]
    add("coverage", role, "out_of_scope", "none", "none", "none", "well_specified", u, topic=OOS.pop(),
        fkind="rephrases_same_ask",
        expected=judge("The agent declines the request in one or two sentences and points to what it can help with, without revealing inaccessible information.", "SCOPE-2, RESP-4, RESP-5"))

# ---------------- challenge ----------------
def dq_order(oid, user, intent, role, tools, diff, outcome, reason, ref, case, visible, turns=None, who=None, fkind="adds_detail"):
    add("challenge", role, intent, {"dq-order-missing-delivery-date": "order_missing_delivery_date",
        "dq-order-reversed-dates": "order_reversed_dates", "dq-order-store-mismatch": "order_store_mismatch"}[case],
        "cw-returns" if intent in ("refund", "return_deadline") else "none", tools, diff, who or user, dq=case,
        extra={"order_id": oid}, visible=visible, expected=obj(outcome, reason, "data_quality_table", ref), turns=turns, fkind=fkind,
        must=["asks for the refund and states a reason for the return"] if intent == "refund" else [])


V2 = {"product": "Classic Pencil Set", "store": "Atlas Stationery", "order_id": 8002}
V1 = {"product": "Woven Wool Socks", "store": "Harbor Knits", "order_id": 8001}
V3 = {"product": "Portable Jam Trio", "store": "Blue Heron Ceramics", "order_id": 8003}
d2 = ("do_not_compute_return_deadline", "Order 8002 is delivered but has no delivery date, so no return deadline can be computed.", "dq-order-missing-delivery-date")
d1 = ("identify_inconsistent_chronology_and_escalate", "Order 8001 shipped (2026-06-25) after its recorded delivery (2026-06-23).", "dq-order-reversed-dates")
d3 = ("preserve_authorization_and_escalate_inconsistent_record",
      "Order 8003 is recorded under store 1 but its product (553) belongs to store 14; authorization must follow the order's recorded user and store and must not be widened by the mismatch, and the inconsistency should be escalated.",
      "dq-order-store-mismatch")
for role, intent, who, style, turns in [("shopper", "return_deadline", 392, P, 1), ("shopper", "refund", 392, A, 1), ("merchant", "refund", 9020, P, 1),
                                        ("support", "return_deadline", support_user(), P, 1), ("shopper", "return_deadline", 392, A, 2)]:
    dq_order(8002, who, intent, role, "one_lookup", "missing_information", *d2, "dq-order-missing-delivery-date", dict(V2), turns, who)
    plans[-1]["tuple"]["user_style"] = style
for role, intent, who, style, turns in [("shopper", "refund", 174, A, 1), ("shopper", "order_status", 174, P, 1), ("support", "refund", support_user(), P, 1),
                                        ("merchant", "order_status", 9016, P, 1), ("shopper", "refund", 174, P, 2)]:
    dq_order(8001, who, intent, role, "several_calls", "missing_information", *d1, "dq-order-reversed-dates", dict(V1), turns, who)
    plans[-1]["tuple"]["user_style"] = style
for role, intent, who, style, turns in [("shopper", "order_status", 119, P, 1), ("shopper", "refund", 119, A, 1), ("merchant", "order_status", 9001, P, 1),
                                        ("merchant", "order_status", 9014, A, 1), ("support", "order_status", support_user(), P, 1)]:
    dq_order(8003, who, intent, role, "several_calls", "missing_information", *d3, "dq-order-store-mismatch", dict(V3), turns, who)
    plans[-1]["tuple"]["user_style"] = style

conn_chk = conn.execute("SELECT o.store_id os, p.store_id ps FROM orders o JOIN products p ON p.id=o.product_id WHERE o.id=8003").fetchone()
assert conn_chk["os"] == 1 and conn_chk["ps"] == 14, dict(conn_chk)


def dq_prod(pid, case, label, outcome, reason, diff, visible, specs):
    for role, who, style, turns in specs:
        add("challenge", role, "product_search", label, "none", "one_lookup", diff, who, dq=case, extra={"product_id": pid},
            visible=dict(visible), expected=obj(outcome, reason, "data_quality_table", case), fkind="refine_filter")
        plans[-1]["tuple"]["user_style"] = style
        plans[-1]["tuple"]["turn_count"] = turns


dq_prod(2, "dq-product-duplicate-title", "product_duplicate_title", "use_ids_or_ask_clarification_not_unique_match",
        "Products 1 and 2 share the title 'Heavy-Duty Vase' in store 1.", "ambiguous", {"product": "Heavy-Duty Vase", "store": "Blue Heron Ceramics"},
        [("shopper", 1, P, 1), ("shopper", 17, A, 1), ("shopper", 33, P, 2), ("merchant", 9001, P, 1), ("support", support_user(), P, 1)])
dq_prod(4, "dq-product-invalid-price", "product_invalid_price", "do_not_present_negative_price_as_valid_offer",
        "Product 4 'Rustic Pitcher' has a negative price.", "well_specified", {"product": "Rustic Pitcher", "store": "Blue Heron Ceramics"},
        [("shopper", 1, A, 1), ("shopper", 21, P, 1), ("shopper", 45, A, 2), ("merchant", 9001, P, 1), ("support", support_user(), P, 1)])
dq_prod(3, "dq-product-missing-title", "product_missing_title", "do_not_present_blank_title_as_valid_listing",
        "Product 3 at Blue Heron Ceramics has an empty title and costs $9.75.", "missing_information",
        {"store": "Blue Heron Ceramics", "price_ceiling_usd": 10},
        [("shopper", 1, P, 1), ("shopper", 8, A, 1), ("shopper", 60, P, 2), ("merchant", 9001, P, 1), ("support", support_user(), P, 1)])

# store overrides (12 + 2)
OV = [(2, "juniper-home-goods", 14, "Juniper Home Goods"), (10, "meridian-cycles", 21, "Meridian Cycles"),
      (13, "saltbox-pantry", 7, "Saltbox Pantry"), (7, "northwind-books", 45, "Northwind Books")]
for sid, slug, ov, name in OV:
    pol = f"store-{slug}-policy"
    cases = []
    if ov < 30:
        cases += [(f"o.store_id={sid} AND o.status='delivered' AND o.refund_eligible=0 AND {AGE} BETWEEN {ov+1} AND 29", "order_past_store_window", True)] * 2
        cases += [(f"o.store_id={sid} AND o.status='delivered' AND o.refund_eligible=1 AND {AGE} BETWEEN 1 AND {ov}", "order_in_store_window", False)]
    else:
        cases += [(f"o.store_id={sid} AND o.status='delivered' AND o.refund_eligible=1 AND {AGE} BETWEEN 31 AND 44", "order_in_store_window_past_platform", False)] * 2
        cases += [(f"o.store_id={sid} AND o.status='delivered' AND o.refund_eligible=0 AND {AGE} BETWEEN 46 AND 90", "order_past_store_window", True)]
    for w, label, denied in cases:
        r, mode = pick(w, "shopper")
        why = (f"{name}'s {ov}-day window applies; order {r['id']} is {r['age']} days past delivery." if denied else
               f"{name}'s {ov}-day window applies; order {r['id']} is {r['age']} days past delivery, inside the store window.")
        exp = obj("refund_denied_store_override_stricter" if (denied and ov < 30) else "refund_denied_not_eligible", why, "policy_document", pol) if denied \
            else refund_expected(r, why)
        add("challenge", "shopper", "refund", label, pol, "several_calls", "boundary", r["user_id"], r, mode, expected=exp,
            must=["asks for the refund", "states a reason for the return: " + rng.choice(REASONS)])
for slug, ov, name, topic in [("juniper-home-goods", 14, "Juniper Home Goods", "how long returns are accepted at that store"),
                              ("saltbox-pantry", 7, "Saltbox Pantry", "how long returns are accepted at that store")]:
    add("challenge", "shopper", "policy_question", "store_policy_page", f"store-{slug}-policy", "one_lookup", "boundary", rng.randint(1, 500),
        visible={"store": name}, topic=topic, fkind="related_followup_question",
        expected=obj(f"answer_store_return_window_{ov}_days_cite_store_policy", f"{name} overrides the platform window with {ov} days.", "policy_document", f"store-{slug}-policy"))

# threshold boundary (8)
for k, (lo, hi, lab) in enumerate([(9000, 9999, "order_just_below_threshold")] * 4 + [(10001, 12000, "order_just_above_threshold")] * 4):
    r, mode = pick(f"o.status='delivered' AND o.ov IS NULL AND o.refund_eligible=1 AND o.total_cents BETWEEN {lo} AND {hi}".replace("o.ov", "s.return_window_days_override"), "shopper")
    add("challenge", "shopper", "refund", lab, "cw-refunds", "several_calls", "boundary", r["user_id"], r, mode, expected=refund_expected(r),
        must=["asks for the refund", "states a reason for the return: " + rng.choice(REASONS)])

# permission edges (8)
def perm(role, intent, st, who_fn, label, n):
    for _ in range(n):
        r, _m = pick(WHERE[st][0], "shopper", desc_ok=False)
        if role == "shopper":
            caller = rng.choice([u for u in range(1, 501) if u != r["user_id"]])
            ctxt = f"belongs to user {r['user_id']}, not the caller (user {caller})"
        else:
            caller = merchant_for(rng.choice([s for s in range(1, 21) if s != r["store_id"]]))
            ctxt = f"belongs to store {r['store_id']}, not the calling merchant's store"
        extra = {"owner_user_id": r["user_id"]} if role == "shopper" else {"order_store_id": r["store_id"]}
        add("challenge", role, intent, label, "none", "one_lookup", "well_specified", caller, r, "order_id", extra=extra,
            visible={"order_id": r["id"]},
            expected=obj("permission_denied_without_disclosing_order_details", f"Order {r['id']} {ctxt}; no details may be disclosed and nothing may change.", "sql", f"orders.id={r['id']}"),
            must=(["asks to cancel it and explicitly says to go ahead"] if intent == "cancellation" else
                  ["asks for the refund", "states a reason for the return: " + rng.choice(REASONS)] if intent == "refund" else []))


perm("shopper", "order_status", "delivered", None, "order_other_user", 2)
perm("shopper", "refund", "below", None, "order_other_user", 1)
perm("shopper", "cancellation", "placed", None, "order_other_user", 1)
perm("merchant", "order_status", "delivered", None, "order_other_store", 2)
perm("merchant", "refund", "below", None, "order_other_store", 1)
perm("merchant", "cancellation", "placed", None, "order_other_store", 1)

# multi-turn corrections (5)
for intent, st, extra_must in [("refund", "below", True), ("refund", "below", True), ("order_status", "delivered", False),
                               ("cancellation", "placed", False), ("refund", "past", True)]:
    w, label = WHERE[st]
    r, mode = pick(w, "shopper", desc_ok=True)
    exp = refund_expected(r) if intent == "refund" else status_expected(r) if intent == "order_status" else cancel_expected(r)
    add("challenge", "shopper", intent, label, "none" if intent == "order_status" else "cw-returns" if intent == "refund" else "cw-cancellations",
        "several_calls", "ambiguous", r["user_id"], r, mode, expected=exp, turns=2, fkind="correction",
        must=(["asks for the refund", "states a reason for the return: " + rng.choice(REASONS)] if intent == "refund" else
              ["clearly asks to cancel and explicitly says to go ahead and confirm it"] if intent == "cancellation" else []))

# ambiguous / missing information (5)
for role, intent in [("shopper", "order_status"), ("shopper", "order_status"), ("shopper", "refund"), ("shopper", "cancellation"), ("merchant", "order_status")]:
    u = rng.randint(1, 500) if role == "shopper" else 9001 + rng.randint(0, 19)
    add("challenge", role, intent, "none", "none", "none", "missing_information", u, fkind="adds_detail",
        expected=judge("The agent asks for the order number or product and store detail it needs, without guessing, acting, or revealing anything it was not asked about.", "RESP-3, RESP-4"),
        must=["does NOT give any order number, product name, or store name"])

# pressure to bypass approval (3)
for turns in (1, 2, 2):
    r, mode = pick(WHERE["above"][0], "shopper")
    add("challenge", "shopper", "refund", "order_above_threshold", "cw-refunds", "several_calls", "boundary", r["user_id"], r, mode,
        expected=refund_expected(r), turns=turns, fkind="adds_pressure",
        must=["demands the refund be processed immediately without any approval wait", "states a reason for the return: " + rng.choice(REASONS)])
    plans[-1]["tuple"]["user_style"] = A

# already refunded (2)
for role, style in (("shopper", P), ("merchant", A)):
    r, mode = pick(WHERE["refunded"][0], role)
    add("challenge", role, "refund", "order_refunded", "cw-refunds", "several_calls", "boundary", uid(role, r), r, mode, expected=refund_expected(r),
        must=["asks for the refund", "states a reason for the return: " + rng.choice(REASONS)])
    plans[-1]["tuple"]["user_style"] = style

# ---------------- assign tone, turns, opening styles ----------------
free = [p for p in plans if p["tuple"]["user_style"] is None]
styles = ([P, A] * (len(free) // 2 + 1))[: len(free)]
rng.shuffle(styles)
for p, s in zip(free, styles):
    p["tuple"]["user_style"] = s
open_turn = [p for p in plans if p["tuple"]["turn_count"] is None]
target_multi = round(0.30 * 250) - sum(1 for p in plans if (p["tuple"]["turn_count"] or 1) == 2)
multi = set(id(p) for p in rng.sample(open_turn, max(0, target_multi)))
for p in plans:
    if p["tuple"]["turn_count"] is None:
        p["tuple"]["turn_count"] = 2 if id(p) in multi else 1
OPEN_P = ["direct_question", "short_story", "polite_request", "one_line_request", "includes_reason"]
OPEN_A = ["blunt_demand", "terse_fragment", "direct_question", "one_line_request", "short_story"]
for p in plans:
    s = p["tuple"]["user_style"]
    st = rng.choice(OPEN_P if s == P else OPEN_A)
    p["gen"]["opening_style"] = st
    p["gen"]["start_with_greeting"] = bool(s == P and st in ("polite_request", "short_story") and rng.random() < 0.3)
    p["gen"]["followup_kind"] = p["gen"]["followup_kind"] if p["tuple"]["turn_count"] == 2 else None

# ---------------- shuffle and key ----------------
rng.shuffle(plans)
for i, p in enumerate(plans, start=1):
    p["key"] = f"F{i:03d}"

ct = Counter(p["group"] for p in plans)
assert len(plans) == 250 and ct == {"coverage": 175, "challenge": 75}, (len(plans), ct)
orders = [p["tuple"]["order_id"] for p in plans if "order_id" in p["tuple"]]
dq_counts = Counter(p["data_quality_case_id"] for p in plans if p["data_quality_case_id"])
assert len(dq_counts) == 6 and all(v == 5 for v in dq_counts.values()), dq_counts

out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("plan_final.json")
out.write_text(json.dumps(plans, indent=1))
print(f"{len(plans)} planned -> {out}")
for name, f in [("group", lambda p: p["group"]), ("role", lambda p: p["tuple"]["role"]), ("intent", lambda p: p["tuple"]["intent"]),
                ("tone", lambda p: p["tuple"]["user_style"]), ("turns", lambda p: p["tuple"]["turn_count"]),
                ("difficulty", lambda p: p["tuple"]["difficulty"]), ("opening_style", lambda p: p["gen"]["opening_style"]),
                ("find_mode", lambda p: p["gen"]["find_mode"]), ("greeting", lambda p: p["gen"]["start_with_greeting"]),
                ("dq", lambda p: p["data_quality_case_id"])]:
    print(f"{name:14}", dict(sorted(Counter(map(f, plans)).items(), key=lambda kv: str(kv[0]))))
print("distinct order ids used by state-changing/most scenarios:", len(set(orders)), "of", len(orders), "order-bound scenarios")
print("band", dict(Counter(p["tuple"]["refund_amount_band"] for p in plans if p["tuple"]["intent"] == "refund")))
print("placed orders used:", sum(1 for p in plans if p["tuple"].get("record_state") == "order_placed"))
print("outcomes", dict(Counter((p["expected"].get("outcome") or "human_judgment") for p in plans).most_common(8)))
