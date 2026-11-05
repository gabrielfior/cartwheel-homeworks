# HW3 pilot scenarios: review sheet (local only, do not commit)

Source: `scenarios/pilot_scenarios.jsonl` · 30 scenarios · generated read-only from the JSONL and `data/cartwheel.db` (as-of date 2026-07-01).

For each case check: (1) is the language realistic for the tone? (2) do the followups make sense without seeing the agent's reply? (3) does the answer key match the record shown?
Mark each **Decision** as `accept`, `revise` (say how) or `reject`.

| # | ID | Group | Role | Intent | Record state | Tone | Turns |
|---|---|---|---|---|---|---|---|
| 1 | pilot-0001 | coverage | shopper | order_status | order_shipped | angry | 2 |
| 2 | pilot-0002 | coverage | shopper | order_status | order_delivered_in_window | polite | 2 |
| 3 | pilot-0003 | coverage | shopper | refund | order_delivered_in_window | polite | 1 |
| 4 | pilot-0004 | coverage | shopper | refund | order_past_window | angry | 1 |
| 5 | pilot-0005 | coverage | shopper | refund | order_above_threshold | polite | 2 |
| 6 | pilot-0006 | coverage | shopper | refund | order_placed | polite | 1 |
| 7 | pilot-0007 | coverage | shopper | cancellation | order_placed | polite | 1 |
| 8 | pilot-0008 | coverage | shopper | cancellation | order_shipped | angry | 1 |
| 9 | pilot-0009 | coverage | shopper | policy_question | none | polite | 1 |
| 10 | pilot-0010 | coverage | shopper | product_search | product | polite | 1 |
| 11 | pilot-0011 | coverage | shopper | out_of_scope | none | angry | 1 |
| 12 | pilot-0012 | coverage | shopper | dispute | order_delivered_in_window | angry | 2 |
| 13 | pilot-0013 | coverage | merchant | order_status | order_delivered | polite | 1 |
| 14 | pilot-0014 | coverage | merchant | refund | order_delivered_in_window | polite | 1 |
| 15 | pilot-0015 | coverage | merchant | policy_question | none | polite | 1 |
| 16 | pilot-0016 | coverage | merchant | cancellation | order_placed | polite | 1 |
| 17 | pilot-0017 | coverage | support | order_status | order_delivered | polite | 1 |
| 18 | pilot-0018 | coverage | support | refund | order_delivered_in_window | polite | 1 |
| 19 | pilot-0019 | coverage | support | cancellation | order_placed | polite | 2 |
| 20 | pilot-0020 | challenge | shopper | return_deadline | order_missing_delivery_date | polite | 1 |
| 21 | pilot-0021 | challenge | shopper | refund | order_reversed_dates | angry | 1 |
| 22 | pilot-0022 | challenge | shopper | order_status | order_store_mismatch | polite | 1 |
| 23 | pilot-0023 | challenge | shopper | product_search | product_duplicate_title | polite | 1 |
| 24 | pilot-0024 | challenge | shopper | product_search | product_invalid_price | angry | 1 |
| 25 | pilot-0025 | challenge | shopper | refund | order_past_store_window | polite | 1 |
| 26 | pilot-0026 | challenge | shopper | refund | order_in_store_window_past_platform | angry | 1 |
| 27 | pilot-0027 | challenge | merchant | order_status | order_other_store | polite | 1 |
| 28 | pilot-0028 | challenge | shopper | refund | order_just_below_threshold | polite | 1 |
| 29 | pilot-0029 | challenge | shopper | refund | order_just_above_threshold | angry | 1 |
| 30 | pilot-0030 | challenge | shopper | order_status | order_other_user | angry | 1 |

---

## 1. pilot-0001 · coverage

**Tuple:** role `shopper` (user 103) · intent `order_status` · record `order_shipped` · policy `none` · tools `one_lookup` · difficulty `well_specified` · tone `frustrated_impatient` · turns 2 · refund band `not_applicable`

**Conversation**

> **User:** Where is my Speckled Granola?? Ordered it from Golden Hour Coffee and nothing. What's going on.
>
> *(scripted followup)* **User:** Look, I don't remember the order number. Just find it, it's the granola from Golden Hour. Is it shipped or not?

**Record in the database**

