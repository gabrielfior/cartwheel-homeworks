"""Render pilot results for human review: scenario + expected + agent replies + tool calls (Langfuse API) + DB effects.
Read-only. Usage: python render_results.py <scenarios.jsonl> <results.jsonl> <out.md>"""
import base64
import json
import os
import sqlite3
import sys
import urllib.request
from pathlib import Path

REPO = Path("/Users/gabrielfior/code/cartwheel-homeworks")
env = {}
for line in (REPO / ".env").read_text().splitlines():
    if "=" in line and not line.lstrip().startswith("#"):
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip().strip('"')
HOST, PK, SK = env["LANGFUSE_HOST"], env["LANGFUSE_PUBLIC_KEY"], env["LANGFUSE_SECRET_KEY"]
AUTH = "Basic " + base64.b64encode(f"{PK}:{SK}".encode()).decode()


def api(path):
    req = urllib.request.Request(HOST + path, headers={"Authorization": AUTH})
    return json.loads(urllib.request.urlopen(req, timeout=30).read())


def short(x, n=260):
    s = x if isinstance(x, str) else json.dumps(x, ensure_ascii=False)
    s = " ".join(s.split())
    return s if len(s) <= n else s[: n - 1] + "…"


scen = {json.loads(l)["id"]: json.loads(l) for l in Path(sys.argv[1]).read_text().splitlines() if l.strip()}
res = {json.loads(l)["scenario_id"]: json.loads(l) for l in Path(sys.argv[2]).read_text().splitlines() if l.strip()}

# trace ids per scenario, in time order
traces = {}
page = 1
while True:
    d = api(f"/api/public/traces?limit=100&page={page}&name=cartwheel.session_message")
    for t in d["data"]:
        sid = (t.get("metadata") or {}).get("attributes", {}).get("cartwheel.scenario_id")
        if sid and sid.startswith("pilot-"):
            traces.setdefault(sid, []).append((t["timestamp"], t["id"]))
    if page >= d["meta"]["totalPages"]:
        break
    page += 1

conn = sqlite3.connect(f"file:{REPO / 'data' / 'cartwheel.db'}?mode=ro", uri=True)
conn.row_factory = sqlite3.Row


def order_now(oid):
    r = conn.execute("select status, total_cents, refund_eligible from orders where id=?", (oid,)).fetchone()
    refs = conn.execute("select id, amount_cents, status, created_at from refunds where order_id=? order by id", (oid,)).fetchall()
    return r, refs


lines = ["# HW3 pilot results: review sheet (local only, do not commit)", "",
         f"{len(res)} results · tool calls read from Langfuse (`{HOST}`) · order state read from `data/cartwheel.db` AFTER the run.", "",
         "You decide `scenario_valid`, `confirmed_failure` and `evidence` for `scenarios/pilot_review.jsonl`. "
         "The \"Observed facts\" below are mechanical (what tools ran, what the DB shows), not judgments.", ""]
summary = []
for sid in sorted(scen):
    s, r = scen[sid], res[sid]
    t, e = s["tuple"], s["expected"]
    tr = sorted(traces.get(sid, []))
    tools_by_turn = []
    for ts, tid in tr:
        obs = api(f"/api/public/traces/{tid}")["observations"]
        calls = sorted([o for o in obs if o["type"] == "TOOL"], key=lambda o: o["startTime"])
        tools_by_turn.append((tid, [(o["name"], o.get("input"), o.get("output")) for o in calls]))
    all_tools = [c[0] for _, cs in tools_by_turn for c in cs]
    summary.append((sid, s["scenario_group"], t["intent"], t["record_state"], e.get("outcome", "human_judgment"), all_tools))

    lines += ["---", "", f"## {sid} · {s['scenario_group']} · {t['role']} · {t['intent']} · {t['record_state']}"
              + (f" · dq `{s['data_quality_case_id']}`" if s["data_quality_case_id"] else ""), ""]
    lines.append(f"Tone `{t['user_style']}` · turns {t['turn_count']} · order {t.get('order_id', '—')} · product {t.get('product_id', '—')} · user {t['user_id']} ({t['role']})")
    lines.append("")
    lines.append("**Answer key**")
    if e["evaluation"] == "objective":
        lines.append(f"- outcome `{e['outcome']}` — {e['reason']}  \n- source `{e['source']['type']}` → `{e['source']['reference']}`")
    else:
        lines.append(f"- human judgment: {e['criterion']}  \n- source `{e['source']['type']}` → `{e['source']['reference']}`")
    lines.append("")
    lines.append("**Conversation as run**")
    lines.append("")
    for i, turn in enumerate(r["turns"]):
        lines.append(f"> **User:** {turn['user']}")
        lines.append(">")
        lines.append(f"> **Agent:** {' '.join(turn['agent'].split())}")
        lines.append("")
        if i < len(tools_by_turn):
            tid, calls = tools_by_turn[i]
            if calls:
                for name, inp, out in calls:
                    lines.append(f"- tool `{name}` ← `{short(inp, 160)}` → `{short(out, 300)}`")
            else:
                lines.append("- no tool calls")
            lines.append(f"- trace `{tid}`")
            lines.append("")
    if "order_id" in t:
        row, refs = order_now(t["order_id"])
        lines.append(f"**Observed facts:** order {t['order_id']} status now `{row['status']}`, refund rows: "
                     + (", ".join(f"#{x['id']} {x['status']} ${x['amount_cents']/100:.2f} {x['created_at']}" for x in refs) if refs else "none"))
        lines.append("")
    lines += ["**Your review:** valid? ☐ yes ☐ no · confirmed failure? ☐ yes ☐ no · evidence / scenario_change:", ""]

head = ["", "## Tool usage at a glance", "", "| Scenario | Group | Intent | Expected | Tools called |", "|---|---|---|---|---|"]
for sid, g, intent, rs, outcome, tools in summary:
    head.append(f"| {sid} | {g} | {intent} | `{outcome}` | {', '.join(tools) or '—'} |")
lines[6:6] = head + [""]
Path(sys.argv[3]).write_text("\n".join(lines) + "\n")
print(f"wrote {sys.argv[3]}: {len(summary)} scenarios, {sum(len(v) for v in traces.values())} traces")
