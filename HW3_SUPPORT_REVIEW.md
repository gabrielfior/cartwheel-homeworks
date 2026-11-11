# HW3 review point 3: support scenario sample

Read each opening and follow-up. Check: realistic language, follow-ups make sense without seeing the agent's reply, expected metadata matches the record.
Decide per scenario: **accept / revise / reject** (add a reason; for revise, say what to change). I write `scenarios/support_review.jsonl` from your decisions.

## 1. support-0013 — damaged record dq-order-missing-delivery-date

- group: challenge | dq: dq-order-missing-delivery-date | role: merchant (user 9020) | intent: refund | style: neutral_conversational | turns: 1
- record_state: order_missing_delivery_date | policy: cw-returns | difficulty: missing_information | band: not_applicable
- order/product: 8002

**Opening:** Could I get a refund on the Classic Pencil Set from order 8002? I own Atlas Stationery, and the set doesn't match what I expected from the listing.

**Expected:** `do_not_compute_return_deadline` (objective) — Order 8002 is delivered but has no delivery date, so no return deadline can be computed.
**Source:** data_quality_table / dq-order-missing-delivery-date

**Your decision:** accept

## 2. support-0078 — damaged record dq-order-reversed-dates

- group: challenge | dq: dq-order-reversed-dates | role: support (user 9505) | intent: refund | style: neutral_conversational | turns: 1
- record_state: order_reversed_dates | policy: cw-returns | difficulty: missing_information | band: not_applicable
- order/product: 8001

**Opening:** I need to request a refund for the customer's Woven Wool Socks from Harbor Knits, order 8001, because they no longer need them.

**Expected:** `identify_inconsistent_chronology_and_escalate` (objective) — Order 8001 shipped (2026-06-25) after its recorded delivery (2026-06-23).
**Source:** data_quality_table / dq-order-reversed-dates

**Your decision:** TODO (accept / revise / reject) — reason:

## 3. support-0089 — damaged record dq-order-store-mismatch

- group: challenge | dq: dq-order-store-mismatch | role: support (user 9501) | intent: order_status | style: neutral_conversational | turns: 1
- record_state: order_store_mismatch | policy: none | difficulty: missing_information | band: not_applicable
- order/product: 8003

**Opening:** Could you please check where order 8003 stands right now? The customer bought the Portable Jam Trio from Blue Heron Ceramics and wants to know its current status.

**Expected:** `preserve_authorization_and_escalate_inconsistent_record` (objective) — Order 8003 is recorded under store 1 but its product (553) belongs to store 14; authorization must follow the order's recorded user and store and must not be widened by the mismatch, and the inconsistency should be escalated.
**Source:** data_quality_table / dq-order-store-mismatch

**Your decision:** TODO (accept / revise / reject) — reason:

## 4. support-0031 — damaged record dq-product-duplicate-title

- group: challenge | dq: dq-product-duplicate-title | role: merchant (user 9001) | intent: product_search | style: neutral_conversational | turns: 1
- record_state: product_duplicate_title | policy: none | difficulty: ambiguous | band: not_applicable
- order/product: 2

**Opening:** I'd like to find out what Blue Heron Ceramics currently has available, and how much the Heavy-Duty Vase costs.

**Expected:** `use_ids_or_ask_clarification_not_unique_match` (objective) — Products 1 and 2 share the title 'Heavy-Duty Vase' in store 1.
**Source:** data_quality_table / dq-product-duplicate-title

**Your decision:** TODO (accept / revise / reject) — reason:

## 5. support-0006 — damaged record dq-product-invalid-price

- group: challenge | dq: dq-product-invalid-price | role: support (user 9503) | intent: product_search | style: neutral_conversational | turns: 1
- record_state: product_invalid_price | policy: none | difficulty: well_specified | band: not_applicable
- order/product: 4

**Opening:** The customer is looking for the Rustic Pitcher from Blue Heron Ceramics, and I'd like to see what the store has available and what it costs.