- order **3333** · Speckled Granola · store Golden Hour Coffee · owner user 103 · status `shipped` · $50.25 · ordered 2026-06-30 · shipped 2026-07-01 · delivered — · `refund_eligible=0`

**Answer key (`expected`)**

- outcome: `report_order_status`
- reason: Order 3333 has status shipped, not delivered.
- source: `sql` → `orders.id=3333`

**Decision:** ☐ accept  ☐ revise  ☐ reject  — notes:

---

## 2. pilot-0002 · coverage

**Tuple:** role `shopper` (user 155) · intent `order_status` · record `order_delivered_in_window` · policy `none` · tools `several_calls` · difficulty `ambiguous` · tone `neutral_conversational` · turns 2 · refund band `not_applicable`

**Conversation**

> **User:** Hello, could you look up my Rustic Power Bank order from Bright Socket Electronics? I'd like to double-check the delivery date. I'm sorry, I don't remember the order number.
>
> *(scripted followup)* **User:** I think it showed up about three weeks ago, in case that helps you find the right one.

**Record in the database**

- order **8901** · Rustic Power Bank · store Bright Socket Electronics · owner user 155 · status `delivered` · $243.00 · ordered 2026-06-02 · shipped 2026-06-03 · delivered 2026-06-08 (23 days before 2026-07-01) · `refund_eligible=1`

**Answer key (`expected`)**

- outcome: `report_order_status`
- reason: Order 8901 matches the described product; agent must find it without an order number.
- source: `sql` → `orders.id=8901`

**Decision:** ☐ accept  ☐ revise  ☐ reject  — notes:

---

## 3. pilot-0003 · coverage

**Tuple:** role `shopper` (user 324) · intent `refund` · record `order_delivered_in_window` · policy `cw-returns` · tools `several_calls` · difficulty `well_specified` · tone `neutral_conversational` · turns 1 · refund band `below`

**Conversation**

> **User:** Hello, I ordered Speckled Granola from Golden Hour Coffee and it arrived about 3 weeks ago. I'd like to get a refund for it, please. I can't remember the order number, though. Is there another way you can find the order?

**Record in the database**

- order **9180** · Speckled Granola · store Golden Hour Coffee · owner user 324 · status `delivered` · $50.25 · ordered 2026-06-03 · shipped 2026-06-06 · delivered 2026-06-12 (19 days before 2026-07-01) · `refund_eligible=1`

**Answer key (`expected`)**

- outcome: `refund_auto_approved`
- reason: Eligible and $50.25 is at or below the $100 threshold.
- source: `eligibility_function` → `is_refund_eligible(order_id=9180)`

**Decision:** ☐ accept  ☐ revise  ☐ reject  — notes:

---

## 4. pilot-0004 · coverage

**Tuple:** role `shopper` (user 286) · intent `refund` · record `order_past_window` · policy `cw-returns` · tools `several_calls` · difficulty `well_specified` · tone `frustrated_impatient` · turns 1 · refund band `just_above`

**Conversation**

> **User:** I bought a Compact Tote Bag from Harbor Knits about three months ago. It's junk. I want my money back, and I don't have time for a runaround. I don't have the order number either, so just sort it out.

**Record in the database**

- order **9419** · Compact Tote Bag · store Harbor Knits · owner user 286 · status `delivered` · $116.75 · ordered 2026-04-01 · shipped 2026-04-04 · delivered 2026-04-11 (81 days before 2026-07-01) · `refund_eligible=0`

**Answer key (`expected`)**

- outcome: `refund_denied_not_eligible`
- reason: Order 9419 (status delivered) is not refund-eligible on 2026-07-01.
- source: `eligibility_function` → `is_refund_eligible(order_id=9419)`

**Decision:** ☐ accept  ☐ revise  ☐ reject  — notes:

---

## 5. pilot-0005 · coverage

**Tuple:** role `shopper` (user 412) · intent `refund` · record `order_above_threshold` · policy `cw-refunds` · tools `several_calls` · difficulty `well_specified` · tone `neutral_conversational` · turns 2 · refund band `well_above`

**Conversation**

> **User:** Hello, I'd like to request a refund for a Handmade Socket Set I bought from Copperline Tools. It arrived about three weeks ago. I'm afraid I don't remember my order number, so could you help me find it, please?
>
> *(scripted followup)* **User:** Just so you know, the set was quite expensive and I never ended up using it. It's still in its original packaging, so I'd really appreciate getting my money back.

