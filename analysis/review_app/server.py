"""HW4 review app server (standard library only).

Serves ``index.html`` and a JSON API over plain files in the state directory
(default ``analysis/state/``). Differences from the reference server:

* Records are upserted one at a time under a lock, never overwritten wholesale.
* Edited notes keep their earlier text in ``history``; deletes are soft, so the
  path from observation to category stays inspectable.
* Accepted binary judgments are written to ``labels/<mode>.jsonl`` and to
  Langfuse as scores with a deterministic id (``hw4-<trace>-<mode>``), so saving
  twice updates one score instead of creating duplicates.
* Annotations and labels are only accepted for traces in the sample manifest.
* New mode names that would collide with an existing label file (for example
  the shipped HW5 reference ``unsupported_policy_claim``) are refused.

Run (from the repository root)::

    python -m analysis.review_app.server                 # port 8030
    python -m analysis.review_app.server --refresh       # re-pull Langfuse
    python -m analysis.review_app.server --offline       # never write scores
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from . import data as data_mod
from . import report as report_mod

HERE = Path(__file__).resolve().parent
DEFAULT_STATE = HERE.parent / "state"
SNAKE = re.compile(r"^[a-z][a-z0-9]*(_[a-z0-9]+)*$")
BATCH_TARGETS = {1: 30, 2: 30, 3: 25, 4: 15}
EVALUATORS = {"", "code check", "LLM judge"}
MODE_FIELDS = ("definition", "boundary", "requirement", "evaluator", "neighbor", "status")


class ApiError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


class Store:
    """All review state, backed by JSON files in ``state_dir``."""

    def __init__(
        self,
        state_dir: Path,
        payload: dict[str, Any],
        offline: bool,
        source_note: str = "",
    ):
        self.dir = Path(state_dir)
        self.labels_dir = self.dir / "labels"
        self.labels_dir.mkdir(parents=True, exist_ok=True)
        self.report_dir = self.dir.parent / "report"  # tests override this
        self.lock = threading.RLock()
        self.offline = offline
        self.source = {
            "source": payload.get("source"),
            "fetched_at": payload.get("fetched_at"),
            "note": source_note,
        }
        self.set_traces(payload["traces"])

    def set_traces(self, traces: list[dict[str, Any]]) -> None:
        self.sessions = data_mod.build_sessions(traces)
        self.trace_session: dict[str, str] = {}
        for s in self.sessions:
            for t in s["turns"]:
                self.trace_session[t["trace_id"]] = s["session_id"]

    # ---- file helpers ------------------------------------------------
    def _read(self, name: str, default: Any) -> Any:
        path = self.dir / name
        if not path.exists():
            return default
        try:
            return json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            raise ApiError(f"{name} is unreadable; fix or restore it before continuing", 500)

    def _write(self, name: str, value: Any) -> None:
        path = self.dir / name
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(value, indent=2, ensure_ascii=False))
        tmp.replace(path)

    def _annotations(self) -> dict[str, Any]:
        d = self._read("annotations.json", {"annotations": []})
        if isinstance(d, list):
            d = {"annotations": d}
        d.setdefault("annotations", [])
        return d

    def _patterns(self) -> dict[str, Any]:
        d = self._read("patterns.json", {"modes": []})
        if not isinstance(d.get("modes"), list):
            d["modes"] = []
        return d

    def _manifest(self) -> dict[str, Any]:
        d = self._read("sample_manifest.json", {"entries": []})
        d.setdefault("entries", [])
        return d

    def _suggestions(self) -> list[dict[str, Any]]:
        d = self._read("suggestions.json", [])
        return d if isinstance(d, list) else []

    def _label_path(self, mode: str) -> Path:
        if not SNAKE.match(mode):
            raise ApiError(f"invalid mode name: {mode!r}")
        return self.labels_dir / f"{mode}.jsonl"

    def _read_labels(self, mode: str) -> dict[str, dict[str, Any]]:
        path = self._label_path(mode)
        out: dict[str, dict[str, Any]] = {}
        if path.exists():
            for line in path.read_text().splitlines():
                if line.strip():
                    rec = json.loads(line)
                    out[rec["trace_id"]] = rec
        return out

    def _write_labels(self, mode: str, recs: dict[str, dict[str, Any]]) -> None:
        path = self._label_path(mode)
        tmp = path.with_suffix(".tmp")
        tmp.write_text("".join(json.dumps(recs[k], ensure_ascii=False) + "\n" for k in sorted(recs)))
        tmp.replace(path)

    # ---- reads ---------------------------------------------------------
    def labels(self) -> dict[str, dict[str, Any]]:
        out: dict[str, dict[str, Any]] = {}
        for m in self._patterns()["modes"]:
            out[m["name"]] = self._read_labels(m["name"])
        return out

    def state(self, include_sessions: bool = True) -> dict[str, Any]:
        with self.lock:
            out = {
                "meta": {**self.source, "offline": self.offline, "batch_targets": BATCH_TARGETS},
                "manifest": self._manifest(),
                "annotations": self._annotations()["annotations"],
                "patterns": self._patterns()["modes"],
                "suggestions": self._suggestions(),
                "labels": self.labels(),
            }
            if include_sessions:
                out["sessions"] = self.sessions
            return out

    # ---- manifest ------------------------------------------------------
    def manifest_add(self, trace_ids: list[str], batch: int, reason: str) -> dict[str, Any]:
        if batch not in BATCH_TARGETS:
            raise ApiError("batch must be 1, 2, 3 or 4")
        with self.lock:
            man = self._manifest()
            have = {e["trace_id"] for e in man["entries"]}
            added = []
            for tid in trace_ids:
                if tid not in self.trace_session:
                    raise ApiError(f"unknown trace id {tid}")
                if tid in have:
                    raise ApiError(f"trace {tid} is already in the sample (a trace counts toward one batch)", 409)
                man["entries"].append(
                    {
                        "trace_id": tid,
                        "session_id": self.trace_session[tid],
                        "batch": batch,
                        "reason": reason,
                        "added_ts": now(),
                    }
                )
                have.add(tid)
                added.append(tid)
            self._write("sample_manifest.json", man)
            return {"added": added, "total": len(man["entries"])}

    def _require_sampled(self, trace_id: str) -> dict[str, Any]:
        for e in self._manifest()["entries"]:
            if e["trace_id"] == trace_id:
                return e
        raise ApiError(f"trace {trace_id} is not in the sample manifest", 400)

    # ---- annotations ---------------------------------------------------
    def annotation_upsert(self, a: dict[str, Any]) -> dict[str, Any]:
        kind = a.get("kind", "note")
        if kind not in ("note", "no_failure"):
            raise ApiError("kind must be 'note' or 'no_failure'")
        tid = a.get("trace_id")
        with self.lock:
            self._require_sampled(str(tid))
            doc = self._annotations()
            items = doc["annotations"]
            note = (a.get("note") or "").strip()
            if kind == "note" and not note:
                raise ApiError("a note needs text")
            existing = next((x for x in items if x["id"] == a["id"]), None) if a.get("id") else None

            if existing:
                if existing.get("deleted"):
                    raise ApiError("annotation was deleted", 409)
                if existing.get("kind") == "note" and note != existing.get("note", ""):
                    existing.setdefault("history", []).append(
                        {"ts": existing.get("updated_ts") or existing["ts"], "note": existing.get("note", "")}
                    )
                    existing["note"] = note
                    existing["updated_ts"] = now()
                result = existing
            else:
                active = [x for x in items if x["trace_id"] == tid and not x.get("deleted")]
                if kind == "no_failure":
                    if any(x["kind"] == "note" for x in active):
                        raise ApiError("this trace already has a failure note", 409)
                    dup = next((x for x in active if x["kind"] == "no_failure"), None)
                    if dup:
                        return dup
                else:
                    for x in active:  # a note supersedes "no failure observed"
                        if x["kind"] == "no_failure":
                            x["deleted"] = True
                            x["deleted_ts"] = now()
                            x["deleted_reason"] = "superseded by a failure note"
                result = {
                    "id": a.get("id") or uuid.uuid4().hex[:12],
                    "trace_id": tid,
                    "session_id": self.trace_session[tid],
                    "kind": kind,
                    "note": note if kind == "note" else "no failure observed",
                    "quote": a.get("quote") or "",
                    "idx": a.get("idx"),
                    "start": a.get("start"),
                    "end": a.get("end"),
                    "source": a.get("source") or "human",
                    "ts": now(),
                    "deleted": False,
                }
                items.append(result)
            self._write("annotations.json", doc)
            return result

    def annotation_delete(self, ann_id: str) -> dict[str, Any]:
        with self.lock:
            doc = self._annotations()
            for x in doc["annotations"]:
                if x["id"] == ann_id and not x.get("deleted"):
                    x["deleted"] = True
                    x["deleted_ts"] = now()
                    self._write("annotations.json", doc)
                    for m in (p := self._patterns())["modes"]:
                        if ann_id in m.get("created_from", []):
                            m["created_from"] = [i for i in m["created_from"] if i != ann_id]
                    self._write("patterns.json", p)
                    return x
            raise ApiError("no such active annotation", 404)

    # ---- taxonomy ------------------------------------------------------
    def mode_upsert(self, body: dict[str, Any]) -> dict[str, Any]:
        name = body.get("name", "")
        if not SNAKE.match(name):
            raise ApiError("mode name must be snake_case (e.g. unconfirmed_write)")
        if body.get("evaluator", "") not in EVALUATORS:
            raise ApiError("evaluator must be 'code check' or 'LLM judge'")
        with self.lock:
            pat = self._patterns()
            existing = next((m for m in pat["modes"] if m["name"] == name), None)
            if existing is None:
                if (self.labels_dir / f"{name}.jsonl").exists():
                    raise ApiError(
                        f"labels/{name}.jsonl already exists (shipped or earlier work); pick another name", 409
                    )
                existing = {
                    "name": name,
                    "definition": "",
                    "boundary": "",
                    "requirement": "",
                    "evaluator": "",
                    "neighbor": "",
                    "status": "candidate",
                    "created_from": [],
                    "created_ts": now(),
                    "history": [],
                }
                pat["modes"].append(existing)
            for f in MODE_FIELDS:
                if f in body and body[f] != existing.get(f):
                    existing["history"].append(
                        {"ts": now(), "field": f, "old": existing.get(f), "new": body[f]}
                    )
                    existing[f] = body[f]
            self._write("patterns.json", pat)
            return existing

    def mode_rename(self, old: str, new: str) -> dict[str, Any]:
        """Rename a mode, keeping its history; refuses names that would collide."""
        if not SNAKE.match(new):
            raise ApiError("mode name must be snake_case (e.g. unconfirmed_write)")
        with self.lock:
            pat = self._patterns()
            mode = next((m for m in pat["modes"] if m["name"] == old), None)
            if not mode:
                raise ApiError("unknown mode", 404)
            if any(m["name"] == new for m in pat["modes"]) or (self.labels_dir / f"{new}.jsonl").exists():
                raise ApiError(f"mode or labels file '{new}' already exists", 409)
            old_labels = self.labels_dir / f"{old}.jsonl"
            if old_labels.exists():
                recs = self._read_labels(old)
                for r in recs.values():
                    r["mode"] = new
                self._write_labels(new, recs)
                old_labels.unlink()
            mode["history"].append({"ts": now(), "field": "name", "old": old, "new": new})
            mode["name"] = new
            self._write("patterns.json", pat)
            return mode

    def mode_link(self, name: str, ann_id: str, linked: bool) -> dict[str, Any]:
        with self.lock:
            pat = self._patterns()
            mode = next((m for m in pat["modes"] if m["name"] == name), None)
            if not mode:
                raise ApiError("unknown mode", 404)
            ann = next((x for x in self._annotations()["annotations"] if x["id"] == ann_id and not x.get("deleted")), None)
            if not ann:
                raise ApiError("unknown or deleted annotation", 404)
            links = mode.setdefault("created_from", [])
            if linked and ann_id not in links:
                links.append(ann_id)
                mode["history"].append({"ts": now(), "field": "created_from", "added": ann_id})
            if not linked and ann_id in links:
                links.remove(ann_id)
                mode["history"].append({"ts": now(), "field": "created_from", "removed": ann_id})
            self._write("patterns.json", pat)
            return mode

    # ---- labels --------------------------------------------------------
    def label_set(self, body: dict[str, Any]) -> dict[str, Any]:
        tid, mode, label = body.get("trace_id"), body.get("mode"), body.get("label")
        if label not in (0, 1):
            raise ApiError("label must be 1 (failure present) or 0 (absent)")
        with self.lock:
            entry = self._require_sampled(str(tid))
            if not any(m["name"] == mode for m in self._patterns()["modes"]):
                raise ApiError("define the mode in the taxonomy before labeling with it", 400)
            recs = self._read_labels(mode)
            rec = {
                "trace_id": tid,
                "session_id": entry["session_id"],
                "mode": mode,
                "label": label,
                "evidence": (body.get("evidence") or "").strip(),
                "close_negative": bool(body.get("close_negative")) and label == 0,
                "source": body.get("source") or "human",
                "ts": now(),
                "langfuse_synced": False,
            }
            try:
                self._push_score(rec)
                rec["langfuse_synced"] = not self.offline
            except Exception as exc:  # keep the local judgment, report the gap
                rec["langfuse_error"] = f"{type(exc).__name__}: {exc}"
            recs[tid] = rec
            self._write_labels(mode, recs)
            return rec

    def _push_score(self, rec: dict[str, Any]) -> None:
        if self.offline:
            return
        from analysis.helpers import langfuse_io

        client = langfuse_io._client()
        client.create_score(
            name=rec["mode"],
            value=int(rec["label"]),
            trace_id=rec["trace_id"],
            score_id=f"hw4-{rec['trace_id']}-{rec['mode']}",
            data_type="NUMERIC",
            comment=rec.get("evidence") or None,
        )
        client.flush()

    def labels_sync(self) -> dict[str, Any]:
        """Retry Langfuse writes for judgments that did not sync."""
        done = failed = 0
        with self.lock:
            for m in self._patterns()["modes"]:
                recs = self._read_labels(m["name"])
                dirty = False
                for rec in recs.values():
                    if rec.get("langfuse_synced"):
                        continue
                    try:
                        self._push_score(rec)
                        if not self.offline:
                            rec["langfuse_synced"] = True
                            rec.pop("langfuse_error", None)
                            done += 1
                            dirty = True
                    except Exception as exc:
                        rec["langfuse_error"] = f"{type(exc).__name__}: {exc}"
                        failed += 1
                        dirty = True
                if dirty:
                    self._write_labels(m["name"], recs)
        return {"synced": done, "failed": failed, "offline": self.offline}

    # ---- written report ------------------------------------------------
    def _report_answers(self) -> dict[str, Any]:
        d = self._read("report_answers.json", {"answers": {}})
        d.setdefault("answers", {})
        return d

    def report_state(self) -> dict[str, Any]:
        with self.lock:
            return {
                "questions": report_mod.questions(list(self.trace_session)),
                "answers": self._report_answers()["answers"],
            }

    def report_answer(self, qid: str, text: str) -> dict[str, Any]:
        if not any(q["id"] == qid for q in report_mod.QUESTIONS):
            raise ApiError("unknown question", 404)
        text = text or ""
        with self.lock:
            doc = self._report_answers()
            cur = doc["answers"].get(qid, {"text": "", "history": []})
            if text.strip() == cur["text"].strip():
                return cur
            if cur["text"].strip():
                cur["history"].append({"ts": cur.get("ts"), "text": cur["text"]})
            cur["text"] = text
            cur["ts"] = now()
            doc["answers"][qid] = cur
            self._write("report_answers.json", doc)
            return cur

    def report_export(self) -> dict[str, Any]:
        with self.lock:
            return report_mod.export(self.report_dir, self._report_answers()["answers"])

    # ---- suggestions ---------------------------------------------------
    def suggestions_replace(self, incoming: list[dict[str, Any]]) -> dict[str, Any]:
        with self.lock:
            cur = {s["id"]: s for s in self._suggestions()}
            for s in incoming:
                if s.get("trace_id") not in self.trace_session:
                    raise ApiError(f"unknown trace id {s.get('trace_id')}")
                s.setdefault("id", uuid.uuid4().hex[:12])
                if s["id"] in cur and cur[s["id"]].get("status") != "pending":
                    continue  # never overwrite a human decision
                s.setdefault("status", "pending")
                s.setdefault("ts", now())
                cur[s["id"]] = s
            self._write("suggestions.json", list(cur.values()))
            return {"count": len(cur)}

    def suggestion_decide(self, sid: str, decision: str, reason: str = "") -> dict[str, Any]:
        if decision not in ("accept", "reject"):
            raise ApiError("decision must be 'accept' or 'reject'")
        with self.lock:
            sugg = self._suggestions()
            s = next((x for x in sugg if x["id"] == sid), None)
            if not s:
                raise ApiError("no such suggestion", 404)
            if s.get("status") != "pending":
                raise ApiError("suggestion already decided", 409)
            ann = None
            if decision == "accept":
                tid = s["trace_id"]
                man = self._manifest()
                if not any(e["trace_id"] == tid for e in man["entries"]):
                    self.manifest_add([tid], 3, f"accepted suggestion for {s.get('mode', '?')}")
                ann = self.annotation_upsert(
                    {
                        "trace_id": tid,
                        "kind": "note",
                        "note": s.get("text") or f"accepted suggestion ({s.get('mode', '?')}): {s.get('quote', '')}",
                        "quote": s.get("quote"),
                        "idx": s.get("idx"),
                        "start": s.get("start"),
                        "end": s.get("end"),
                        "source": "accepted_suggestion",
                    }
                )
                s["annotation_id"] = ann["id"]
            s["status"] = "accepted" if decision == "accept" else "rejected"
            s["decided_ts"] = now()
            if reason:
                s["decision_reason"] = reason
            self._write("suggestions.json", sugg)
            return {"suggestion": s, "annotation": ann}

    # ---- progress ------------------------------------------------------
    def progress(self) -> dict[str, Any]:
        with self.lock:
            entries = self._manifest()["entries"]
            ann = [a for a in self._annotations()["annotations"] if not a.get("deleted")]
            modes = self._patterns()["modes"]
            labels = self.labels()
            by_trace: dict[str, list[dict[str, Any]]] = {}
            for a in ann:
                by_trace.setdefault(a["trace_id"], []).append(a)
            batch_of = {e["trace_id"]: e["batch"] for e in entries}
            batches = {}
            for b, target in BATCH_TARGETS.items():
                ids = [e["trace_id"] for e in entries if e["batch"] == b]
                batches[b] = {
                    "target": target,
                    "sampled": len(ids),
                    "reviewed": sum(1 for t in ids if t in by_trace),
                }
            reviewed = sum(1 for e in entries if e["trace_id"] in by_trace)
            per_mode = {}
            missing = 0
            for m in modes:
                recs = labels.get(m["name"], {})
                present = sum(1 for r in recs.values() if r["label"] == 1)
                absent = sum(1 for r in recs.values() if r["label"] == 0)
                miss = sum(1 for e in entries if e["trace_id"] not in recs)
                missing += miss
                links = [by_id for by_id in m.get("created_from", [])]
                first_batches = [
                    batch_of[a["trace_id"]]
                    for a in ann
                    if a["id"] in links and a["trace_id"] in batch_of
                ]
                per_mode[m["name"]] = {
                    "present": present,
                    "absent": absent,
                    "close_negatives": sum(1 for r in recs.values() if r.get("close_negative")),
                    "missing": miss,
                    "first_seen_batch": min(first_batches) if first_batches else None,
                    "sample_fraction": (present / len(recs)) if recs else None,
                }
            return {
                "total_sampled": len(entries),
                "total_reviewed": reviewed,
                "unreviewed": len(entries) - reviewed,
                "min_required": 100,
                "batches": batches,
                "modes": per_mode,
                "missing_judgments": missing,
                "mode_count": len(modes),
                "new_modes_first_seen_in_batch_4": [n for n, v in per_mode.items() if v["first_seen_batch"] == 4],
                "pending_suggestions": sum(1 for s in self._suggestions() if s.get("status") == "pending"),
            }


# ---------------------------------------------------------------------------
# HTTP layer
# ---------------------------------------------------------------------------


def make_handler(store: Store, refresh_fn=None):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args: Any) -> None:  # quiet
            return

        def _json(self, payload: Any, status: int = 200) -> None:
            body = json.dumps(payload, default=str).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _origin_ok(self) -> bool:
            origin = self.headers.get("Origin")
            if not origin:
                return True
            return urlparse(origin).netloc == self.headers.get("Host")

        def do_GET(self) -> None:  # noqa: N802
            path = urlparse(self.path).path
            try:
                if path in ("/", "/index.html"):
                    body = (HERE / "index.html").read_bytes()
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                elif path == "/api/state":
                    query = urlparse(self.path).query
                    self._json(store.state(include_sessions="sessions=0" not in query))
                elif path == "/api/progress":
                    self._json(store.progress())
                elif path == "/api/report":
                    self._json(store.report_state())
                else:
                    self._json({"error": f"unknown path {path}"}, 404)
            except ApiError as e:
                self._json({"error": str(e)}, e.status)

        def do_POST(self) -> None:  # noqa: N802
            path = urlparse(self.path).path
            if not self._origin_ok():
                self._json({"error": "cross-origin request refused"}, 403)
                return
            length = int(self.headers.get("Content-Length") or 0)
            try:
                body = json.loads(self.rfile.read(length)) if length else {}
            except json.JSONDecodeError:
                self._json({"error": "expected a JSON body"}, 400)
                return
            try:
                if path == "/api/annotation":
                    self._json(store.annotation_upsert(body))
                elif path == "/api/annotation/delete":
                    self._json(store.annotation_delete(body.get("id", "")))
                elif path == "/api/mode":
                    self._json(store.mode_upsert(body))
                elif path == "/api/mode/rename":
                    self._json(store.mode_rename(body.get("from", ""), body.get("to", "")))
                elif path == "/api/mode/link":
                    self._json(store.mode_link(body.get("name", ""), body.get("annotation_id", ""), bool(body.get("linked", True))))
                elif path == "/api/label":
                    self._json(store.label_set(body))
                elif path == "/api/labels/sync":
                    self._json(store.labels_sync())
                elif path == "/api/manifest/add":
                    self._json(store.manifest_add(body.get("trace_ids", []), int(body.get("batch", 0)), body.get("reason", "")))
                elif path == "/api/suggestions":
                    items = body if isinstance(body, list) else body.get("suggestions", [])
                    self._json(store.suggestions_replace(items))
                elif path == "/api/suggestion/decide":
                    self._json(store.suggestion_decide(body.get("id", ""), body.get("decision", ""), body.get("reason", "")))
                elif path == "/api/report/answer":
                    self._json(store.report_answer(body.get("id", ""), body.get("text", "")))
                elif path == "/api/report/export":
                    self._json(store.report_export())
                elif path == "/api/refresh":
                    if refresh_fn is None:
                        raise ApiError("refresh is unavailable in this mode", 400)
                    self._json(refresh_fn())
                else:
                    self._json({"error": f"cannot POST to {path}"}, 404)
            except ApiError as e:
                self._json({"error": str(e)}, e.status)

    return Handler


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--port", type=int, default=8030)
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--state-dir", default=str(DEFAULT_STATE))
    p.add_argument("--traces-file", help="trace cache-format JSON to load instead of Langfuse (tests, offline)")
    p.add_argument("--refresh", action="store_true", help="re-pull traces from Langfuse and rewrite the cache")
    p.add_argument("--offline", action="store_true", help="never write Langfuse scores (labels stay local)")
    args = p.parse_args(argv)

    note = ""
    if args.traces_file:
        payload = data_mod.load_cache(Path(args.traces_file))
        note = f"loaded from {args.traces_file}"
    else:
        payload = None
        if not args.refresh and data_mod.CACHE_PATH.exists():
            payload = data_mod.load_cache()
            note = "served from local cache (use --refresh to re-pull Langfuse)"
        if payload is None:
            try:
                payload = data_mod.fetch_and_cache()
                note = "fetched live from Langfuse"
            except Exception as exc:
                if data_mod.CACHE_PATH.exists():
                    payload = data_mod.load_cache()
                    note = f"Langfuse unavailable ({type(exc).__name__}: {exc}); using cache. Record this in interface_comparison.md."
                else:
                    print(f"cannot load traces: {exc}", file=sys.stderr)
                    return 1

    store = Store(Path(args.state_dir), payload, offline=args.offline, source_note=note)

    def refresh() -> dict[str, Any]:
        fresh = data_mod.fetch_and_cache()
        with store.lock:
            store.source.update(source=fresh["source"], fetched_at=fresh["fetched_at"], note="refreshed from Langfuse")
            store.set_traces(fresh["traces"])
        return {"traces": len(fresh["traces"]), "sessions": len(store.sessions)}

    server = ThreadingHTTPServer((args.host, args.port), make_handler(store, None if args.traces_file else refresh))
    print(f"review app on http://{args.host}:{args.port}/  ({len(store.sessions)} sessions; {note})")
    print(f"state dir: {store.dir}  |  Langfuse score writes: {'OFF (--offline)' if args.offline else 'ON'}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nshutting down")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
