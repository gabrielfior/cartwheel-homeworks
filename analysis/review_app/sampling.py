"""Sampling for the HW4 review set (kept outside the app, as the skill advises).

Writes ``analysis/state/sample_manifest.json``. Every pick records its batch, the
selection reason, and the seed, so another reviewer can see how the sample was
built. A trace counts toward exactly one batch: every subcommand excludes
traces already in the manifest.

    python -m analysis.review_app.sampling status
    python -m analysis.review_app.sampling batch1 [--uniform 15] [--clusters 15]
    python -m analysis.review_app.sampling batch2 --dimension role --n 30
    python -m analysis.review_app.sampling batch3 --trace-ids ID [ID ...] --reason TEXT
    python -m analysis.review_app.sampling batch4 [--n 15]

Add ``--dry-run`` to print the picks without writing. Batch 2's dimension is
your choice and must be made before you look at outcomes. Batch 3 traces come
from depth searches you reviewed; this script only records them.
Selection never uses a model or heuristic prediction of failure.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from analysis.helpers.selection import _feature_vector, _kmeans, _standardize

from . import data as data_mod

DEFAULT_STATE = Path(__file__).resolve().parent.parent / "state"
DIMENSIONS = ("role", "store", "prompt_version")


def read_manifest(state_dir: Path) -> dict[str, Any]:
    path = state_dir / "sample_manifest.json"
    if path.exists():
        m = json.loads(path.read_text())
        m.setdefault("entries", [])
        return m
    return {"entries": []}


def write_manifest(state_dir: Path, manifest: dict[str, Any]) -> None:
    state_dir.mkdir(parents=True, exist_ok=True)
    path = state_dir / "sample_manifest.json"
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(manifest, indent=2))
    tmp.replace(path)


def uniform_picks(pool: list[dict[str, Any]], n: int, seed: int, reason: str) -> list[dict[str, str]]:
    rng = random.Random(seed)
    chosen = rng.sample(pool, min(n, len(pool)))
    return [{"trace_id": t["trace_id"], "reason": reason} for t in chosen]


def cluster_representatives(
    pool: list[dict[str, Any]], n: int, seed: int, k: int = 8
) -> list[dict[str, str]]:
    """k-means on trace features; take members nearest each centroid, round-robin."""
    if not pool:
        return []
    vectors = _standardize([_feature_vector(t) for t in pool])
    k = min(k, len(pool))
    assign = _kmeans(vectors, k=k, seed=seed)
    members: dict[int, list[tuple[float, int]]] = defaultdict(list)
    for c in set(assign):
        idx = [i for i, a in enumerate(assign) if a == c]
        cen = [sum(vectors[i][d] for i in idx) / len(idx) for d in range(len(vectors[0]))]
        members[c] = sorted(
            (sum((vectors[i][d] - cen[d]) ** 2 for d in range(len(cen))), i) for i in idx
        )
    picks: list[dict[str, str]] = []
    order = sorted(members)
    while len(picks) < n and any(members[c] for c in order):
        for c in order:
            if members[c] and len(picks) < n:
                _, i = members[c].pop(0)
                picks.append({"trace_id": pool[i]["trace_id"], "reason": f"cluster {c} representative (k={k})"})
    return picks


def load_ids(path: Path, key: str) -> set[str]:
    text = path.read_text().strip()
    if text.startswith("["):
        rows = json.loads(text)
    else:
        rows = [json.loads(line) for line in text.splitlines() if line.strip()]
    return {str(r[key] if isinstance(r, dict) else r) for r in rows}


def dimension_value(trace: dict[str, Any], dimension: str) -> str:
    return str((trace.get("meta") or {}).get(dimension) or "unknown")


def dimension_picks(
    pool: list[dict[str, Any]], dimension: str, n: int, seed: int
) -> list[dict[str, str]]:
    """Spread picks as evenly as possible across the dimension's values."""
    rng = random.Random(seed)
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for t in pool:
        buckets[dimension_value(t, dimension)].append(t)
    for b in buckets.values():
        rng.shuffle(b)
    values = sorted(buckets)
    picks: list[dict[str, str]] = []
    while len(picks) < n and any(buckets[v] for v in values):
        for v in values:
            if buckets[v] and len(picks) < n:
                t = buckets[v].pop()
                picks.append({"trace_id": t["trace_id"], "reason": f"{dimension}={v}"})
    return picks