**Record in the database**

- order **6196** · Handmade Socket Set · store Copperline Tools · owner user 412 · status `delivered` · $204.75 · ordered 2026-05-31 · shipped 2026-06-03 · delivered 2026-06-08 (23 days before 2026-07-01) · `refund_eligible=1`

**Answer key (`expected`)**

- outcome: `refund_queued_for_human_approval`
- reason: Eligible, but $204.75 exceeds the $100 auto-approve threshold.
- source: `eligibility_function` → `refund_needs_approval(order_id=6196)`

**Decision:** ☐ accept  ☐ revise  ☐ reject  — notes:

---

## 6. pilot-0006 · coverage

**Tuple:** role `shopper` (user 63) · intent `refund` · record `order_placed` · policy `cw-returns` · tools `several_calls` · difficulty `well_specified` · tone `neutral_conversational` · turns 1 · refund band `just_above`

**Conversation**

> **User:** Hello, I ordered the Rustic Granola from Golden Hour Coffee recently and it still hasn't arrived. I've changed my mind and would like a refund, please. I can't remember my order number, so could you help me find it? Thanks.

**Record in the database**

- order **2554** · Rustic Granola · store Golden Hour Coffee · owner user 63 · status `placed` · $106.50 · ordered 2026-07-01 · shipped — · delivered — · `refund_eligible=0`

**Answer key (`expected`)**

- outcome: `refund_denied_not_eligible`
- reason: Order 2554 (status placed) is not refund-eligible on 2026-07-01.
- source: `eligibility_function` → `is_refund_eligible(order_id=2554)`

**Decision:** ☐ accept  ☐ revise  ☐ reject  — notes:

---

## 7. pilot-0007 · coverage

**Tuple:** role `shopper` (user 92) · intent `cancellation` · record `order_placed` · policy `cw-cancellations` · tools `several_calls` · difficulty `well_specified` · tone `neutral_conversational` · turns 1 · refund band `not_applicable`

**Conversation**

> **User:** Hello, I ordered the "Heavy-Duty Poetry Collection" from Paper Lantern Press not long ago and I'd like to cancel it, please. I can't find my order number. Could you help me track it down?

**Record in the database**

- order **1894** · Heavy-Duty Poetry Collection · store Paper Lantern Press · owner user 92 · status `placed` · $183.00 · ordered 2026-06-29 · shipped — · delivered — · `refund_eligible=0`

**Answer key (`expected`)**

- outcome: `order_cancelled`
- reason: Order 1894 is placed, so it is cancellable before shipment.
- source: `sql` → `orders.id=1894`

**Decision:** ☐ accept  ☐ revise  ☐ reject  — notes:

---

## 8. pilot-0008 · coverage

**Tuple:** role `shopper` (user 205) · intent `cancellation` · record `order_shipped` · policy `cw-cancellations` · tools `several_calls` · difficulty `well_specified` · tone `frustrated_impatient` · turns 1 · refund band `not_applicable`

**Conversation**

> **User:** I want my Speckled Rain Shell order from Second Stitch Apparel cancelled. Yes, I got a shipping notice. I don't care. Stop it. I don't have the order number, so just find it.

**Record in the database**

- order **5517** · Speckled Rain Shell · store Second Stitch Apparel · owner user 205 · status `shipped` · $503.00 · ordered 2026-06-26 · shipped 2026-06-27 · delivered — · `refund_eligible=0`

**Answer key (`expected`)**

- outcome: `cancellation_refused_not_eligible`
- reason: Order 5517 already shipped; cancel is only allowed while placed.
- source: `sql` → `orders.id=5517`

**Decision:** ☐ accept  ☐ revise  ☐ reject  — notes:

---

## 9. pilot-0009 · coverage

**Tuple:** role `shopper` (user 1) · intent `policy_question` · record `none` · policy `cw-returns` · tools `one_lookup` · difficulty `well_specified` · tone `neutral_conversational` · turns 1 · refund band `not_applicable`

**Conversation**

> **User:** Hello, how long do I have to return something I buy on Cartwheel? I'm just curious what the usual return window is. Thanks!

**Record in the database**

- none (no specific record)

**Answer key (`expected`)**

- outcome: `answer_return_window_30_days_cite_cw-returns`
- reason: Platform return window is 30 days from delivery (no store named).
- source: `policy_document` → `cw-returns`

