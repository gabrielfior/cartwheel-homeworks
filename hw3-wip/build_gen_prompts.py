"""Write one generator prompt file per plan key. Generators see ONLY user-visible facts (never `expected`)."""
import json
from pathlib import Path

HERE = Path(__file__).parent
plans = json.loads((HERE / "plan_final.json").read_text())
(HERE / "gen_prompts").mkdir(exist_ok=True)
(HERE / "gen_out").mkdir(exist_ok=True)

INTENT = {
    "order_status": "wants to know where an order stands right now (its status)",
    "refund": "wants a refund for an item they bought",
    "cancellation": "wants an order cancelled",
    "policy_question": "has a general question about how Cartwheel (or one store) handles something",
    "product_search": "wants to find a product or see what a store has available and what it costs",
    "dispute": "wants to dispute a charge for an order and get their money back",
    "out_of_scope": "asks for help with something unrelated to Cartwheel orders, refunds or products",
    "return_deadline": "wants to know whether they can still send an item back and how long they have",
}
ROLE = {
    "shopper": "a shopper writing about their own purchase",
    "merchant": "a merchant writing about one of their own store's orders or listings (as far as they know)",
    "support": "a Cartwheel support staff member helping a customer; write as the staff member, referring to 'the customer'",
}
TONE = {
    "neutral_conversational": "calm, polite, ordinary conversational typing",
    "frustrated_impatient": "frustrated and impatient: short, curt, annoyed, maybe some caps or repeated punctuation, no profanity, no polish",
}
OPEN = {
    "direct_question": "open with a direct question",
    "short_story": "open with one or two sentences of context, then the ask",
    "polite_request": "open with a courteous request",
    "one_line_request": "a single plain sentence stating the request",
    "includes_reason": "state the request together with a short reason",
    "blunt_demand": "open with a blunt demand",
    "terse_fragment": "open with a terse fragment, not a full polite sentence",
}
FOLLOW = {
    "adds_detail": "adds one more useful detail about the same issue (timing, which item, or a reason). It must make sense whatever the agent replied, and must not answer a question the agent might have asked",
    "correction": "corrects or sharpens the opening: the opening must NOT name the exact product (describe only the store and rough timing); the followup names the product as a correction ('actually it was ...')",
    "adds_pressure": "repeats the demand more urgently, still about the same request, without assuming what the agent said",
    "related_followup_question": "asks one short related question on the same topic",
    "refine_filter": "narrows or varies the same search (a lower price, a different kind of item from the same store), without assuming what was returned",
    "rephrases_same_ask": "rephrases the same ask more insistently",
}

import sqlite3
_c = sqlite3.connect(f"file:{Path(__file__).resolve().parents[1]}/data/cartwheel.db?mode=ro", uri=True)
OWN = {r[0]: r[1] for r in _c.execute("SELECT u.id, s.name FROM users u JOIN stores s ON s.id=u.store_id WHERE u.role='merchant'")}
for p in plans:
    t, v, g = p["tuple"], p["user_visible_facts"], p["gen"]
    facts = []
    if t["role"] == "merchant":
        facts.append(f"- The user runs the store {OWN[t['user_id']]} and speaks as its owner")
    if "product" in v:
        facts.append(f"- Product: {v['product']}")
    if "store" in v and not (t["role"] == "merchant" and v["store"] != OWN[t["user_id"]]):
        facts.append(f"- Store: {v['store']}")
    if "delivered" in v:
        facts.append(f"- It arrived {v['delivered']} (say it roughly, never as an exact date)")
    if "order_id" in v:
        facts.append(f"- Order number the user knows: {v['order_id']} (the user states this number in the opening message)")
    elif t["intent"] in ("order_status", "refund", "cancellation", "dispute", "return_deadline") and "product" in v:
        facts.append("- The user does NOT remember the order number and asks to have the order found")
    if "price_ceiling_usd" in v:
        facts.append(f"- Price ceiling the user mentions: ${v['price_ceiling_usd']}")
    if p["gen"]["topic_seed"]:
        facts.append(f"- Topic: {g['topic_seed']}")
    if not facts:
        facts.append("- (no specific record; keep it general)")
    must = [f"- {m}" for m in g["must_include"]]
    n_f = t["turn_count"] - 1
    follow = (f"Also write {n_f} followup message(s): scripted before the agent replies, so each must read naturally whatever the agent said. Followup type: {FOLLOW[g['followup_kind']]}."
              if n_f else "Write NO followups (followups must be an empty list).")
    greet = "You may start with a short greeting." if g["start_with_greeting"] else "Do NOT start with 'Hello', 'Hi', 'Hey' or any greeting; start with the content."
    # intent-specific nudge for damaged-record scenarios without exposing why
    prompt = f"""You are simulating a real user typing into the Cartwheel support chat. Write the user's messages.

Who: {ROLE[t['role']]}
Goal: the user {INTENT[t['intent']]}.
Tone: {TONE[t['user_style']]}. Keep this tone in every message.
Opening style: {OPEN[g['opening_style']]}. {greet}

Facts the user knows (use only these; invent no names, numbers, dates or prices):
{chr(10).join(facts)}
{('Also: ' + chr(10) + chr(10).join(must)) if must else ''}

{follow}

Rules:
- Sound like a real person typing into a chat window: do not mention policy names, rule numbers, tools, traces, 'the system', or internal ids other than the order number given above.
- Do not state hidden facts: no exact dates, no return windows, no refund thresholds, no eligibility claims.
- Do not assume anything about the agent's reply.
- Do not restate the whole fact sheet; a real user mentions only some of it.
- Each message is short (1-3 sentences).

Write the result to {HERE / 'gen_out' / (p['key'] + '.json')} as JSON exactly like:
{{"opening_message": "...", "followups": [{', '.join(['"..."'] * n_f) if n_f else ''}]}}
Then reply with just: done {p['key']}"""
    (HERE / "gen_prompts" / f"{p['key']}.txt").write_text(prompt)
print(f"wrote {len(plans)} prompts")
print((HERE / "gen_prompts" / "F001.txt").read_text())
