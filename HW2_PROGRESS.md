# HW2 progress note (local only, do not commit)

## Current status
Step 0 done: progress note created. Handout, SPEC.md, server/app.py, observability/instrument.py, agent/auth.py read.
Part A done (uv sync already done by student; `_call` read). Parts A-D written. COMMITTED a3a8b9d on hw2-submission, pushed, PR #2 open on gabrielfior/cartwheel-homeworks (base main). Video recorded by student. Parts A-F DONE, hw2-traces.json written, suite green. Remaining (student): open both permalinks + read traces in UI, record video, assessments. Server (:8010) and Langfuse stack still running. Part E: E1-E5 DONE (5 requests #2,#4,#5,#8,#9 traced; see Observations; UI inspection by student still to do once). Earlier: E1-E4 for request #2 (stack rebuilt with `down` + `up -d` after clickhouse AND minio lost their docker network; server on :8010 running in background). Next E5: requests #4, #5, #8, #9 (avoid #1, #3: they write to DB).

## Environment
- Student: software engineer working with AI; terminal/curl familiar. Explain eval concepts (trace, span, attributes, prompt versioning) in depth; infra as a checklist.
- Starting state: HW1 done (five tools, DB seeded). HW2 stubs in place (NotImplementedError).
- Not yet verified: .env keys, TRACELOOP_TRACE_CONTENT, Docker, Langfuse.

## Deliverable checklist
- [x] Part A: `record_tool_result` + `_set_permission_denied_attributes` (observability/instrument.py) — written by student, ids fixed to str; Langfuse verification pending until Part E
- [x] Part B: `create_session` (server/app.py); test `-k create_session_binds` PASSED (offline). Session id minted by `_new_session_id()`. Role mismatch = 403 per handout (student expected 401; discussed).
- [x] Part C: `post_message` (server/app.py) — written; offline helper checks pass; LIVE verification pending until Part E. Shared `identity_attributes(ctx)` in instrument.py used by tool + root spans; `_message_attr` gates content on TRACELOOP_TRACE_CONTENT.
- [x] Part D: tests/test_observability.py (2 tests, in-memory sessions DB) PASSED offline
- [x] Checks: `-k hw2` 1 passed; test_observability 2 passed; full pytest 149 passed, 0 failed (x2, Langfuse up). All offline (no live model). The earlier Module 2 failure was a test-isolation leak: `import litellm` (DEV mode) loads the repo .env into os.environ, so analysis.load_store_traces went to live Langfuse. Fixed locally with `os.environ.setdefault('LITELLM_MODE','PRODUCTION')` in tests/conftest.py (NOT a deliverable; not committed unless student chooses). Not tested with Langfuse stopped.
- [x] Part E: 5 traced requests (#2,#4,#5,#8,#9) verified via Langfuse API; student to view root+tool spans in UI
- [x] Part F: A 37682731843e (trace 7806cf84f01d36538246615ed55d656c) vs B d108f6949e5e (trace 7c497fad9c19e2145b1cf0db6e908cb8), same user/request/model/tools; prompt RESTORED (sha256 9cf61eea...37fd9, git clean) and server restarted
- [x] hw2-traces.json written (e1a2a049 merchant denied + 7806cf84 shopper allowed), generated from Langfuse API; permalink form http://localhost:3000/project/cartwheel-dev/traces/<id> NOT yet confirmed in browser (student to click)
- [ ] Video (<= 5 min), recorded by student
- [ ] Assessments, by student

## Files to commit
- observability/instrument.py
- server/app.py
- tests/test_observability.py
- hw2-traces.json

## Observations
- Traced request #2 (shopper 1, 'refund for order 3980'): trace_id 7806cf84f01d36538246615ed55d656c, prompt_version 37682731843e, tools [get_order], 6 observations (root, Agent Workflow, agent, 2x model call, 1 tool). Verified via Langfuse API: root has cartwheel.session_id/user_id('1' str)/user_role/prompt_version; tool span has permission_denied=false + identity attrs, no reason. gen_ai.input/output.messages appear in Langfuse Input/Output fields (not metadata). Permalink form: http://localhost:3000/project/cartwheel-dev/traces/<trace_id> (confirm in UI).
- Earlier trace e75488e531f9041b006f0f94af304ae0 exists from an earlier request (student-sent).
- Known unresolved: Module 2 test failure (see Checks).

## Part E traces (all prompt_version 37682731843e, model openai/google/gemma-4-26B-A4B-it)
- 7806cf84f01d36538246615ed55d656c shopper 1 [get_order] denied=false (#2)
- e1a2a049bda9c83b67d915d3324958ae merchant 9002 [get_order] denied=TRUE reason role 'merchant' (user 9002) may not view order #4127 (#4)
- 14d86887cee33612528380608fe4a34e merchant 9002 [search_help_center, get_policy] 8 obs (#5)
- 22afd5318880536e37865bba17801e52 support 9501 [get_order] (#8)
- aa868f137efbe62a298707fd2129eed6 shopper 1 [find_order] (#9)
- Candidates for hw2-traces.json (student chooses): the denied merchant trace + one allowed trace.

## Part F
- Version A = current template (with 3 ESC-2 lines from commit 3f4fa86), hash 37682731843e. Baseline run A = trace 7806cf84... (request #2).
- Backup of agent/agent.py: scratchpad/agent.py.current (sha256 recorded below); git HEAD also has it (file unmodified).
- Plan: remove ONLY the 3 ESC-2 lines from SYSTEM_PROMPT_TEMPLATE (keep check_cancellable tool), restart server, new session, same request #2, compare hash, then RESTORE and restart.
- Follow-up idea (not for HW2): prompt_version hashes only the template, so tool changes are invisible; consider a separate cartwheel.tools_version attribute. Handout requires template-only hash.