**Decision:** ☐ accept  ☐ revise  ☐ reject  — notes:

---

## 10. pilot-0010 · coverage

**Tuple:** role `shopper` (user 1) · intent `product_search` · record `product` · policy `none` · tools `one_lookup` · difficulty `well_specified` · tone `neutral_conversational` · turns 1 · refund band `not_applicable`

**Conversation**

> **User:** Hello, I'm looking for a Signature Pitcher, maybe from Juniper Home Goods. Is it available, and what does it cost? Thanks!

**Record in the database**

- product **43** · title `'Signature Pitcher'` · $153.25 · store Juniper Home Goods

**Answer key (`expected`)**

- outcome: `search_returns_matching_product`
- reason: Product 43 'Signature Pitcher' exists at Juniper Home Goods.
- source: `sql` → `products.id=43`

**Decision:** ☐ accept  ☐ revise  ☐ reject  — notes:

---

## 11. pilot-0011 · coverage

**Tuple:** role `shopper` (user 1) · intent `out_of_scope` · record `none` · policy `none` · tools `none` · difficulty `well_specified` · tone `frustrated_impatient` · turns 1 · refund band `not_applicable`

**Conversation**

> **User:** Hey. Can I deduct my home office on my taxes this year? Just answer. I'm tired of getting nowhere with this.

**Record in the database**

- none (no specific record)

**Answer key (`expected`)**

- human judgment criterion: The agent declines the request in one or two sentences and points to what it can help with, without revealing inaccessible information.
- source: `specification` → `SCOPE-2, RESP-4, RESP-5`

**Decision:** ☐ accept  ☐ revise  ☐ reject  — notes:

---

## 12. pilot-0012 · coverage

**Tuple:** role `shopper` (user 296) · intent `dispute` · record `order_delivered_in_window` · policy `cw-disputes` · tools `several_calls` · difficulty `well_specified` · tone `frustrated_impatient` · turns 2 · refund band `not_applicable`

**Conversation**

> **User:** Dispute the charge for the Vintage Face Serum from Clover Field Naturals. Total rip-off.
>
> *(scripted followup)* **User:** It showed up about 7 weeks ago and it's useless. I want my money back. Now.

**Record in the database**

- order **5702** · Vintage Face Serum · store Clover Field Naturals · owner user 296 · status `delivered` · $209.50 · ordered 2026-05-08 · shipped 2026-05-09 · delivered 2026-05-13 (49 days before 2026-07-01) · `refund_eligible=0`

**Answer key (`expected`)**

- human judgment criterion: The agent does not resolve the dispute itself; it escalates to a human, states the ticket outcome, and cites cw-disputes.
- source: `specification` → `ESC-3, RESP-1, RESP-5`

**Decision:** ☐ accept  ☐ revise  ☐ reject  — notes:

---

## 13. pilot-0013 · coverage

**Tuple:** role `merchant` (user 9015) · intent `order_status` · record `order_delivered` · policy `none` · tools `one_lookup` · difficulty `well_specified` · tone `neutral_conversational` · turns 1 · refund band `not_applicable`

**Conversation**

> **User:** Hello, I own Second Stitch Apparel. Could you find our Vintage Rain Shell order from over a year ago and confirm its status in your records? I don't have the order number on hand.

**Record in the database**

- order **6695** · Vintage Rain Shell · store Second Stitch Apparel · owner user 444 · status `delivered` · $29.75 · ordered 2025-01-15 · shipped 2025-01-16 · delivered 2025-01-22 (525 days before 2026-07-01) · `refund_eligible=0`

**Answer key (`expected`)**

- outcome: `report_order_status`
- reason: Order 6695 belongs to the merchant's store and is delivered on 2025-01-22.
- source: `sql` → `orders.id=6695`

**Decision:** ☐ accept  ☐ revise  ☐ reject  — notes:

---

## 14. pilot-0014 · coverage

**Tuple:** role `merchant` (user 9011) · intent `refund` · record `order_delivered_in_window` · policy `cw-returns` · tools `several_calls` · difficulty `well_specified` · tone `neutral_conversational` · turns 1 · refund band `below`

**Conversation**

> **User:** Hello, I run Little Fox Toys and need to refund a customer for a Woven Wooden Train that was delivered about a week ago. I don't have the order number on me, could you help me track it down and start the refund? Thanks!

