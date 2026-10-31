# HW1 video run sheet (local only, do not commit)

Target: one continuous take, 5 minutes or less. Aim for about 4:30 so there is slack.
Run everything from the repository root in one terminal window.

## Before you press record
1. Reset the data so the demo orders are fresh:
   `uv run python -m seed.generate`
2. Close or hide `.env` and any editor tab showing keys. Never show it on screen.
3. Use a large terminal font. Clear the screen (`clear`).
4. Have `agent/agent.py` open at the Escalation section (about line 74) in your editor, to show the edit.
5. Quit any old CLI sessions. Start each conversation in a fresh CLI.

## Beat sheet

| Time | What to show | Command / message |
|---|---|---|
| 0:00 | One-line intro: what HW1 is, which model (see banner) | none |
| 0:15 | **Authorized request** (shopper 1) | `uv run python -m agent.cli --role shopper --user 1 --debug` then `Can you show me the status of order 4127?` then `quit` |
| 0:50 | **Permission denial** (merchant, store 2) | `uv run python -m agent.cli --role merchant --user 9002 --debug` then `Show me order 4127.` then `quit` |
| 1:25 | **Refund for order 4455** (above the $100 threshold) | `uv run python -m agent.cli --role shopper --user 1 --debug` then `I want a full refund for order 4455.` and, if it asks, `It arrived broken.` then `quit` |
| 2:10 | **Say out loud** whether it called `issue_refund` or `escalate_to_human` (read it from the `[tool]` lines) | none |
| 2:25 | **Requirement examined (ESC-2): the failure.** Show the recorded "before" (record 7) | `python3 -c "import json;r=[json.loads(l) for l in open('hw1-session.jsonl')][6];print(json.dumps({k:r[k] for k in ('request','tool_calls','response','requirement','met_requirement','problem_source')},indent=1))"` |
| 3:00 | **The exact edit** | `git show HEAD -- agent/agent.py` (the diff also shows the `check_cancellable` wrapper below it; point at the 3 added lines in the Escalation section at the top) |
| 3:20 | **After:** rerun the same request in a fresh session | `uv run python -m agent.cli --role shopper --user 1 --debug` then `Can you change the email address on my Cartwheel account to new@example.com?` then `quit` |
| 3:55 | **Run a test** | `uv run pytest --runxfail tests/test_hw_holes.py -k hw1` |
| 4:15 | **Record count** | `wc -l hw1-session.jsonl` |
| 4:25 | Wrap up | none |

## Things to know while recording
- The model is non-deterministic. If it does something different from your recorded run (for example the 4455 case calls `issue_refund` and gets `queued_for_approval` instead of escalating), narrate what you actually see. That is fine and honest.
- The 4455 and email cases may create support tickets. Reset afterwards: `uv run python -m seed.generate`.
- If a take goes badly, reset the data and start over. The video must be one continuous recording.
- The "before" of the ESC-2 case is shown from the saved record, because the prompt now contains the fix. The "after" is the live run.

## After recording
- Reset the data once more: `uv run python -m seed.generate`
- Tell Claude the video is done so the checklist can be updated.
