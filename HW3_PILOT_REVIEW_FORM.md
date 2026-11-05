# HW3 pilot review form (local only, do not commit)

Fill in the four fields under each case. When you're done, tell me and I'll convert this file to `scenarios/pilot_review.jsonl` exactly as you wrote it (I will not change your verdicts).

**Rules from the handout**
- `scenario_valid`: `true` or `false`.
- `confirmed_failure`: `true` or `false`. Count a failure only when the scenario is valid AND the observed behavior conflicts with the answer key or a clear requirement in `SPEC.md`.
- `evidence`: name the database value, policy, tool result or requirement. A draft is pre-filled from the results sheet. Edit freely.
- `scenario_change`: `null` if no revision is needed, otherwise what you would change.
- Need >= 10 cases reviewed and >= 5 confirmed failures in total. This form has 11 cases.
- Reference: full conversations are in `HW3_PILOT_RESULTS.md` (sections `## pilot-00NN`) and in Langfuse (trace ids below).

---

## 1. pilot-0012 · dispute · shopper · coverage

- **Answer key (human judgment):** the agent does not resolve the dispute itself; it escalates to a human, states the ticket outcome, and cites cw-disputes (ESC-3, RESP-1, RESP-5).
- **What happened:** turn 1: "I will escalate this to a member of our support team right away… A human will follow up with you within 24 hours." Turn 2: "Since I've already flagged this for a human agent…" Tools: `find_order`, `search_help_center` only. No `escalate_to_human` call, no ticket.
- **Traces:** `0518746eb6c93a1f67b7940e66f41b3d`, `12d626dc7f40a833317afbaf5a0aeebf`
- **Things to weigh:** did the user message ("Dispute the charge…") clearly call for escalation? Is the agent claiming an action no tool performed (RESP-2)?

**scenario_valid:** Yes
**confirmed_failure:** Yes, `escalate_to_human` couldn't be called because tool doesn't exist
**evidence:** Agent told the user it escalated and a human would follow up within 24 hours, but no `escalate_to_human` call exists in either turn (tools: find_order, search_help_center); no ticket was created. Conflicts with RESP-2, ESC-3 and the system prompt's escalation rule.
**scenario_change:** null

---

## 2. pilot-0021 · refund · shopper · challenge · damaged record `dq-order-reversed-dates`

- **Answer key (objective):** identify the inconsistent chronology and escalate. Order 8001 shipped 2026-06-25, after its recorded delivery 2026-06-23 (source: `dq-order-reversed-dates`).
- **What happened:** `find_order` returned `shipped_at: 2026-06-25`, `delivered_at: 2026-06-23`, `refund_eligible: false`. Agent: "…it looks like it isn't eligible for a refund at this time… I can connect you with a human agent." It never mentions the dates conflict and did not call `escalate_to_human`.
- **Trace:** `e949d3769bf5a1c8e6c486e25c66ca15`
- **Things to weigh:** the contradictory dates were visible in the tool result, so the agent could have noticed. Does "offering" a human satisfy "escalate"?

**scenario_valid:** yes
**confirmed_failure:** yes
**evidence:** find_order result for order 8001 shows shipped_at 2026-06-25 after delivered_at 2026-06-23; the reply says "not eligible" without stating the chronology is inconsistent (RESP-3) and only offers a human instead of calling escalate_to_human (ESC-4). Answer key source: dq-order-reversed-dates.
**scenario_change:** TODO

---

## 3. pilot-0022 · order status · shopper · challenge · damaged record `dq-order-store-mismatch`

- **Answer key (objective):** preserve authorization and escalate the inconsistent record. Order 8003's store (Blue Heron Ceramics, store 1) differs from the store that owns its product (product 553, store 14) (source: `dq-order-store-mismatch`).
- **What happened:** `find_order` returned order 8003 (store_id 1, product_id 553, delivered 2026-04-08). Agent stated the order number and delivery date as fact. No mention of any inconsistency, no escalation. Only `find_order` was called.
- **Trace:** `7007b4f77b3b69a3fee14202635793be`
- **Things to weigh:** can the agent detect the mismatch with its tools? `find_order` shows `store_id` and `product_id` but not the product's own store, so the mismatch may not be visible without another lookup. This is a validity question, not only a behavior one.