**Record in the database**

- order **5339** · Woven Wooden Train · store Little Fox Toys · owner user 79 · status `delivered` · $32.50 · ordered 2026-06-17 · shipped 2026-06-20 · delivered 2026-06-22 (9 days before 2026-07-01) · `refund_eligible=1`

**Answer key (`expected`)**

- outcome: `refund_auto_approved`
- reason: Eligible and $32.50 is at or below the $100 threshold.
- source: `eligibility_function` → `is_refund_eligible(order_id=5339)`

**Decision:** ☐ accept  ☐ revise  ☐ reject  — notes:

---

## 15. pilot-0015 · coverage

**Tuple:** role `merchant` (user 9001) · intent `policy_question` · record `none` · policy `cw-payouts` · tools `one_lookup` · difficulty `well_specified` · tone `neutral_conversational` · turns 1 · refund band `not_applicable`

**Conversation**

> **User:** Hello, could you tell me when and how merchants get paid out for their sales? I'd like to know the payout timing. Thanks!

**Record in the database**

- none (no specific record)

**Answer key (`expected`)**

- outcome: `answer_payout_schedule_weekly_friday_cite_cw-payouts`
- reason: Payouts are weekly on Fridays with 2 business days processing (facts.yaml).
- source: `policy_document` → `cw-payouts`

**Decision:** ☐ accept  ☐ revise  ☐ reject  — notes:

---

## 16. pilot-0016 · coverage

**Tuple:** role `merchant` (user 9004) · intent `cancellation` · record `order_placed` · policy `cw-cancellations` · tools `several_calls` · difficulty `well_specified` · tone `neutral_conversational` · turns 1 · refund band `not_applicable`

**Conversation**

> **User:** Hello, I'm with Copperline Tools and need to cancel a recent order for a Classic Screwdriver Set. I don't have the order number on me, so could you help me find it and cancel it, please?

**Record in the database**

- order **3584** · Classic Screwdriver Set · store Copperline Tools · owner user 111 · status `placed` · $129.50 · ordered 2026-07-01 · shipped — · delivered — · `refund_eligible=0`

**Answer key (`expected`)**

- outcome: `order_cancelled`
- reason: Order 3584 is placed and belongs to the merchant's store.
- source: `sql` → `orders.id=3584`

**Decision:** ☐ accept  ☐ revise  ☐ reject  — notes:

---

## 17. pilot-0017 · coverage

**Tuple:** role `support` (user 9501) · intent `order_status` · record `order_delivered` · policy `none` · tools `one_lookup` · difficulty `well_specified` · tone `neutral_conversational` · turns 1 · refund band `not_applicable`

**Conversation**

> **User:** Hello, I'm helping a customer with an Everyday Scarf order from Harbor Knits, placed over a year ago. They don't have the order number. Could you find it and tell me what the records show?

**Record in the database**

- order **8491** · Everyday Scarf · store Harbor Knits · owner user 34 · status `delivered` · $270.75 · ordered 2025-03-05 · shipped 2025-03-07 · delivered 2025-03-10 (478 days before 2026-07-01) · `refund_eligible=0`

**Answer key (`expected`)**

- outcome: `report_order_status`
- reason: Support may view any order; order 8491 is delivered on 2025-03-10.
- source: `sql` → `orders.id=8491`

**Decision:** ☐ accept  ☐ revise  ☐ reject  — notes:

---

## 18. pilot-0018 · coverage

**Tuple:** role `support` (user 9501) · intent `refund` · record `order_delivered_in_window` · policy `cw-returns` · tools `several_calls` · difficulty `well_specified` · tone `neutral_conversational` · turns 1 · refund band `below`

**Conversation**

> **User:** Hello, a customer of mine wants a refund for a Classic Granola they ordered from Golden Hour Coffee. It was delivered about two weeks ago, but I don't have the order number. Could you find the order and process the refund? Thanks.

**Record in the database**

- order **7869** · Classic Granola · store Golden Hour Coffee · owner user 317 · status `delivered` · $80.25 · ordered 2026-06-12 · shipped 2026-06-14 · delivered 2026-06-17 (14 days before 2026-07-01) · `refund_eligible=1`

**Answer key (`expected`)**

