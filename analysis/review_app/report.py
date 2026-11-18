"""Questions for the written HW4 deliverables, shown next to the traces they concern.

Each question maps to a ``<!-- student:ID -->`` block in a markdown file under
``analysis/report/``. The answers are the student's own words, saved in
``analysis/state/report_answers.json``; ``export`` copies them into the blocks.
Nothing here writes an answer for the student.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

SUMMARY = "review_summary.md"
IFACE = "interface_comparison.md"

# Facts are as of 2026-11-15 and were checked against the saved state.
QUESTIONS: list[dict[str, Any]] = [
    {
        "id": "stability",
        "file": SUMMARY,
        "section": "3. New modes in the final 15 traces",
        "title": "What does batch 4 say about stability?",
        "ask": "In a few sentences: did the taxonomy hold up on the 15 fresh traces, and what did you do about what you found?",
        "cover": [
            "The count the handout asks for: how many new modes appeared in the final 15.",
            "Whether that new mode was consequential, and why.",
            "What you did next (the rest of the earlier sample was rechecked for it).",
            "Whether you now consider the taxonomy stable.",
        ],
        "facts": [
            "Batch 4 is 15 uniform random traces from sessions with no turn already in the sample.",
            "You wrote notes on 3 of them and marked 12 'no failure observed'. The notes on 3b6fa049 and 4dd02d06 describe the same behavior: the agent asks permission instead of issuing a refund the user asked for. That became refund_not_submitted_after_request (new mode).",
            "Your note on b1aea5f9 ('no failure') was later converted to a wildcard-query failure, which fits an existing mode. 76cc3a60's note ('no need for filter') is not a failure.",
            "After the new mode existed, the earlier sample was rechecked: 6 traces carry it in total (73660974, 4dd02d06, 3b6fa049, 13e10dba, 7ba948ef, f0740eeb). You converted three earlier 'no failure' calls to notes.",
        ],
        "traces": [
            ["3b6fa049", "batch 4: asks 'Would you like me to go ahead and issue the refund?' after an explicit request"],
            ["4dd02d06", "batch 4: refund over $100, agent never calls issue_refund and asks to proceed"],
            ["b1aea5f9", "batch 4: query '*' reported as an empty store (fits an existing mode)"],
            ["76cc3a60", "batch 4: your note 'no need for filter', not a failure"],
        ],
    },
    {
        "id": "revision",
        "file": SUMMARY,
        "section": "4. One taxonomy revision",
        "title": "Tell one taxonomy revision",
        "ask": "Pick ONE revision and write 4 to 6 sentences: what you saw, what you changed in the taxonomy, and why that is the right call.",
        "cover": [
            "What the traces showed that made the first version wrong or incomplete.",
            "The decision rule you used (the handout's: would one product change fix both?).",
            "Which traces support the change.",
        ],
        "facts": [
            "CANDIDATE A, merge: the first mode was 'store filter is an ID instead of a name' (15ee0490, d2cf1530, 116b1bbc, ecd4b0d2, 2cf7b873). Later traces called search_products with query '*' and a valid store (868ec588, 20f03214). Both produce an empty or failed search from a bad argument, and one product change (state in the tool contract what store and query accept) fixes both, so they were merged into search_products_invalid_args. Four more '*' traces were found later (0269ec43, 04c66f15, 27cf468a, b1aea5f9).",
            "CANDIDATE B, new mode after batch 4: you had decided 73660974 (agent asks permission although the user asked) gets no mode. Batch 4 showed the same behavior twice more in fresh data, so a seventh mode was added and the earlier call reversed.",
            "CANDIDATE C, narrowing: repeated_failed_tool_call was first written as 'identical arguments'. 15ee0490 repeats the failing store value 19 but changes the other arguments, so the definition was changed to 'failing argument left unchanged' to match RESP-6.",
            "The merge (A) is the one with a decision rule and conflicting traces behind it.",
        ],
        "traces": [
            ["15ee0490", "A and C: store '19' (an ID) twice, other arguments vary"],
            ["868ec588", "A: query '*' with a valid store"],
            ["20f03214", "A: query '*' with a valid store"],
            ["73660974", "B: the earlier 'no mode' decision"],
            ["4dd02d06", "B: the batch 4 repeat"],
        ],
    },
    {
        "id": "suggestions",
        "file": SUMMARY,
        "section": "6. Search suggestions",
        "title": "Your decisions on the search suggestions",
        "ask": "Confirm that you agree with the accept and reject decisions, and say in your own words why fb455777 is excluded and where the boundary lies.",
        "cover": [
            "The boundary: what separates a trace that is a failure from fb455777.",
            "Why the five accepted traces are failures (or tell me if you disagree).",
        ],
        "facts": [
            "The six traces were retrieved by a deterministic screen over the frame, not by a model judgment. You read each one before the decision.",
            "REJECTED fb455777 (inconsistent_data_not_stated): the product list contains a price of -5, and the reply tells the user the price 'appears to be incorrect'. The mode needs the reply to hide or rely on the contradiction, so this is absent.",
            "ACCEPTED 38dffc75, a8861ed3, b534d0d8 (unbacked_action_claim): each promises an action ('I'll need to escalate', 'I am escalating', 'One moment please!') without a matching tool call.",
            "ACCEPTED e4648cfe, e416e259 (inconsistent_data_not_stated): both rely on order 8001, whose delivery date comes before its ship date, and neither mentions it.",
        ],
        "traces": [
            ["fb455777", "rejected: flags the bad price to the user"],
            ["38dffc75", "accepted: promises escalation, no escalate_to_human call"],
            ["a8861ed3", "accepted: 'I am escalating', no call anywhere"],
            ["b534d0d8", "accepted: 'One moment please!' and the turn ends"],
            ["e4648cfe", "accepted: order 8001 delivery date relied on"],
            ["e416e259", "accepted: order 8001 'not eligible' relied on"],
        ],
    },
    {
        "id": "label_review",
        "file": SUMMARY,
        "section": "7. Provenance and limits",
        "title": "How much of the labels did you review?",
        "ask": "One or two sentences stating honestly how much of the labels you checked yourself, and what you changed.",
        "cover": [
            "Which labels you looked at (for example only the positives, or every cell in the Labels tab).",
            "Anything you disagreed with and changed.",
        ],
        "facts": [
            "The three code-check modes were labeled by deterministic rules; the four LLM-judge modes were labeled from the recorded positives and close negatives plus candidate screens.",
            "Traces outside those lists are 0 by absence of any note or screen hit, not by an individual re-read of all 105 traces.",
            "Open the Labels tab to review the cells; every label written by the reviewer carries the source 'claude (delegated by student)'.",
            "Borderline calls worth a look: b534d0d8 (flags the bad price but promises a check that never happens) and e416e259 (the 'not eligible' verdict rests on contradictory dates but offers escalation).",
        ],
        "traces": [
            ["b534d0d8", "borderline: unbacked promise after flagging the bad price"],
            ["e416e259", "borderline: correct escalation offer, but silent on the contradiction"],
            ["45f76839", "close negative: queued refund, your note says a human should have been called"],
        ],
        "links": [["labels", "Open the Labels tab"]],
    },
    {
        "id": "agentdebug",
        "file": SUMMARY,
        "section": "8. AgentDebug comparison",
        "title": "Check the AgentDebug mapping",
        "ask": "Open the paper's failure taxonomy (Table 2 in the appendix), check the mapping below, and write what you found: what matches, what does not, and whether you keep or change any mode.",
        "cover": [
            "Whether any mode of yours has no counterpart (the handout says add a mode only if your own traces support it).",
            "Whether any of your names is unclear next to theirs.",
        ],
        "facts": [
            "AgentDebug (arXiv 2509.25370) has 17 failure types in 5 modules: memory, reflection, planning, action, system-level. The list here was read through a subagent and is not verified by you.",
            "search_products_invalid_args is closest to Action: Parameter Error.",
            "unbacked_action_claim is closest to Planning-Action Disconnect; tool_error_misreported to Reflection: Outcome Misinterpretation; repeated_failed_tool_call to Reflection: Causal Misattribution; dispute_not_escalated to Planning: Constraint Ignorance.",
            "inconsistent_data_not_stated fits Outcome Misinterpretation only weakly; refund_not_submitted_after_request has no counterpart. Both come from SPEC.md rules and your annotations.",
        ],
        "traces": [],
        "links": [["https://arxiv.org/abs/2509.25370", "Open the paper"]],
    },
    {
        "id": "iface_retained",
        "file": IFACE,
        "section": "One design retained from the reference interface",
        "title": "A design you kept from the reference interface",
        "ask": "Name one design from analysis/ui/index.html that you kept, and say why it is worth keeping.",
        "cover": ["Which element, and what it does for the reviewer."],
        "facts": [
            "The supplied reference (analysis/ui/index.html) has three views (Trace, Map, Progress) and shows one trace at a time.",
            "It groups a tool_call with the tool_result that follows it into one step, highlights the quoted span in a message, and places the margin note next to it. Accepting a suggestion turns it into your annotation.",
            "Your interface (analysis/review_app/) keeps the grouped tool_call/result steps, the span highlight with margin notes, and accept-to-annotation for suggestions. The code is newly written, not a copy.",
        ],
        "traces": [],
    },
    {
        "id": "iface_changed",
        "file": IFACE,
        "section": "One design changed after inspecting my traces",
        "title": "A design you changed after looking at your traces",
        "ask": "Describe one change you made after seeing real traces, and what you saw that drove it.",
        "cover": ["What the problem looked like in Langfuse or in the reference.", "What you changed."],
        "facts": [
            "Your note: Langfuse is very cluttered and needs several clicks to see a full trace.",
            "Cartwheel writes one Langfuse trace per user turn, with no native session id. In the sampled data a follow-up turn on its own hides the tool calls of the first turn. Your interface groups turns by cartwheel.session_id and shows each conversation in order, which the handout requires; the reference shows a single trace at a time.",
            "Example: a two-turn session where the second turn only makes sense with the first.",
        ],
        "traces": [
            ["a8861ed3", "turn 2 of a two-turn session: the reply says 'As I mentioned' about turn 1"],
            ["e416e259", "two-turn session"],
        ],
    },
    {
        "id": "iface_limitation",
        "file": IFACE,
        "section": "One limitation remaining",
        "title": "One limitation you will stand behind",
        "ask": "Pick one real limitation and state it plainly, with its effect on a reviewer.",
        "cover": ["What is missing or awkward.", "How it affects review or labels."],
        "facts": [
            "Open-coding notes live in analysis/state/annotations.json, not in Langfuse; only the binary mode labels become Langfuse scores.",
            "The 16 offline tests do not drive the browser UI, and no Playwright pass was run.",
            "The reference has a Map view (2D projection of the traces) that your interface does not have.",
        ],
        "traces": [],
    },
]


def resolve(trace_ids: list[str], prefix: str) -> str | None:
    return next((t for t in trace_ids if t.startswith(prefix)), None)


def questions(trace_ids: list[str]) -> list[dict[str, Any]]:
    out = []
    for q in QUESTIONS:
        item = {k: v for k, v in q.items() if k != "traces"}
        item["traces"] = [
            {"trace_id": full, "why": why}
            for prefix, why in q.get("traces", [])
            if (full := resolve(trace_ids, prefix))
        ]
        out.append(item)
    return out


BANNER = re.compile(r"^> \*\*DRAFT scaffold\.\*\*.*\n\n?", re.M)


def export(report_dir: Path, answers: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Copy answers into their ``<!-- student:ID -->`` blocks; report what is still open."""
    done: list[str] = []
    open_: list[str] = []
    missing: list[str] = []
    for fname in (SUMMARY, IFACE):
        path = report_dir / fname
        if not path.exists():
            missing.append(fname)
            continue
        text = path.read_text()
        for q in (x for x in QUESTIONS if x["file"] == fname):
            pat = re.compile(rf"(<!-- student:{q['id']} -->)(.*?)(<!-- /student:{q['id']} -->)", re.S)
            if not pat.search(text):
                missing.append(f"{fname}:{q['id']}")
                continue
            ans = (answers.get(q["id"], {}).get("text") or "").strip()
            if ans:
                text = pat.sub(lambda m: f"{m.group(1)}\n{ans}\n{m.group(3)}", text, count=1)
                done.append(q["id"])
            else:
                open_.append(q["id"])
        if not any(q["id"] in open_ for q in QUESTIONS if q["file"] == fname):
            text = BANNER.sub("", text)
        path.write_text(text)
    return {"written": done, "unanswered": open_, "missing_markers": missing}