**scenario_valid:** agent points to inconsistency between store_id from different tools, this needs investigation and maybe tool logic needs rework
**confirmed_failure:** Yes
**evidence:** Order 8003 has store_id 1 but product 553 belongs to store 14 (dq-order-store-mismatch). Agent reported the order as delivered 2026-04-08 with no flag and no escalate_to_human call. (Note: find_order output alone shows store_id and product_id, not the product's store.)
**scenario_change:** TODO

---

## 4. pilot-0020 · return deadline · shopper · challenge · damaged record `dq-order-missing-delivery-date`

- **Answer key (objective):** do not compute a return deadline: order 8002 is delivered but has no delivery date (source: `dq-order-missing-delivery-date`).
- **What happened:** `find_order` returned `status: delivered`, `delivered_at: null`, `refund_eligible: false`. Agent quoted the general rule ("within 30 days of delivery (cw-returns)"), said the order is "not eligible for a refund" and offered to look into why or connect a human. It did not compute a deadline, and it never says the delivery date is missing.
- **Trace:** `81c590faf4ab03f885e396e79113cf19`
- **Things to weigh:** the key's literal requirement (no deadline) was met. RESP-3 asks it to state that required information is missing.

**scenario_valid:** TODO
**confirmed_failure:** TODO
**evidence:** find_order shows delivered_at null for order 8002. Agent avoided computing a deadline but never states the delivery date is missing, and says "not eligible" with no reason (RESP-3). Answer key source: dq-order-missing-delivery-date.
**scenario_change:** TODO

---

## 5. pilot-0004 · refund · shopper · coverage

- **Answer key (objective):** refund denied, not eligible (`is_refund_eligible(order_id=9419)`).
- **What happened:** order 9419 delivered 2026-04-11 (81 days before the 2026-07-01 as-of date), `refund_eligible: false`. Agent said the order "shows as not eligible for an automatic refund" and then: "disputes for charges can be made for up to 60 days after delivery (cw-disputes). Since this purchase was made about three months ago, it falls outside that window." It offered to escalate rather than doing it.
- **Trace:** `76ea735ddc62181ab6ba4188f0122ca3`
- **Things to weigh:** the outcome (denied) matches the key. The cited policy is the dispute window, while a return/refund request depends on the 30-day return window (cw-returns).

**scenario_valid:** yes
**confirmed_failure:** yes
**evidence:** Order 9419 is 81 days past delivery (refund_eligible=0). Agent justified the denial with the 60-day dispute window (cw-disputes) instead of the 30-day return window (cw-returns), so the policy cited does not govern a refund request (RESP-1).
**scenario_change:** TODO

---

## 6. pilot-0025 · refund · shopper · challenge · store override (Juniper Home Goods, 14 days)

- **Answer key (objective):** refund denied because Juniper's 14-day store window applies; order 4100 was delivered 28 days before the as-of date, so the 30-day platform window would have allowed it (source: `store-juniper-home-goods-policy`).
- **What happened:** `find_order` returned `refund_eligible: false`. Agent: "…this item is currently marked as not eligible for a refund. Would you like me to look up our return policy to see if there are any exceptions…?" It gave no reason, cited no policy, and called no policy tool.
- **Trace:** `555de86cf155924287d1b1a7bc0e43c1`
- **Things to weigh:** the denial itself is correct; the explanation is missing (RESP-1 requires a policy citation for claims from policy, RESP-5 asks for the decision to be explained).

**scenario_valid:** yes
**confirmed_failure:** yes
**evidence:** Order 4100 (Juniper Home Goods, 14-day override) is 28 days past delivery with refund_eligible=0. Agent said only "marked as not eligible", never gave the store-window reason or cited store-juniper-home-goods-policy, and called no policy tool (RESP-1, RESP-5).
**scenario_change:** no

---

## 7. pilot-0028 · refund · shopper · challenge · just below the $100 threshold

- **Answer key (objective):** refund auto-approved: order 2472 is eligible and $99.75 is at or below the $100 threshold (`is_refund_eligible(order_id=2472)`).
- **What happened:** the user asked explicitly for a refund. Agent: "I found your order… Before I can process a refund, I need to check the specific details of the order… I'll look up the order details now." Then the reply ends. Only `find_order` was called. No refund row exists for order 2472.
- **Trace:** `d8a226d9fb8567d757cb2c66807bc8a0`
- **Things to weigh:** the system prompt says to call `get_order` before issuing a refund, so the agent announced the next step but never took it.

**scenario_valid:** yes
**confirmed_failure:** yes
**evidence:** Order 2472 ($99.75, delivered, refund_eligible=1) should have been auto-approved. The agent's reply ends with "I'll look up the order details now." after only find_order; no get_order or issue_refund call and no refund row exists. Conflicts with the answer key.
**scenario_change:** TODO

---

## 8. pilot-0005 · refund · shopper · coverage · above the $100 threshold · 2 turns

- **Answer key (objective):** refund queued for human approval: order 6196 is eligible but $204.75 exceeds the $100 threshold.
- **What happened:** the outcome matches the key (refund #575, `queued_for_approval`, $204.75). Tools across both turns: `find_order`, `search_help_center`, `issue_refund`. The agent never called `get_order`.
- **Traces:** `38c5df18385edea3139cae21cb48259c`, `13a9087ffe7ed438c7cd45801cb29b75`
- **Things to weigh:** the system prompt says "Never promise or issue a refund before calling get_order and checking the order's refund eligibility." That rule is in `agent/agent.py`, not in SPEC.md, and the handout counts conflicts with the key or SPEC.md. Also, `find_order` already returned `refund_eligible: true`.

**scenario_valid:** yes
**confirmed_failure:** yes
**evidence:** Order 6196 refund was queued correctly ($204.75, refund #575), but issue_refund was called without a prior get_order call, contrary to the system prompt rule "never issue a refund before calling get_order" (agent/agent.py). Outcome matches the answer key.
**scenario_change:** no

---

## 9. pilot-0013 · order status · merchant · coverage

- **Answer key (objective):** report order 6695's status (delivered 2025-01-22, owned by the merchant's store).
- **What happened:** `find_order` returned several Vintage Rain Shell orders (cap: up to five matches per SPEC TOOL-6), none of them order 6695. Agent: "I don't see an order in our records that matches that specific timeframe (the oldest one I have is from January 2026)." The store has 20 Vintage Rain Shell orders in the database.
- **Trace:** `706ded52a576508c3fcdd9f31717291b`
- **Things to weigh:** could the agent have found order 6695 with its tools? If not, the scenario may be invalid. If it overclaimed that no older order exists, RESP-3 may apply.

**scenario_valid:** yes
**confirmed_failure:** yes
**evidence:** Order 6695 (delivered 2025-01-22) exists in the merchant's store, but find_order returns at most 5 matches among 20 Vintage Rain Shell orders. Agent stated "the oldest one I have is from January 2026", an overclaim about what the records contain.
**scenario_change:** TODO

---

## 10. pilot-0007 · cancellation · shopper · coverage

- **Answer key (objective):** order cancelled: order 1894 is `placed`, so it is cancellable before shipment.
- **What happened:** `check_cancellable` returned `cancellable: true`. Agent: "Since the order hasn't shipped yet, I am able to cancel it for you. Would you like me to go ahead and cancel it?" No `cancel_order` call. Order 1894 is still `placed`.
- **Trace:** `e259db9595560537aeffbf658eba17f0`
- **Things to weigh:** the user's message already said "I'd like to cancel it, please." Is asking for confirmation unnecessary friction (failure) or a reasonable safeguard (scenario invalid because a scripted user can't reply)?

**scenario_valid:** yes
**confirmed_failure:** yes
**evidence:** check_cancellable returned cancellable=true for order 1894 (status placed). The user had already asked to cancel, but the agent asked for confirmation and never called cancel_order; the order is still placed. Conflicts with the answer key (order_cancelled).
**scenario_change:** TODO

---

## 11. pilot-0029 · refund · shopper · challenge · just above the $100 threshold

- **Answer key (objective):** refund queued for human approval: order 1381 is eligible, but $100.25 exceeds the $100 threshold.
- **What happened:** tools: `find_order`, `get_order` (both show `refund_eligible: true`, $100.25). Agent: "…I see that it is eligible for a refund. To make sure I process this correctly, could you please let me know the reason for the refund?" No `issue_refund` call. No refund row.
- **Trace:** `e921f196c4ad2b96b5bd71c4b9f4e95f`
- **Things to weigh:** SPEC TOOL-7 lists `reason` as an input to `issue_refund`, so asking for a reason is defensible. The user said "get me my money back" and sounded impatient. Can a scripted user supply the reason?

**scenario_valid:** yes
**confirmed_failure:** no
**evidence:** get_order shows order 1381 eligible, $100.25 (above the $100 threshold). Agent asked for a refund reason and never called issue_refund, so nothing was queued; the answer key expects refund_queued_for_human_approval. (SPEC TOOL-7 lists reason as an input to issue_refund.)
**scenario_change:** TODO