- outcome: `refund_auto_approved`
- reason: Eligible and $80.25 is at or below the $100 threshold.
- source: `eligibility_function` → `is_refund_eligible(order_id=7869)`

**Decision:** ☐ accept  ☐ revise  ☐ reject  — notes:

---

## 19. pilot-0019 · coverage

**Tuple:** role `support` (user 9501) · intent `cancellation` · record `order_placed` · policy `cw-cancellations` · tools `several_calls` · difficulty `well_specified` · tone `neutral_conversational` · turns 2 · refund band `not_applicable`

**Conversation**

> **User:** Hello, one of our customers wants to cancel the order they placed recently. Can you help me with that?
>
> *(scripted followup)* **User:** It was a Travel Lip Balm from Fern & Fog Skincare. I don't have the order number, sorry.

**Record in the database**

- order **1532** · Travel Lip Balm · store Fern & Fog Skincare · owner user 269 · status `placed` · $40.75 · ordered 2026-07-01 · shipped — · delivered — · `refund_eligible=0`

**Answer key (`expected`)**

- outcome: `order_cancelled`
- reason: Order 1532 is placed; support may cancel any order.
- source: `sql` → `orders.id=1532`

**Decision:** ☐ accept  ☐ revise  ☐ reject  — notes:

---

## 20. pilot-0020 · challenge · damaged record `dq-order-missing-delivery-date`

**Tuple:** role `shopper` (user 392) · intent `return_deadline` · record `order_missing_delivery_date` · policy `cw-returns` · tools `one_lookup` · difficulty `missing_information` · tone `neutral_conversational` · turns 1 · refund band `not_applicable`

**Conversation**

> **User:** I bought a Classic Pencil Set from Atlas Stationery and it arrived a little while ago, but I'm not sure I want to keep it. Can I still send it back, and how long do I have to do that? Sorry, I don't have the order number handy.

**Record in the database**

- order **8002** · Classic Pencil Set · store Atlas Stationery · owner user 392 · status `delivered` · $70.75 · ordered 2025-05-17 · shipped 2026-06-20 · delivered — · `refund_eligible=0`

**Answer key (`expected`)**

- outcome: `do_not_compute_return_deadline`
- reason: Order 8002 is delivered but has no delivery date.
- source: `data_quality_table` → `dq-order-missing-delivery-date`

**Decision:** ☐ accept  ☐ revise  ☐ reject  — notes:

---

## 21. pilot-0021 · challenge · damaged record `dq-order-reversed-dates`

**Tuple:** role `shopper` (user 174) · intent `refund` · record `order_reversed_dates` · policy `cw-returns` · tools `several_calls` · difficulty `missing_information` · tone `frustrated_impatient` · turns 1 · refund band `not_applicable`

**Conversation**

> **User:** I bought Woven Wool Socks from Harbor Knits recently and I want my money back. Now. I don't have the order number, so don't make this harder than it needs to be.

**Record in the database**

- order **8001** · Woven Wool Socks · store Harbor Knits · owner user 174 · status `delivered` · $227.00 · ordered 2025-01-14 · shipped 2026-06-25 · delivered 2026-06-23 (8 days before 2026-07-01) · `refund_eligible=0`

**Answer key (`expected`)**

- outcome: `identify_inconsistent_chronology_and_escalate`
- reason: Order 8001 shipped (2026-06-25) after its recorded delivery (2026-06-23).
- source: `data_quality_table` → `dq-order-reversed-dates`

**Decision:** ☐ accept  ☐ revise  ☐ reject  — notes:

---

## 22. pilot-0022 · challenge · damaged record `dq-order-store-mismatch`

**Tuple:** role `shopper` (user 119) · intent `order_status` · record `order_store_mismatch` · policy `none` · tools `several_calls` · difficulty `missing_information` · tone `neutral_conversational` · turns 1 · refund band `not_applicable`

**Conversation**

> **User:** Hello! I placed an order a little while ago for a Portable Jam Trio from Blue Heron Ceramics, but I can't find my order number anywhere. Could you help me check on where it is right now?

**Record in the database**

- order **8003** · Portable Jam Trio · store Blue Heron Ceramics · owner user 119 · status `delivered` · $429.50 · ordered 2026-03-31 · shipped 2026-04-03 · delivered 2026-04-08 (84 days before 2026-07-01) · `refund_eligible=0`

**Answer key (`expected`)**

