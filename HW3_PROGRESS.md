# HW3 progress note

## HANDOFF (read first if you are a new Claude session)
Branch `hw3-wip`. Student is driving: one step at a time, wait for their "go" before running a command, changing a file or generating anything (reading to prepare is fine). Follow AGENTS.md, homework/module-1/hw3.md and scenarios/skill/SKILL.md. Leave assessments, video and review decisions to the student.
State: pilot done (pilot_review.jsonl written, 7 valid confirmed failures). Part C generation + critic pass DONE for all 250: work files are in `hw3-wip/` (copied from a session scratchpad):
- `plan_final.json` (F001..F250 plans incl. `expected`; built by `plan_final.py`), `build_gen_prompts.py` -> `gen_prompts/`, haiku generator outputs `gen_out/Fxxx.json`, sonnet critic prompts `critic_prompts/` -> final messages `critic_out/Fxxx.json` ({opening_message, followups, changed, note}).
- Screen of critic_out: all 250 parse, follow-up counts match turn_count, 0 duplicates, 8 greeting openings, F238 "refund threshold" is an acceptable policy question.
UPDATE 2026-11-11: support_scenarios.jsonl (250, validated --final), support_review.jsonl (15: 13 accept, 2 revise = support-0011 expected.reason, support-0051 expected.reason), monitoring_scenarios.jsonl (50, validated) DONE and committed. REMAINING: Part D reseed + final run + `jq` check 250 completed; Part E smoke report + trace export; student: video, assessments. (Older NEXT list below is partly done.)
OLD NEXT (needs student "go"): assemble `scenarios/support_scenarios.jsonl` (ids support-0001..0250 in plan order; fields id, scenario_group, data_quality_case_id, tuple, opening_message, followups, expected; look at scenarios/pilot_scenarios.jsonl and hw3-wip/assemble_pilot.py for the format) -> `uv run python -m scenarios.validate scenarios/support_scenarios.jsonl --final` -> 15-scenario review sheet for the student (they write scenarios/support_review.jsonl) -> 50 monitoring scenarios -> reseed (`uv run python -m seed.generate`), start server (`uv run uvicorn server.app:app --port 8010`), final run -> Part E (smoke report, trace export).
Env: .env is NOT committed; needs Langfuse vars (local stack: observability/docker-compose.yml) and CARTWHEEL_MODEL=openai/google/gemma-4-26B-A4B-it. Concurrent subagent cap was 20 (waves of 20). hw3-wip/ is scaffolding, not a deliverable (remove before final submission if desired).

(Rest of this note was written earlier; "local only, do not commit" there is superseded by this handoff.)