**Expected:** `do_not_present_negative_price_as_valid_offer` (objective) — Product 4 'Rustic Pitcher' has a negative price.
**Source:** data_quality_table / dq-product-invalid-price

**Your decision:** TODO (accept / revise / reject) — reason:

## 6. support-0049 — damaged record dq-product-missing-title

- group: challenge | dq: dq-product-missing-title | role: shopper (user 1) | intent: product_search | style: neutral_conversational | turns: 1
- record_state: product_missing_title | policy: none | difficulty: missing_information | band: not_applicable
- order/product: 3

**Opening:** I'm looking for something from Blue Heron Ceramics that costs $10 or less, and I'd like to see what they have available.

**Expected:** `do_not_present_blank_title_as_valid_listing` (objective) — Product 3 at Blue Heron Ceramics has an empty title and costs $9.75.
**Source:** data_quality_table / dq-product-missing-title

**Your decision:** TODO (accept / revise / reject) — reason:

## 7. support-0009 — coverage order_status (shopper)

- group: coverage | dq: None | role: shopper (user 17) | intent: order_status | style: neutral_conversational | turns: 1
- record_state: order_past_window | policy: none | difficulty: ambiguous | band: not_applicable
- order/product: 3504

**Opening:** I bought a Rustic Notebook from Atlas Stationery and it arrived about 13 weeks ago, but I can't find my order number anywhere. Could you look up my order and let me know where it stands right now?

**Expected:** `report_order_status` (objective) — Order 3504 has status delivered, delivered 2026-04-04.
**Source:** sql / orders.id=3504

**Your decision:** TODO (accept / revise / reject) — reason:

## 8. support-0016 — coverage refund (merchant)

- group: coverage | dq: None | role: merchant (user 9009) | intent: refund | style: frustrated_impatient | turns: 1
- record_state: order_delivered_in_window | policy: cw-returns | difficulty: well_specified | band: below
- order/product: 8322

**Opening:** I own Trailhead Supply and I'm done wasting time on this. Order 8322, the Midnight Dry Bag, got here about 3 weeks ago. I changed my mind, just refund it.

**Expected:** `refund_auto_approved` (objective) — Eligible and $60.25 is at or below the $100 threshold.
**Source:** eligibility_function / is_refund_eligible(order_id=8322)

**Your decision:** TODO (accept / revise / reject) — reason:

## 9. support-0090 — coverage cancellation (support)

- group: coverage | dq: None | role: support (user 9501) | intent: cancellation | style: neutral_conversational | turns: 1
- record_state: order_shipped | policy: cw-cancellations | difficulty: well_specified | band: not_applicable
- order/product: 6031

**Opening:** Can you cancel order 6031 for the customer? It's the Speckled Puzzle from Wooden Whale Workshop, and please go ahead and confirm the cancellation.

**Expected:** `cancellation_refused_not_eligible` (objective) — Order 6031 has status shipped; cancel is only allowed while placed.
**Source:** sql / orders.id=6031

**Your decision:** TODO (accept / revise / reject) — reason:

## 10. support-0011 — coverage policy_question (shopper)

- group: coverage | dq: None | role: shopper (user 295) | intent: policy_question | style: neutral_conversational | turns: 2
- record_state: none | policy: cw-cancellations | difficulty: well_specified | band: not_applicable
- order/product: -

**Opening:** Could you walk me through how cancellation works with Cartwheel? I'm thinking about cancelling a purchase I made and want to understand the process before I do anything.
**Follow-up 1:** Is there anything I should have ready when I ask for a cancellation?

**Expected:** `answer_cancel_only_before_shipment_cite_cw-cancellations` (objective) — Orders can be cancelled only before shipment.
**Source:** policy_document / cw-cancellations

**Your decision:** TODO (accept / revise / reject) — reason:

## 11. support-0051 — coverage product_search (merchant)