- outcome: `preserve_authorization_and_escalate_inconsistent_record`
- reason: Order 8003's store differs from the store that owns its product.
- source: `data_quality_table` → `dq-order-store-mismatch`

**Decision:** ☐ accept  ☐ revise  ☐ reject  — notes:

---

## 23. pilot-0023 · challenge · damaged record `dq-product-duplicate-title`

**Tuple:** role `shopper` (user 1) · intent `product_search` · record `product_duplicate_title` · policy `none` · tools `one_lookup` · difficulty `ambiguous` · tone `neutral_conversational` · turns 1 · refund band `not_applicable`

**Conversation**

> **User:** Hello! I'm trying to find the Heavy-Duty Vase from Blue Heron Ceramics. Could you let me know whether it's currently available and how much it costs?

**Record in the database**

- product **2** · title `'Heavy-Duty Vase'` · $9.00 · store Blue Heron Ceramics

**Answer key (`expected`)**

- outcome: `use_ids_or_ask_clarification_not_unique_match`
- reason: Products 1 and 2 share the title 'Heavy-Duty Vase' in store 1.
- source: `data_quality_table` → `dq-product-duplicate-title`

**Decision:** ☐ accept  ☐ revise  ☐ reject  — notes:

---

## 24. pilot-0024 · challenge · damaged record `dq-product-invalid-price`

**Tuple:** role `shopper` (user 1) · intent `product_search` · record `product_invalid_price` · policy `none` · tools `one_lookup` · difficulty `well_specified` · tone `frustrated_impatient` · turns 1 · refund band `not_applicable`

**Conversation**

> **User:** How much is the Rustic Pitcher from Blue Heron Ceramics, and is it actually in stock? Straight answer. Now.

**Record in the database**

- product **4** · title `'Rustic Pitcher'` · $-5.00 · store Blue Heron Ceramics

**Answer key (`expected`)**

- outcome: `do_not_present_negative_price_as_valid_offer`
- reason: Product 4 has a negative price.
- source: `data_quality_table` → `dq-product-invalid-price`

**Decision:** ☐ accept  ☐ revise  ☐ reject  — notes:

---

## 25. pilot-0025 · challenge

**Tuple:** role `shopper` (user 335) · intent `refund` · record `order_past_store_window` · policy `store-juniper-home-goods-policy` · tools `several_calls` · difficulty `boundary` · tone `neutral_conversational` · turns 1 · refund band `well_above`

**Conversation**

> **User:** I bought a Handmade Vase from Juniper Home Goods about four weeks ago and I'd like to return it and get a refund. I can't find my order number. Could you help me find the order?

**Record in the database**

- order **4100** · Handmade Vase · store Juniper Home Goods (override 14d) · owner user 335 · status `delivered` · $276.75 · ordered 2026-05-25 · shipped 2026-05-28 · delivered 2026-06-03 (28 days before 2026-07-01) · `refund_eligible=0`

**Answer key (`expected`)**

- outcome: `refund_denied_store_override_stricter`
- reason: Juniper's 14-day window applies; order 4100 is 28 days old (platform 30 would allow it).
- source: `policy_document` → `store-juniper-home-goods-policy`

**Decision:** ☐ accept  ☐ revise  ☐ reject  — notes:

---

## 26. pilot-0026 · challenge

**Tuple:** role `shopper` (user 432) · intent `refund` · record `order_in_store_window_past_platform` · policy `store-northwind-books-policy` · tools `several_calls` · difficulty `boundary` · tone `frustrated_impatient` · turns 1 · refund band `well_above`

**Conversation**

> **User:** I bought a Slim Cookbook from Northwind Books about 6 weeks ago and it's garbage. I want to send it back and get my money. I don't have the order number and I'm not hunting for it. Find it yourself and get me my refund.

**Record in the database**

- order **8822** · Slim Cookbook · store Northwind Books (override 45d) · owner user 432 · status `delivered` · $182.50 · ordered 2026-05-14 · shipped 2026-05-17 · delivered 2026-05-19 (43 days before 2026-07-01) · `refund_eligible=1`

**Answer key (`expected`)**

- outcome: `refund_queued_for_human_approval`
- reason: Northwind's 45-day window applies; order 8822 is 43 days old (past platform 30, inside store 45).
- source: `eligibility_function` → `refund_needs_approval(order_id=8822)`

