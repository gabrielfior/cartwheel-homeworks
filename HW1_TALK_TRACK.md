# HW1 talk track (local only, do not commit)

Prompts and facts to anchor what you say. Put it in your own words and add what you
actually observed. These are not a script to read out.

## 1. Intro (about 15 s)
- Homework 1: finish five support tools, then examine the agent through manual conversations.
- Agent model and where it runs (read it from the CLI banner or your notes).

## 2. Authorized request, order 4127 (about 35 s)
- Shopper 1 owns the order, so `get_order` succeeds.
- What do you notice in the answer? (Facts from your session: it gave status and delivery date but
  no product name, because order results carry only a `product_id`.)

## 3. Permission denial (about 35 s)
- Merchant 9002 belongs to store 2; order 4127 belongs to store 1.
- `get_order` returns `permission_denied` in the tool layer, not because the model decided.
- Why this is enforced in code rather than the prompt (AUTH-1: authorization is not a prompt).
- Point out that the reply reveals nothing about the order (RESP-4).

## 4. Refund for order 4455 (about 45 s)
- The order is $240, above the $100 auto-approval threshold (ESC-1).
- Say which tool it called: `issue_refund`, `escalate_to_human`, or neither at first. What happened
  to the refund, and what did the user get told?
- Your own assessment: did it meet the requirement? (In your recorded run it did not cite a policy
  id, RESP-1.)

## 5. The requirement I examined: ESC-2 (about 1 min 30 s)
- Requirement: account changes of any kind always go to a human.
- What the prompt said: nothing about account changes, and its refusal line said it refuses
  "credential changes".
- My prediction: the agent would refuse instead of escalating.
- The failure (record 7 and the fresh rerun): it refused, no tool call, no ticket.
- Why I judged it a prompt problem and not a tool problem: there is no tool that changes accounts,
  and the tools were not involved; the decision was the model's.
- The exact edit: one added sentence in the Escalation section (show it on screen).
- Same request, fresh session, after the edit: it called `escalate_to_human`, created a ticket, and
  did not claim the email was changed (RESP-2).
- Honest limit: one run each; the model is non-deterministic, so this shows the edit can fix the
  case, not that it always will.

## 6. Test and records (about 30 s)
- Run the HW1 tests. Say what passing means here (the five tools meet their contracts).
- Count the records: 10 conversations, all three roles.

## 7. Close (about 10 s)
- One sentence on what surprised you most. Candidates from your own results: the wrong 30-day
  answer for store 2, or the agent saying order 10 was not cancellable when it was.

## Extra tool (mention briefly if time allows)
- `check_cancellable`: added after conversation 10, where the agent confused refund eligibility
  with cancellability. With the tool, the same request now checks and then cancels.