## Current status
Steps 1-4 done: progress note; read AGENTS.md, hw3.md, SPEC.md, scenarios/skill/SKILL.md (homework/module-1/AGENTS.md does not exist; not needed); preparation checks; smoke trace verified.
Preparation: seed reset run (as-of 2026-07-01, pinned orders #4127/#3980/#4455). Langfuse local stack up (6 containers). Cartwheel server on :8010 started by me as a background task (dies with the session; sessions are in-memory, so re-open one after any restart).
Smoke trace (local Langfuse, project cartwheel-dev): 5d63249c10d767c1576cbe5f5449b27e, shopper 1, "What is the status of order 3980?", scenario_id smoke-check-001 (not a support-NNNN id). Verified: conversation (root span Input/Output), model name, get_order tool call+result, cartwheel.scenario_id. Reply lives on the root span (cartwheel.session_message); the two openai.response generations show Input but empty Output.
Token usage: NOT recorded (0 input/output/cost on both generations; no token attributes). Known limitation; smoke report tokens/cost will likely be zero. Cause not diagnosed (gateway or instrumentation).
Part A DONE: plan approved (see "Approved dimension plan").
Part B generation DONE, runner NOT started: scenarios/pilot_scenarios.jsonl written (30 = 19 coverage + 11 challenge; ids pilot-0001..0030) and validated OK (`scenarios.validate`: 30 records, 30 unique ids, 5 dq). Pipeline: scratchpad plan_pilot.py (seeded SQL tuple sampling, oracle cross-check) -> 30 generator subagents (never saw expected) -> 30 critic subagents -> assemble_pilot.py. Scratchpad has plan_pilot.json (keys C02..H11 -> pilot ids), final_messages.json.
Plan deviations (told to student): dropped C01 to stay at 30; threshold pair H09 ($99.75 o2472, auto-approved) + H10 ($100.25 o1381, queued) because no order totals exactly $100.00; H01-H03 regenerated with true product titles after writers invented items; critic overrode H01/H06 template phrasing by hand.
Known weakness: 16/30 openings start "Hello" (critic replaced "Hi there"). Only 2 tones. 5/30 multi-turn.
Untracked, do NOT commit: .sessions.db-shm/-wal (server), HW3_PROGRESS.md.
Conversation sample REVIEWED by student: only change requested was pilot-0002 (asked status of an item it said had arrived) -> rewritten; I also fixed the same flaw in pilot-0013/0017 (student approved). File re-validated.
PILOT RUN DONE (after seed reset): `uv run python -m scenarios.runner scenarios/pilot_scenarios.jsonl --model openai/google/gemma-4-26B-A4B-it --output scenarios/pilot-results.jsonl` -> 30/30 completed, ~78 s total, 35 traces (5 two-turn). scenarios/pilot-results.jsonl EXISTS.
Mechanical observations (NOT judgments; student decides failures): only 2 refunds issued (queued: orders 6196, 8822), 0 cancellations; order status counts unchanged from seed (403 cancelled/573 refunded/35 placed). In 8 action scenarios (pilot-0003,0007,0014,0016?,0018,0019,0028,0029) the agent stopped to ask for confirmation/reason, so scripted single-turn users could not authorize the action; pilot-0028 reply ends mid-thought ("I'll look up the order details now."). No escalate_to_human call anywhere, incl. pilot-0012 (dispute), 0021 (reversed dates), 0022 (store mismatch). Token usage still 0.
Review aid: HW3_PILOT_RESULTS.md (local only, do not commit; agent replies + tool calls + DB effects per scenario, from render_results.py). HW3_PILOT_REVIEW.md = scenario review sheet (also local only).
Candidates I suggested the student look at (NOT decisions): 0012 (claims escalation, no escalate_to_human call), 0021, 0022, 0020 (dq data issues not stated/escalated), 0004 (cites cw-disputes 60d for a refund), 0005 (refund without get_order, prompt rule), 0025 (denial w/o Juniper 14d reason), 0028 (reply ends mid-thought, no refund), 0013 (false "oldest order is Jan 2026"; find_order caps at 5). Validity questions: 0002 (system prompt has NO current date, only role/user/store), 0003/0007/0029/0014/0018 (asks confirmation/reason; scripted user can't answer), 0013/0017 (target order outside find_order's 5 results).
Student reviewed 11 cases (0012,0021,0022,0020,0004,0025,0028,0005,0013,0007,0029) and said they "look odd"; formal verdicts NOT yet given. Scaffold created: HW3_PILOT_REVIEW_FORM.md (local only; verdict fields = TODO, evidence drafted from tool results). When student fills it in, convert to scenarios/pilot_review.jsonl verbatim (do not change verdicts) and check `jq -s '[.[]|select(.scenario_valid and .confirmed_failure)]|length'` >= 5.
PILOT VERDICTS GIVEN IN CHAT (student; not yet written to pilot_review.jsonl): 0004, 0012, 0020, 0021, 0028 = valid + confirmed failure. 0013 and 0022 = scenario_valid false (failure assumed false, to confirm). find_order cap of 5 newest is per SPEC (no date cutoff); get_order works. Still open: 0025, 0005, 0007, 0029 (need >= 3 more for 10 reviewed).
PART C PLAN APPROVED by student: coverage 175 (status 35, refund 35, cancel 25, policy 25, search 25, dispute 15, out_of_scope 15), challenge 75 (30 dq = 5 per record + ~45 other); roles ~60/25/15; tones 50/50; ~30% multi-turn; <15% "Hello" openings; actions pre-authorized with reason; find_order target must be in first 5 matches (oracle); cancels capped ~30 (35 placed orders). Generators on haiku, critics on sonnet (approved). dq-order-store-mismatch (8003): option (a) = permission/authorization framing (merchant of store 1 or 14, owner, others; no leaking, no assumed ownership). Ids support-0001..0250. Waiting for student "go" to start planner.
PART C STEP 1 DONE (go given): scratchpad plan_final.py -> plan_final.json (250 tuples, keys F001..F250; 175 coverage/75 challenge; 5 per dq; distinct orders for all non-dq; 55 find-by-description scenarios oracle-checked reachable within find_order's top 5). NOT generated yet: waiting for student to see the plan summary and say go for subagent generation (haiku generators, sonnet critics).
PART C STEP 2 DONE (student said go): 250 haiku generator outputs in scratchpad gen_out/F001..F250.json (all parse, turn counts match plan; 8/250 greeting openings; 1 possible leak F238 'threshold'). Concurrent-subagent cap is 20, so waves of 20. STEP 3 (sonnet critics) in progress: critic_prompts/ -> critic_out/. Then assemble support-0001..0250 (keep plan order F001..F250), validate --final, build review sheet for student (15 scenarios), then monitoring 50.
Next: STUDENT writes scenarios/pilot_review.jsonl (>= 10 reviewed; fields scenario_id, scenario_valid, confirmed_failure, evidence, scenario_change|null; >= 5 confirmed failures). Then Part C. If < 5 failures: add 20 challenge scenarios, reseed, rerun (or lower-capability model from same provider).

## Environment
- Student: AI engineer + software engineer. Skip programming basics; explain eval concepts briefly, infra as a checklist.
- CARTWHEEL_MODEL=openai/google/gemma-4-26B-A4B-it, confirmed by student. Same string in every `--model` flag.
- HW2 completed by student (do NOT apply hw2-reference.patch).
- .env Langfuse vars had pointed at Langfuse Cloud (us.cloud.langfuse.com, cloud keys); student switched back to local (http://localhost:3000, pk/sk-lf-cartwheel-dev). Local login: student@example.com (password in a comment in observability/docker-compose.yml); demo@langfuse.com has no org, so it shows no orgs. Never print key values.
- Local Langfuse had 9 traces from HW2 before the smoke trace.

## Damaged records (data_quality_cases)
- dq-order-missing-delivery-date: order 8002
- dq-order-reversed-dates: order 8001
- dq-order-store-mismatch: order 8003
- dq-product-duplicate-title: product 2 (dup of product 1)
- dq-product-invalid-price: product 4 (negative)
- dq-product-missing-title: product 3 (empty)
Need 5 challenge scenarios per case (30 total) in the final set.

## Approved dimension plan (REVIEW POINT 1 passed; approved by student)
Student's own: intent, tone, role, one vs multi turn. Added from SPEC/data, then student decided:
- role: shopper | merchant | support (AUTH-1). Enum enforced.
- intent: order status, refund, cancellation, policy question, product search, dispute, out of scope (free string in validator).
- record_state: order in window / past window / above $100 / placed / shipped / delivered / refunded / cancelled; product; store policy page; none. Data skew: 8915 delivered, 573 refunded, 403 cancelled, only 74 shipped and 35 placed, so cancellation/shipped must be oversampled deliberately.
- applicable_policy: platform default | store override (stricter or looser) | none. Six store policy docs; Juniper = 14 days.
- tools_needed: none | one lookup | several calls.
- difficulty: well specified | ambiguous | missing information | boundary.
- user_style: STUDENT CHOSE 2 tones only: neutral_conversational (polite) and frustrated_impatient (angry). Validator allows a subset of its 8-value enum.
- turn_count: 1 + len(followups), validator-checked. Mix left to sampling (student decision); scripted followups must not assume the agent's reply.
- ADDED by student: refund_amount_band relative to the $100 auto-approve threshold (below | at | just above | well above) to test threshold behavior. Extra tuple fields are accepted by the validator (only missing required fields are rejected).
Validator facts: required tuple fields = role, intent, record_state, applicable_policy, tools_needed, turn_count, difficulty, user_style. DQ scenarios must be challenge + objective + source data_quality_table with the case id.

## Deliverable checklist
- [x] Part A: dimension plan approved (REVIEW POINT 1 done)
- [x] scenarios/pilot_scenarios.jsonl (30; validated; student reviewed sample)
- [x] scenarios/pilot-results.jsonl (30/30 completed; still pending: student pilot review)
- [x] scenarios/pilot_review.jsonl (REVIEW POINT 2 done: 11 reviewed, 7 valid confirmed failures; written from student verdicts; 0007/0029/0013/0022 invalid, need replacement scenarios in Part C)
- [ ] scenarios/support_scenarios.jsonl (175 coverage + 75 challenge, 5 per damaged record, new ids)
- [ ] scenarios/support_review.jsonl (REVIEW POINT 3: student, 15 scenarios)
- [ ] scenarios/monitoring_scenarios.jsonl (50; both groups, all roles)
- [ ] scenarios/final-results.jsonl (250 completed)
- [ ] reports/smoke-output.txt
- [ ] traces/support_traces.json (250 ids; 3 traces opened by student)
- [ ] Video (<= 5 min), by student
- [ ] Assessments, by student

## Files to commit
- scenarios/pilot_scenarios.jsonl
- scenarios/pilot-results.jsonl
- scenarios/pilot_review.jsonl
- scenarios/support_scenarios.jsonl
- scenarios/support_review.jsonl
- scenarios/monitoring_scenarios.jsonl
- scenarios/final-results.jsonl
- reports/smoke-output.txt
- traces/support_traces.json

## Observations
(none yet)