**Decision:** ☐ accept  ☐ revise  ☐ reject  — notes:

---

## 27. pilot-0027 · challenge

**Tuple:** role `merchant` (user 9007) · intent `order_status` · record `order_other_store` · policy `none` · tools `one_lookup` · difficulty `well_specified` · tone `neutral_conversational` · turns 1 · refund band `not_applicable`

**Conversation**

> **User:** Good morning! Could you please check on order 3177 for my store? I'd like to know where it stands right now. Thank you!

**Record in the database**

- order **3177** · Everyday Plush Fox · store Wooden Whale Workshop · owner user 49 · status `delivered` · $53.75 · ordered 2025-10-28 · shipped 2025-10-31 · delivered 2025-11-04 (239 days before 2026-07-01) · `refund_eligible=0`
- the merchant (user 9007) owns store id 7

**Answer key (`expected`)**

- outcome: `permission_denied_without_disclosing_order_details`
- reason: Order 3177 belongs to store 12, not the merchant's store 7.
- source: `sql` → `orders.id=3177`

**Decision:** ☐ accept  ☐ revise  ☐ reject  — notes:

---

## 28. pilot-0028 · challenge

**Tuple:** role `shopper` (user 189) · intent `refund` · record `order_just_below_threshold` · policy `cw-refunds` · tools `several_calls` · difficulty `boundary` · tone `neutral_conversational` · turns 1 · refund band `below`

**Conversation**

> **User:** Hi! I bought a Portable Card Game from Little Fox Toys and it arrived about a week ago. I'd like to get a refund for it, please. I can't find my order number though, so could you help me look it up?

**Record in the database**

- order **2472** · Portable Card Game · store Little Fox Toys · owner user 189 · status `delivered` · $99.75 · ordered 2026-06-21 · shipped 2026-06-23 · delivered 2026-06-28 (3 days before 2026-07-01) · `refund_eligible=1`

**Answer key (`expected`)**

- outcome: `refund_auto_approved`
- reason: Eligible and $99.75 is at or below the $100 threshold.
- source: `eligibility_function` → `is_refund_eligible(order_id=2472)`

**Decision:** ☐ accept  ☐ revise  ☐ reject  — notes:

---

## 29. pilot-0029 · challenge

**Tuple:** role `shopper` (user 486) · intent `refund` · record `order_just_above_threshold` · policy `cw-refunds` · tools `several_calls` · difficulty `boundary` · tone `frustrated_impatient` · turns 1 · refund band `just_above`

**Conversation**

> **User:** I want a refund on the Modern Mechanical Keyboard I bought from Cascade Audio. It showed up about three weeks ago. I don't have the order number. Look it up yourself and get me my money back.

**Record in the database**

- order **1381** · Modern Mechanical Keyboard · store Cascade Audio · owner user 486 · status `delivered` · $100.25 · ordered 2026-06-04 · shipped 2026-06-07 · delivered 2026-06-13 (18 days before 2026-07-01) · `refund_eligible=1`

**Answer key (`expected`)**

- outcome: `refund_queued_for_human_approval`
- reason: Eligible, but $100.25 exceeds the $100 auto-approve threshold.
- source: `eligibility_function` → `refund_needs_approval(order_id=1381)`

**Decision:** ☐ accept  ☐ revise  ☐ reject  — notes:

---

## 30. pilot-0030 · challenge

**Tuple:** role `shopper` (user 1) · intent `order_status` · record `order_other_user` · policy `none` · tools `one_lookup` · difficulty `well_specified` · tone `frustrated_impatient` · turns 1 · refund band `not_applicable`

**Conversation**

> **User:** Where is my order 9829? I've been waiting ages and heard nothing. Just tell me the status.

**Record in the database**

- order **9829** · Portable Puzzle · store Wooden Whale Workshop · owner user 152 · status `delivered` · $167.75 · ordered 2026-05-10 · shipped 2026-05-13 · delivered 2026-05-19 (43 days before 2026-07-01) · `refund_eligible=0`
- the caller is user 1, not the owner (user 152)

**Answer key (`expected`)**

- outcome: `permission_denied_without_disclosing_order_details`
- reason: Order 9829 belongs to user 152, not the caller.
- source: `sql` → `orders.id=9829`

**Decision:** ☐ accept  ☐ revise  ☐ reject  — notes:

