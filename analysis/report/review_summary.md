# HW4 review summary

## 1. Sample size and composition

105 distinct traces reviewed, drawn from the 325 traces of the 250 final HW3 scenarios (frame: `scenarios/support_scenarios.jsonl`; 9 trace(s) from 6 excluded session(s); seed 7). Selection never used a model prediction of failure.

| Batch | n | Method | Roles |
|---|---|---|---|
| 1 | 30 | 15 uniform random + 15 cluster representatives (k-means on trace features) | merchant 6, shopper 20, support 4 |
| 2 | 30 | Stratified on `role`, dimension chosen before looking at outcomes | merchant 10, shopper 10, support 10 |
| 3 | 30 | Depth-search picks (positives and close negatives); 5 added by accepting search suggestions | merchant 5, shopper 25 |
| 4 | 15 | Uniform random from sessions with no turn already in the sample (stability check) | merchant 5, shopper 9, support 1 |

Active annotations at the time of writing: 58 "no failure observed" marks and 28 notes by the student; 15 added by Claude under delegation (14 notes, 1 "no failure"); 5 from accepted suggestions. See section 7.

## 2. Failure modes and sample fractions by batch

Failures present / traces in the batch. Batch 3 is a biased depth search and must never be used for prevalence; batch 2 is stratified by role; batch 1 mixes uniform picks with cluster representatives. Only the "Uniform draws" column, which counts the 30 uniform random picks (15 in batch 1, 15 in batch 4), is a prevalence estimate, and with n = 30 it is rough.

| Mode | Evaluator | B1 | B2 | B3 | B4 | Uniform draws (n=30) | All 105 |
|---|---|---|---|---|---|---|---|
| `unbacked_action_claim` | LLM judge | 0/30 | 1/30 | 8/30 | 0/15 | 0/30 | 9/105 |
| `dispute_not_escalated` | LLM judge | 0/30 | 1/30 | 2/30 | 0/15 | 0/30 | 3/105 |
| `search_products_invalid_args` | code check | 3/30 | 4/30 | 3/30 | 1/15 | 3/30 | 11/105 |
| `inconsistent_data_not_stated` | LLM judge | 2/30 | 2/30 | 6/30 | 0/15 | 1/30 | 10/105 |
| `repeated_failed_tool_call` | code check | 0/30 | 1/30 | 2/30 | 0/15 | 0/30 | 3/105 |
| `tool_error_misreported` | LLM judge | 0/30 | 1/30 | 2/30 | 0/15 | 0/30 | 3/105 |
| `refund_not_submitted_after_request` | code check | 2/30 | 2/30 | 0/30 | 2/15 | 4/30 | 6/105 |

Labels live in `analysis/state/labels/<mode>.jsonl` and as Langfuse scores (`hw4-<trace_id>-<mode>`, 1 = failure present).

## 3. New modes in the final 15 traces

**1.** Batch 4 produced one new consequential mode, `refund_not_submitted_after_request` (`3b6fa049`, `4dd02d06`). Of the 15 traces, 11 are marked "no failure observed", one more (`b1aea5f9`, the `query='*'` pattern) fits an existing mode after the student converted it, and `76cc3a60` has a note about an unnecessary argument that is not a failure.

<!-- student:stability -->
-> New mode was found ("refund_not_submitted_after_request")
-> further notes were added to existing modes
-> taxonomy is now stable
<!-- /student:stability -->

## 4. One taxonomy revision

<!-- student:revision -->
-> See traces below
-> The first mode was "store filter is an ID not name"
-> Second mode was search_products with query '*' and a valid store
-> The solution was to change the tool contract to be more clear and what it accepts, it fixed both
-> We merged both modes into search_products_invalid_args
-> Traces:  15ee0490, d2cf1530, 116b1bbc, ecd4b0d2, 2cf7b873, 868ec588, 20f03214
-> Four more '*' traces were found later (0269ec43, 04c66f15, 27cf468a, b1aea5f9).
<!-- /student:revision -->

## 5. Revisions to `SPEC.md`

| Change | Motivating annotations | Mode |
|---|---|---|
| TOOL-3: store is a name or slug, query is keywords, `*` matches nothing | `15ee0490`, `d2cf1530`, `116b1bbc`, `ecd4b0d2`, `868ec588`, `20f03214` | `search_products_invalid_args` |
| ESC-1: call `issue_refund` in the same turn for an eligible, requested refund | `73660974`, `4dd02d06`, `3b6fa049`, `13e10dba`, `7ba948ef`, `f0740eeb` | `refund_not_submitted_after_request` |
| RESP-6 (new): change the failing argument or report `ok: false`; no identical retry | `15ee0490`, `116b1bbc`, `ecd4b0d2` | `repeated_failed_tool_call`, `tool_error_misreported` |

These edit the document only; they do not change the running agent.

## 6. Search suggestions

- **Rejected:** `fb455777` (`inconsistent_data_not_stated`).
- **Accepted:** `38dffc75`, `a8861ed3`, `b534d0d8` (`unbacked_action_claim`), `e4648cfe`, `e416e259` (`inconsistent_data_not_stated`). All six were retrieved by a deterministic screen over the frame and read before the decision.

<!-- student:suggestions -->
On the ones that passed, model flagged the data discrepancy, in the others, it didn't acknowledge it
<!-- /student:suggestions -->

## 7. Provenance and limits

- Open coding is the student's. Several early notes were revised after the student read the traces (`2297d0c2`, `0128`, `0162`).
- Claude wrote notes or decisions where the student delegated them (`source: "claude (delegated by student)"`). On 13 traces they replaced the student's "no failure observed" (`13e10dba`, `7ba948ef`, `f0740eeb`, `0269ec43`, `04c66f15`, `27cf468a`, `b1aea5f9`, `5832fe13`, `66c278db`, `26d9d711`, `59ef9309`, `ccb3c3e0`, `d85df8c2`); the student chose or delegated each replacement, and the earlier records are soft-deleted with history kept.
- Code-check modes (`search_products_invalid_args`, `repeated_failed_tool_call`, `refund_not_submitted_after_request`) were labeled by deterministic checks. The four LLM-judge modes were labeled from recorded positives and close negatives plus candidate screens; traces outside those lists are 0 by absence of a note or screen hit, not by an individual re-read.
- `repeated_failed_tool_call` and `tool_error_misreported` have no linked originating annotation yet.
- Rare modes cannot reach HW5's 30 Pass / 30 Fail: `dispute_not_escalated`, `repeated_failed_tool_call` and `tool_error_misreported` have 3 positives each, and the frame holds no more of the last two.

<!-- student:label_review -->
10 labels were reviewed, only positives
<!-- /student:label_review -->

## 8. AgentDebug comparison

AgentDebug (arXiv 2509.25370) groups agent failures into 5 modules (memory, reflection, planning, action, system-level).

<!-- student:agentdebug -->
I compared my taxonomy with AgentDebug (arXiv 2509.25370), which groups agent failures into five modules: memory, reflection, planning, action and system-level. I could read the module descriptions in the paper's main text, but not its appendix table of individual failure types; the type names below come from a second-hand reading of that table, so they should be checked against Appendix A.2 before they are relied on.

- `search_products_invalid_args` is closest to Action: Parameter Error (a malformed or unreasonable argument).
- `unbacked_action_claim` is closest to Action: Planning-Action Disconnect (the reply states an intent that the actions do not carry out).
- `tool_error_misreported` is closest to Reflection: Outcome Misinterpretation (the agent misreads what the tool returned).
- `repeated_failed_tool_call` is closest to Reflection: Causal Misattribution (the failure is noticed but the cause is not corrected).
- `dispute_not_escalated` fits Planning: Constraint Ignorance only if a policy counts as a constraint.
- `inconsistent_data_not_stated` fits Outcome Misinterpretation only weakly.
- `refund_not_submitted_after_request` has no counterpart.

I am not adding a mode because of AgentDebug. Its modules describe how an agent's reasoning and actions break down, while two of my modes (`dispute_not_escalated`, `refund_not_submitted_after_request`) are defined by this product's rules in `SPEC.md` and by my annotations, which AgentDebug does not cover. All seven modes stay.
<!-- /student:agentdebug -->
