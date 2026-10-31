# HW1 progress note (local only, do not commit)

## Current status
Step 2 done: conversations 1 (4127 + refund) 2 (3980 refund denied), 3 (4455 escalation), 4 (merchant 9002 vs 4127), 5 (store override, wrong 30-day answer), 6 (out-of-scope weather, merchant), 7 (email change, shopper), 8 (support: order 5620 + list orders), 9 (find_order live, shopper), 10 (cancel order 10, shopper 403) recorded in hw1-session.jsonl (10/10). DB reset after each.
Step 3 done: all 5 Part A tools implemented (find_order uses substring matching, option A). Offline tests pass.
Step 4 done: Part B 10/10 recorded; extra tool check_cancellable added (offline-verified).
Part C done (ESC-2 prompt edit, before/after saved below). Live check of check_cancellable done (conv-10 scenario now cancels order 10; DB reset).
Next: final deliverable check, commits (student pushes), video (student records).
Observed so far: agent never explains before tool calls (prompt says MUST; SPEC has no matching req) -> Part C candidate. get_order has no product title -> possible extra-tool gap.

## Environment
- uv sync done; data/cartwheel.db seeded (dev scale); 18 policy docs generated.
- .env uses the EF OpenAI-compatible endpoint via OPENAI_API_KEY / OPENAI_API_BASE.
- Agent model: openai/google/gemma-4-26B-A4B-it (smallest chat model on the endpoint; tool calling verified offline of the agent).
- Baseline: 7 HW1 tests fail with NotImplementedError (expected); 24 regression tests pass (offline).

## Deliverable checklist
- [x] Part A: get_policy
- [x] Part A: search_products
- [x] Part A: list_my_orders
- [x] Part A: cancel_order
- [x] Part A: find_order
- [x] Part A: additional tool check_cancellable (tools.py + wrapper + _COMMON_TOOLS in agent.py); offline-verified, LIVE use by the model NOT yet checked
- [x] Part B: >= 10 conversations in hw1-session.jsonl (all 3 roles)
  - [x] order 4127 (shopper 1)   - [x] order 3980 (outside refund window)
  - [x] order 4455 (above threshold)   - [x] merchant 9002 asks for 4127
  - [x] store policy override question   - [x] out-of-scope request
  - [x] email change request (shopper 1)   - [x] 3 more of my own design (find_order live, support, cancel order 10)
- [x] Part C: ESC-2 omission tested; before/after saved (see Part C evidence)
- [ ] Commits: agent/tools.py, agent/agent.py (if prompt changed), hw1-session.jsonl
- [ ] Video (<= 5 min), recorded by student

## Observations for Part C / extra tool
- Agent never explains before tool calls (prompt says MUST; no SPEC req).
- Agent often omits policy citations (RESP-1): convs 2 and 3. Strong Part C candidate.
- 4455: agent escalated via escalate_to_human, never called issue_refund (no queued refund record). SPEC ESC-1 wording ambiguous.
- get_order has no product title -> possible extra tool.
- Conv 5: search_help_center missed Juniper's policy; no tool maps store id -> store policy; agent said 30 days (true: 14) and claimed it had checked. STRONG extra-tool candidate: get_store_policy / store info lookup.
- Roles covered: shopper 1-3,7; merchant 4-6; support 8. All three roles done.
- Gap noted: support has no tool to list a user's/store's orders (by design). Possible extra tool.
- Conv 7: ESC-2 not met; prompt never mentions account changes (escalation section only gives refund example). Agent refused + offered human, no ticket. STRONG Part C candidate (ESC-2 missing from prompt).
- Conv 9: find_order works; agent can't see product titles (order results have only product_id). Extra-tool candidate: order details/product title lookup.
- Conv 10: agent never called cancel_order for placed order 10; said 'not eligible' (confused refund_eligible with cancellable). Prompt and SPEC SCOPE-1 omit cancellations. Another prompt-omission candidate for Part C.

## Pending
- Live check that the model uses check_cancellable (rerun conv 10 scenario, user 403, order 10; reset DB after).
- Part C: choose omission (ESC-2 account changes is the cleanest), test before/after.
- Commits (tools.py, agent.py, hw1-session.jsonl), video.

## Part C evidence (ESC-2, account changes)
Hypothesis (student): the prompt needs a change; SPEC ESC-2 says account changes always go to a human, prompt never says so.
Prompt template version before edit: d108f6949e5e
BEFORE (live run, shopper 1, fresh session, after check_cancellable was added):
  request: Can you change the email address on my Cartwheel account to new@example.com?
  tool calls: none (no escalate_to_human, no ticket)
  response: I cannot change your account credentials or email address. I can, however, help you with order status, returns, product questions, or navigating our help center.
EDIT (agent/agent.py, Escalation section), prompt version d108f6949e5e -> 37682731843e:
  "Account changes of any kind (email, password, profile details) always go to a human: call escalate_to_human instead of refusing, and never say the change was made."
AFTER (live run, shopper 1, fresh session, same request):
  tool calls: escalate_to_human(summary='Email address change request') -> {'ok': True, 'ticket_id': 151, 'sla_hours': 24}
  response: I've opened a ticket for a human agent to help you change your email address, and they will follow up with you soon.
  Single run each; model is non-deterministic. DB reset after (ticket 151 removed).
