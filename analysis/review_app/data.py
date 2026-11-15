"""Trace loading, offline cache, and session grouping for the HW4 review app.

Langfuse is the canonical trace store. ``fetch_and_cache`` pulls the Module 1
traces (via ``analysis.helpers.langfuse_io.fetch_traces``) and keeps a slim copy
under ``analysis/review_app/.cache/`` (gitignored) so the app and the sampling
script can run when Langfuse is temporarily unreachable. The Langfuse trace id
is preserved everywhere, so a judgment is always written to the trace the
reviewer actually read.

Cartwheel records one Langfuse trace per user turn, and Langfuse's native
``sessionId`` is empty on these traces. The conversation link lives only in the
``cartwheel.session_id`` metadata, so ``build_sessions`` regroups turns by it.
"""

from __future__ import annotations

import json
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
CACHE_PATH = HERE / ".cache" / "traces.json"


def slim_trace(trace: dict[str, Any]) -> dict[str, Any]:
    """Keep only what review and sampling need from a normalized trace."""
    meta = dict(trace.get("meta") or {})
    metadata = trace.get("metadata") or {}
    user_id = metadata.get("cartwheel.user_id")
    if user_id is not None:
        meta["user_id"] = user_id
    return {
        "trace_id": trace["trace_id"],
        "timestamp": trace.get("timestamp"),
        "meta": meta,
        "features": trace.get("features") or {},
        "messages": trace.get("trace") or [],
    }


def write_cache(traces: list[dict[str, Any]], source: str, path: Path = CACHE_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "source": source,
        "traces": traces,
    }
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, default=str))
    tmp.replace(path)


def load_cache(path: Path = CACHE_PATH) -> dict[str, Any]:
    """Return ``{"fetched_at", "source", "traces"}``; raise if absent or empty."""
    if not path.exists():
        raise FileNotFoundError(f"no trace cache at {path}")
    payload = json.loads(path.read_text())
    if not payload.get("traces"):
        raise ValueError(f"trace cache is empty: {path}")
    return payload


def fetch_and_cache(path: Path = CACHE_PATH) -> dict[str, Any]:
    """Pull live traces from Langfuse (read-only) and refresh the local cache."""
    from analysis.helpers import langfuse_io

    traces = [slim_trace(t) for t in langfuse_io.fetch_traces()]
    if not traces:
        raise RuntimeError("Langfuse returned no Cartwheel traces")
    write_cache(traces, "langfuse", path)
    return load_cache(path)


def build_sessions(traces: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Group per-turn traces into sessions, turns in chronological order."""
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for t in traces:
        meta = t.get("meta") or {}
        sid = meta.get("session_id") or meta.get("scenario_id") or t["trace_id"]
        groups[str(sid)].append(t)

    sessions: list[dict[str, Any]] = []
    for sid, turns in groups.items():
        turns = sorted(turns, key=lambda t: (str(t.get("timestamp") or ""), t["trace_id"]))
        meta = turns[0].get("meta") or {}
        sessions.append(
            {
                "session_id": sid,
                "role": meta.get("role"),
                "store": meta.get("store"),
                "prompt_version": meta.get("prompt_version"),
                "scenario_id": meta.get("scenario_id"),
                "user_id": meta.get("user_id"),
                "turns": [
                    {
                        "trace_id": t["trace_id"],
                        "timestamp": t.get("timestamp"),
                        "messages": t.get("messages") or [],
                        "features": t.get("features") or {},
                    }
                    for t in turns
                ],
            }
        )
    sessions.sort(key=lambda s: (str(s["turns"][0].get("timestamp") or ""), s["session_id"]))
    return sessions
