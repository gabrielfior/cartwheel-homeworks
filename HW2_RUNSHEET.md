# HW2 video runsheet (local only, do not commit)

Plan for the one continuous recording, 5:00 max. No scripted answers: the
explanations are yours. This only says what to show and where.

## Before you hit record

- [ ] Server running: `curl -s localhost:8010/health` returns `status: ok`
      (start it with `uv run uvicorn server.app:app --port 8010`)
- [ ] Langfuse healthy: `curl -s localhost:3000/api/public/health`, UI signed in
      (`student@example.com`)
- [ ] Two browser tabs open, one per permalink:
  - http://localhost:3000/project/cartwheel-dev/traces/e1a2a049bda9c83b67d915d3324958ae
  - http://localhost:3000/project/cartwheel-dev/traces/7806cf84f01d36538246615ed55d656c
- [ ] Terminal in the repo root, large font; notifications off
- [ ] `server/app.py` open at `create_session` and `_authorize`
- [ ] Both permalinks confirmed to load (if not, use the `?peek=` form)
- [ ] Prompt is the restored one: `git status --short agent/agent.py` prints nothing

## Timeline

| Time | Handout requirement | Show |
| --- | --- | --- |
| 0:00-0:30 | Context | Path: message -> POST /sessions -> signed token -> POST /messages -> `_authorize` -> agent -> tools -> trace in Langfuse |
| 0:30-1:15 | **Run one authentication test** | `uv run pytest tests/test_observability.py -v`. Point at the role-mismatch test (403, no session stored) and the cross-session token test (403, plus the control that the token works for its own session) |
| 1:15-2:00 | **Explain how the endpoint established the authenticated identity** | `create_session`: DB lookup, role check, `AuthContext` from the stored row, signed token. `_authorize`: signature, session id match, session exists. Where the message body is used, and where it is not |
| 2:00-3:15 | **Read both traces root to final response** and **explain the tool calls and results** | Trace `e1a2a049...` (merchant 9002, denied): root span attributes and Input/Output, then the `get_order` tool span: args, result, `cartwheel.permission_denied=true`, the reason. Trace `7806cf84...` (shopper 1, allowed): root, `get_order` args and result, `permission_denied=false`, final reply. Use the JSON view if `parts` is collapsed |
| 3:15-4:15 | **Show the two prompt version hashes** | `37682731843e` (current template) vs `d108f6949e5e` (3 ESC-2 lines removed). Traces `7806cf84...` and `7c497fad9c19e2145b1cf0db6e908cb8`; same user, request and model |
| 4:15-4:50 | **Regenerate the span count for one selected trace** | Run the command below; it should print the same number the UI tree shows |

## Span count command (read-only; prints a number, no secrets)

```bash
uv run python -c "import base64,json,urllib.request as u;e=dict(l.split('=',1) for l in open('.env').read().splitlines() if '=' in l and l[0]!='#');a=base64.b64encode(f\"{e['LANGFUSE_PUBLIC_KEY']}:{e['LANGFUSE_SECRET_KEY']}\".encode()).decode();r=u.Request(e['LANGFUSE_HOST']+'/api/public/traces/7806cf84f01d36538246615ed55d656c',headers={'Authorization':'Basic '+a});print(len(json.load(u.urlopen(r))['observations']))"
```

Expected for `7806cf84...`: 6 (root, Agent Workflow, agent, 2 model calls, 1 tool).
Cross-check the same number against the tree in the UI.

## Where things are in the UI

- Tool span attributes: click the `get_order` row (type TOOL), then Metadata ->
  `attributes` -> `cartwheel.*` and `gen_ai.*`.
- Root span attributes: click `cartwheel.session_message` (not the trace row).
- `prompt_version`: root span, Metadata -> `attributes` -> `cartwheel.prompt_version`.

## Reference values

| Trace | Caller | tool_order | prompt_version |
| --- | --- | --- | --- |
| e1a2a049bda9c83b67d915d3324958ae | merchant 9002 | get_order (denied) | 37682731843e |
| 7806cf84f01d36538246615ed55d656c | shopper 1 | get_order | 37682731843e |
| 7c497fad9c19e2145b1cf0db6e908cb8 | shopper 1 (edited prompt) | get_order | d108f6949e5e |

## Open items that are yours

- [ ] Permalinks confirmed in the browser
- [ ] Read both traces in the UI
- [ ] Record the video (5:00 max, one continuous take)
- [ ] Assessments
