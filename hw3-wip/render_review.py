"""Render scenarios/pilot_scenarios.jsonl as a Markdown review sheet. Read-only on the DB."""
import json
import sqlite3
import sys
from pathlib import Path

REPO = Path("/Users/gabrielfior/code/cartwheel-homeworks")
src, out = Path(sys.argv[1]), Path(sys.argv[2])
conn = sqlite3.connect(f"file:{REPO / 'data' / 'cartwheel.db'}?mode=ro", uri=True)
conn.row_factory = sqlite3.Row

ORDER_SQL = """SELECT o.id, o.user_id, o.status, o.total_cents, o.ordered_at, o.shipped_at, o.delivered_at,
  o.refund_eligible, s.name store, s.return_window_days_override ov, p.title product,
  CAST(julianday('2026-07-01') - julianday(o.delivered_at) AS INT) AS age
  FROM orders o JOIN stores s ON s.id=o.store_id JOIN products p ON p.id=o.product_id WHERE o.id=?"""


def money(c):
    return f"${c/100:,.2f}"


def order_line(oid):
    r = conn.execute(ORDER_SQL, (oid,)).fetchone()
    if not r:
        return f"order {oid}: NOT FOUND"
    parts = [f"order **{r['id']}**", f"{r['product'] or '(empty title)'}", f"store {r['store']}" + (f" (override {r['ov']}d)" if r["ov"] is not None else ""),
             f"owner user {r['user_id']}", f"status `{r['status']}`", money(r["total_cents"]),
             f"ordered {r['ordered_at']}", f"shipped {r['shipped_at'] or '—'}", f"delivered {r['delivered_at'] or '—'}" + (f" ({r['age']} days before 2026-07-01)" if r["age"] is not None else ""),
             f"`refund_eligible={r['refund_eligible']}`"]
    return " · ".join(parts)


def product_line(pid):
    r = conn.execute("SELECT p.id, p.title, p.price_cents, s.name store FROM products p JOIN stores s ON s.id=p.store_id WHERE p.id=?", (pid,)).fetchone()
    return f"product **{r['id']}** · title `{r['title']!r}` · {money(r['price_cents'])} · store {r['store']}"


rows = [json.loads(l) for l in src.read_text().splitlines() if l.strip()]
lines = [
    "# HW3 pilot scenarios: review sheet (local only, do not commit)",
    "",
    f"Source: `{src}` · {len(rows)} scenarios · generated read-only from the JSONL and `data/cartwheel.db` (as-of date 2026-07-01).",
    "",
    "For each case check: (1) is the language realistic for the tone? (2) do the followups make sense without seeing the agent's reply? (3) does the answer key match the record shown?",
    "Mark each **Decision** as `accept`, `revise` (say how) or `reject`.",
    "",
    "| # | ID | Group | Role | Intent | Record state | Tone | Turns |",
    "|---|---|---|---|---|---|---|---|",
]
for i, r in enumerate(rows, 1):
    t = r["tuple"]
    lines.append(f"| {i} | {r['id']} | {r['scenario_group']} | {t['role']} | {t['intent']} | {t['record_state']} | {'angry' if t['user_style']=='frustrated_impatient' else 'polite'} | {t['turn_count']} |")
lines.append("")

for i, r in enumerate(rows, 1):
    t, e = r["tuple"], r["expected"]
    lines += [f"---", "", f"## {i}. {r['id']} · {r['scenario_group']}" + (f" · damaged record `{r['data_quality_case_id']}`" if r["data_quality_case_id"] else ""), ""]
    lines.append(f"**Tuple:** role `{t['role']}` (user {t['user_id']}) · intent `{t['intent']}` · record `{t['record_state']}` · policy `{t['applicable_policy']}` · tools `{t['tools_needed']}` · difficulty `{t['difficulty']}` · tone `{t['user_style']}` · turns {t['turn_count']} · refund band `{t['refund_amount_band']}`")
    lines.append("")
    lines.append("**Conversation**")
    lines.append("")
    lines.append(f"> **User:** {r['opening_message']}")
    for f in r["followups"]:
        lines.append(f">")
        lines.append(f"> *(scripted followup)* **User:** {f}")
    lines.append("")
    lines.append("**Record in the database**")
    lines.append("")
    if "order_id" in t:
        lines.append(f"- {order_line(t['order_id'])}")
        if "merchant_store_id" in t:
            lines.append(f"- the merchant (user {t['user_id']}) owns store id {t['merchant_store_id']}")
        if "owner_user_id" in t:
            lines.append(f"- the caller is user {t['user_id']}, not the owner (user {t['owner_user_id']})")
    if "product_id" in t:
        lines.append(f"- {product_line(t['product_id'])}")
    if "order_id" not in t and "product_id" not in t:
        lines.append("- none (no specific record)")
    lines.append("")
    lines.append("**Answer key (`expected`)**")
    lines.append("")
    if e["evaluation"] == "objective":
        lines.append(f"- outcome: `{e['outcome']}`")
        lines.append(f"- reason: {e['reason']}")
    else:
        lines.append(f"- human judgment criterion: {e['criterion']}")
    lines.append(f"- source: `{e['source']['type']}` → `{e['source']['reference']}`")
    lines += ["", "**Decision:** ☐ accept  ☐ revise  ☐ reject  — notes:", ""]

out.write_text("\n".join(lines) + "\n")
print(f"wrote {out} ({len(rows)} cases)")