def apply(
    state_dir: Path, pool_all: list[dict[str, Any]], batch: int, picks: list[dict[str, str]],
    seed: int, extra: dict[str, Any], dry_run: bool, frame_note: dict[str, Any] | None = None,
) -> None:
    by_id = {t["trace_id"]: t for t in pool_all}
    man = read_manifest(state_dir)
    have = {e["trace_id"] for e in man["entries"]}
    clash = [p["trace_id"] for p in picks if p["trace_id"] in have]
    if clash:
        raise SystemExit(f"refusing: {len(clash)} trace(s) already in the sample, e.g. {clash[0]}")
    for p in picks:
        if p["trace_id"] not in by_id:
            raise SystemExit(f"unknown trace id {p['trace_id']}")
    stamp = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    new = [
        {
            "trace_id": p["trace_id"],
            "session_id": str((by_id[p["trace_id"]].get("meta") or {}).get("session_id") or ""),
            "batch": batch,
            "reason": p["reason"],
            "seed": seed,
            "added_ts": stamp,
            **extra,
        }
        for p in picks
    ]
    reasons = Counter(e["reason"].split(" representative")[0] if "cluster" in e["reason"] else e["reason"] for e in new)
    print(f"batch {batch}: {len(new)} trace(s){' (dry run, nothing written)' if dry_run else ''}")
    for r, c in sorted(reasons.items()):
        print(f"  {c:3d}  {r}")
    if not dry_run:
        man["entries"].extend(new)
        man["seed"] = seed
        if frame_note:
            man["frame"] = frame_note
        write_manifest(state_dir, man)
        print(f"manifest now holds {len(man['entries'])} trace(s)")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--state-dir", default=str(DEFAULT_STATE))
    p.add_argument("--traces-file", help="trace cache-format JSON (default: the app's local cache)")
    p.add_argument("--seed", type=int, default=7)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--scenario-ids-file", help="restrict the frame to scenario ids: JSONL with an 'id' field, or a JSON list")
    p.add_argument("--exclude-ids-file", help="JSON list of objects with trace_id/session_id; their whole sessions are excluded")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status")
    b1 = sub.add_parser("batch1")
    b1.add_argument("--uniform", type=int, default=15)
    b1.add_argument("--clusters", type=int, default=15)
    b2 = sub.add_parser("batch2")
    b2.add_argument("--dimension", required=True, choices=DIMENSIONS)
    b2.add_argument("--n", type=int, default=30)
    b3 = sub.add_parser("batch3")
    b3.add_argument("--trace-ids", nargs="+", required=True)
    b3.add_argument("--reason", required=True)
    b4 = sub.add_parser("batch4")
    b4.add_argument("--n", type=int, default=15)
    b4.add_argument(
        "--exclude-sampled-sessions", action="store_true",
        help="draw only from sessions with no turn already in the sample (fresh reads for the stability check)",
    )
    args = p.parse_args(argv)

    state_dir = Path(args.state_dir)
    payload = data_mod.load_cache(Path(args.traces_file) if args.traces_file else data_mod.CACHE_PATH)
    traces = [t for t in payload["traces"] if (t.get("meta") or {}).get("scenario_id")]
    frame_note: dict[str, Any] = {}
    if args.scenario_ids_file:
        keep = load_ids(Path(args.scenario_ids_file), "id")
        traces = [t for t in traces if t["meta"]["scenario_id"] in keep]
        frame_note["frame"] = f"{len(keep)} scenario ids from {Path(args.scenario_ids_file).name}"
    if args.exclude_ids_file:
        rows = json.loads(Path(args.exclude_ids_file).read_text())
        ex_sessions = {str(r.get("session_id")) for r in rows if r.get("session_id")}
        ex_traces = {r["trace_id"] for r in rows if r.get("trace_id")}
        before = len(traces)
        traces = [
            t for t in traces
            if t["trace_id"] not in ex_traces and str(t["meta"].get("session_id")) not in ex_sessions
        ]
        frame_note["excluded"] = f"{before - len(traces)} trace(s) from {len(ex_sessions)} excluded session(s)"
    if frame_note:
        print("frame:", "; ".join(f"{k}: {v}" for k, v in frame_note.items()))
    man = read_manifest(state_dir)
    have = {e["trace_id"] for e in man["entries"]}
    pool = [t for t in traces if t["trace_id"] not in have]

    if args.cmd == "status":
        c = Counter(e["batch"] for e in man["entries"])
        print(f"pool: {len(traces)} scenario traces; sampled: {len(have)}; remaining: {len(pool)}")
        for b, target in {1: 30, 2: 30, 3: 25, 4: 15}.items():
            print(f"  batch {b}: {c.get(b, 0)}/{target}")
        return 0

    if args.cmd == "batch1":
        picks = uniform_picks(pool, args.uniform, args.seed, "uniform random")
        taken = {x["trace_id"] for x in picks}
        reps = cluster_representatives([t for t in pool if t["trace_id"] not in taken], args.clusters, args.seed)
        apply(state_dir, traces, 1, picks + reps, args.seed, {}, args.dry_run, frame_note)
    elif args.cmd == "batch2":
        picks = dimension_picks(pool, args.dimension, args.n, args.seed)
        apply(state_dir, traces, 2, picks, args.seed, {"dimension": args.dimension}, args.dry_run, frame_note)
    elif args.cmd == "batch3":
        picks = [{"trace_id": t, "reason": args.reason} for t in args.trace_ids]
        apply(state_dir, traces, 3, picks, args.seed, {}, args.dry_run, frame_note)
    elif args.cmd == "batch4":
        extra: dict[str, Any] = {}
        if args.exclude_sampled_sessions:
            seen = {e.get("session_id") for e in man["entries"] if e.get("session_id")}
            pool = [t for t in pool if str(t["meta"].get("session_id") or "") not in seen]
            extra["restriction"] = "only sessions with no turn already in the sample"
            print(f"restriction: {extra['restriction']}; pool now {len(pool)}")
        picks = uniform_picks(pool, args.n, args.seed, "uniform random (stability check)")
        apply(state_dir, traces, 4, picks, args.seed, extra, args.dry_run, frame_note)
    return 0


if __name__ == "__main__":
    sys.exit(main())
