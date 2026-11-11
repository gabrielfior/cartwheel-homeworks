# HW3 scenario-generation scripts

Scaffolding used to build `scenarios/pilot_scenarios.jsonl` and `scenarios/support_scenarios.jsonl`. The committed `.jsonl` files are the deliverables; these scripts document how they were produced. Intermediate files (plans, generator and critic prompts and outputs) are not committed.

Pipeline (run from the repo root, on a freshly seeded database: `uv run python -m seed.generate`; the planners sample orders by state, so a database consumed by earlier runs can fail their checks):

1. `plan_pilot.py` / `plan_final.py`: seeded SQL sampling of dimension tuples, with an eligibility-function cross-check, writes `plan_*.json` (tuple, user-visible facts, `expected` from SQL/policy/data-quality sources).
2. `build_gen_prompts.py`: one generator prompt per plan key, from user-visible facts only (never `expected`). Generators (haiku subagents) wrote `gen_out/Fxxx.json`.
3. Critic pass (sonnet subagents) rewrote each draft into `critic_out/Fxxx.json`.
4. `assemble_pilot.py` / `assemble_final.py`: merge plan and final messages into the scenario JSONL files.
5. `select_monitoring.py`: seeded stratified pick of 50 scenarios for `scenarios/monitoring_scenarios.jsonl`.

Validate with `uv run python -m scenarios.validate <file> [--final]`.