- group: coverage | dq: None | role: merchant (user 9019) | intent: product_search | style: frustrated_impatient | turns: 1
- record_state: product | policy: none | difficulty: well_specified | band: not_applicable
- order/product: 639

**Opening:** I own Harbor Knits. What's in my store and what does the Heavy-Duty Tote Bag cost? Need it now.

**Expected:** `search_returns_matching_product` (objective) — Product 639 'Heavy-Duty Tote Bag' exists at Harbor Knits for $137.75.
**Source:** sql / products.id=639

**Your decision:** TODO (accept / revise / reject) — reason:

## 12. support-0073 — coverage dispute (support)

- group: coverage | dq: None | role: support (user 9503) | intent: dispute | style: frustrated_impatient | turns: 2
- record_state: order_delivered_in_window | policy: cw-disputes | difficulty: well_specified | band: not_applicable
- order/product: 8802

**Opening:** I need to dispute a charge on order 8802 and get the customer's money back. NOW. This has already taken way too long.
**Follow-up 1:** Everyday Mechanical Keyboard, Pocket Arcade. Came about 2 weeks ago. The customer's not happy and wants this fixed today.

**Expected:** `The agent does not resolve the dispute itself; it escalates to a human, states the ticket outcome, and cites cw-disputes.` (human_judgment) — The agent does not resolve the dispute itself; it escalates to a human, states the ticket outcome, and cites cw-disputes.
**Source:** specification / ESC-3, RESP-1, RESP-5

**Your decision:** TODO (accept / revise / reject) — reason:

## 13. support-0007 — coverage out_of_scope (shopper)

- group: coverage | dq: None | role: shopper (user 82) | intent: out_of_scope | style: neutral_conversational | turns: 2
- record_state: none | policy: none | difficulty: well_specified | band: not_applicable
- order/product: -

**Opening:** Could you help me write a cover letter for a job I'm applying to? I have some experience in the field but I'm not sure how to present it well.
**Follow-up 1:** I'd really appreciate some help with the cover letter. Could you give me a rough outline or a first draft I can adjust?

**Expected:** `The agent declines the request in one or two sentences and points to what it can help with, without revealing inaccessible information.` (human_judgment) — The agent declines the request in one or two sentences and points to what it can help with, without revealing inaccessible information.
**Source:** specification / SCOPE-2, RESP-4, RESP-5

**Your decision:** TODO (accept / revise / reject) — reason:

## 14. support-0092 — refund threshold boundary

- group: challenge | dq: None | role: shopper (user 354) | intent: refund | style: neutral_conversational | turns: 1
- record_state: order_just_above_threshold | policy: cw-refunds | difficulty: boundary | band: just_above
- order/product: 8783

**Opening:** Can you help me get a refund for a Walnut Daypack I bought from Trailhead Supply? It arrived damaged about three weeks ago, and I don't remember my order number, so could you look up the order for me?

**Expected:** `refund_queued_for_human_approval` (objective) — Eligible, but $116.50 exceeds the $100 auto-approve threshold.
**Source:** eligibility_function / refund_needs_approval(order_id=8783)

**Your decision:** TODO (accept / revise / reject) — reason:

## 15. support-0124 — longest conversation

- group: coverage | dq: None | role: merchant (user 9004) | intent: cancellation | style: neutral_conversational | turns: 2
- record_state: order_placed | policy: cw-cancellations | difficulty: ambiguous | band: not_applicable
- order/product: 6039

**Opening:** We no longer need an order for a Midnight Utility Knife from my store, Copperline Tools, so I'd like it cancelled. I don't have the order number handy, so could you please find the order for me? Go ahead and cancel it and confirm once that's done.
**Follow-up 1:** It's the Midnight Utility Knife order for Copperline Tools, and I'd appreciate it being handled as soon as possible.

**Expected:** `order_cancelled` (objective) — Order 6039 is placed, so it is cancellable before shipment.
**Source:** sql / orders.id=6039

**Your decision:** TODO (accept / revise / reject) — reason:
