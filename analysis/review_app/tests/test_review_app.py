"""Offline tests for the HW4 review app.

All traces here are synthetic (invented for testing, not Cartwheel data). The
tests use a temporary state directory and ``offline=True``, so they never touch
Langfuse, the network, or the real ``analysis/state/`` files.

Run from the repository root:  python -m unittest analysis.review_app.tests.test_review_app -v
"""

from __future__ import annotations

import json
import tempfile
import threading
import unittest
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

from analysis.review_app import sampling
from analysis.review_app.server import ApiError, Store, make_handler


def _trace(tid, session, ts, role="shopper", tools=0, reply="ok"):
    msgs = [{"role": "user", "text": f"user text {tid}"}]
    for i in range(tools):
        msgs.append({"role": "tool_call", "name": "get_order", "arguments": {"order_id": i}})
        msgs.append({"role": "tool_result", "name": "get_order", "content": {"ok": True, "order": {"order_id": i}}})
    msgs.append({"role": "assistant", "text": reply})
    return {
        "trace_id": tid,
        "timestamp": ts,
        "meta": {"session_id": session, "role": role, "store": 1, "prompt_version": "v1", "scenario_id": f"sc-{session}"},
        "features": {"turn_count": 2, "tool_call_count": tools, "distinct_tools": min(tools, 1), "has_retrieval": 0, "tokens": 50 + tools * 40},
        "messages": msgs,
    }


TRACES = [
    _trace("t-a1", "s-a", "2026-01-01T10:00:00", "shopper", 2),
    _trace("t-a2", "s-a", "2026-01-01T10:01:00", "shopper", 0),  # later turn of session s-a
    _trace("t-b1", "s-b", "2026-01-01T11:00:00", "merchant", 1),
    _trace("t-c1", "s-c", "2026-01-01T12:00:00", "support", 0),
    _trace("t-d1", "s-d", "2026-01-01T13:00:00", "shopper", 3),
    _trace("t-d2", "s-d", "2026-01-01T13:02:00", "shopper", 1),
    _trace("t-e1", "s-e", "2026-01-01T14:00:00", "merchant", 2),
    _trace("t-f1", "s-f", "2026-01-01T15:00:00", "support", 1),
]


class StoreTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        # Out-of-order input proves turns are sorted chronologically.
        payload = {"source": "test", "fetched_at": "now", "traces": list(reversed(TRACES))}
        self.store = Store(self.dir, payload, offline=True)

    def tearDown(self):
        self._tmp.cleanup()

    def sample(self, ids, batch=1, reason="test"):
        return self.store.manifest_add(ids, batch, reason)

    # -- written report ----------------------------------------------------
    def test_report_answers_keep_history_and_export_fills_blocks_only(self):
        self.store.report_dir = self.dir / "report"  # never write next to the temp dir's parent
        self.store.report_dir.mkdir()
        from analysis.review_app import report

        def doc(banner):
            blocks = "".join(
                f"## {q['id']}\n<!-- student:{q['id']} -->\n**[STUDENT]** placeholder\n<!-- /student:{q['id']} -->\n"
                for q in report.QUESTIONS if q["file"] == "review_summary.md"
            )
            return (("> **DRAFT scaffold.** delete me\n\n" if banner else "") + "# Title\n" + blocks)

        (self.store.report_dir / "review_summary.md").write_text(doc(True))
        (self.store.report_dir / "interface_comparison.md").write_text("no markers here\n")
        with self.assertRaises(ApiError):
            self.store.report_answer("nope", "x")
        self.store.report_answer("stability", "first")
        self.store.report_answer("stability", "second")
        a = self.store.report_state()["answers"]["stability"]
        self.assertEqual((a["text"], [h["text"] for h in a["history"]]), ("second", ["first"]))
        out = self.store.report_export()
        self.assertEqual(out["written"], ["stability"])
        text = (self.store.report_dir / "review_summary.md").read_text()
        self.assertIn("<!-- student:stability -->\nsecond\n<!-- /student:stability -->", text)
        self.assertIn("**[STUDENT]** placeholder", text)  # unanswered blocks stay as placeholders
        self.assertIn("DRAFT scaffold", text)  # banner stays while a question is open
        self.assertEqual(self.store.report_export()["written"], ["stability"])  # idempotent
        for q in report.QUESTIONS:
            if q["file"] == "review_summary.md":
                self.store.report_answer(q["id"], f"answer {q['id']}")
        self.store.report_export()
        text = (self.store.report_dir / "review_summary.md").read_text()
        self.assertNotIn("DRAFT scaffold", text)
        self.assertNotIn("[STUDENT]", text)
        self.assertEqual((self.store.report_dir / "interface_comparison.md").read_text(), "no markers here\n")

    # -- sessions ----------------------------------------------------------
    def test_sessions_grouped_by_session_id_in_chronological_order(self):
        by = {s["session_id"]: s for s in self.store.sessions}
        self.assertEqual([t["trace_id"] for t in by["s-a"]["turns"]], ["t-a1", "t-a2"])
        self.assertEqual([t["trace_id"] for t in by["s-d"]["turns"]], ["t-d1", "t-d2"])
        self.assertEqual(len(self.store.sessions), 6)

    # -- manifest ------------------------------------------------------------
    def test_trace_counts_toward_one_batch_only(self):
        self.sample(["t-a1"], 1)
        with self.assertRaises(ApiError) as cm:
            self.sample(["t-a1"], 2)
        self.assertEqual(cm.exception.status, 409)
        with self.assertRaises(ApiError):
            self.sample(["nope"], 1)

    # -- annotations ---------------------------------------------------------
    def test_annotation_requires_sampled_trace(self):
        with self.assertRaises(ApiError):
            self.store.annotation_upsert({"trace_id": "t-a1", "kind": "note", "note": "x"})

    def test_note_edit_keeps_history_and_delete_is_soft(self):
        self.sample(["t-a1"])
        a = self.store.annotation_upsert({"trace_id": "t-a1", "note": "first wording", "quote": "q", "idx": "0"})
        self.store.annotation_upsert({**a, "note": "second wording"})
        doc = json.loads((self.dir / "annotations.json").read_text())["annotations"][0]
        self.assertEqual(doc["note"], "second wording")
        self.assertEqual(doc["history"][0]["note"], "first wording")
        self.store.annotation_delete(a["id"])
        doc = json.loads((self.dir / "annotations.json").read_text())["annotations"][0]
        self.assertTrue(doc["deleted"])  # still on disk

    def test_no_failure_rules(self):
        self.sample(["t-a1", "t-b1"])
        n1 = self.store.annotation_upsert({"trace_id": "t-a1", "kind": "no_failure"})
        n2 = self.store.annotation_upsert({"trace_id": "t-a1", "kind": "no_failure"})
        self.assertEqual(n1["id"], n2["id"])  # idempotent
        self.store.annotation_upsert({"trace_id": "t-a1", "note": "now I see a failure"})
        active = [a for a in json.loads((self.dir / "annotations.json").read_text())["annotations"] if not a["deleted"]]
        self.assertEqual([a["kind"] for a in active], ["note"])  # note superseded no_failure
        with self.assertRaises(ApiError) as cm:  # and cannot be re-added while a note exists
            self.store.annotation_upsert({"trace_id": "t-a1", "kind": "no_failure"})
        self.assertEqual(cm.exception.status, 409)

    # -- taxonomy ------------------------------------------------------------
    def test_mode_name_validation_collision_and_history(self):
        with self.assertRaises(ApiError):
            self.store.mode_upsert({"name": "Bad Name"})
        (self.dir / "labels" / "shipped_mode.jsonl").write_text("{}\n")
        with self.assertRaises(ApiError) as cm:
            self.store.mode_upsert({"name": "shipped_mode"})
        self.assertEqual(cm.exception.status, 409)
        self.store.mode_upsert({"name": "unconfirmed_write", "definition": "v1"})
        m = self.store.mode_upsert({"name": "unconfirmed_write", "definition": "v2"})
        self.assertEqual(m["definition"], "v2")
        self.assertTrue(any(h.get("old") == "v1" and h.get("new") == "v2" for h in m["history"]))

    def test_mode_rename_keeps_links_history_and_labels_and_refuses_collisions(self):
        self.sample(["t-a1"])
        a = self.store.annotation_upsert({"trace_id": "t-a1", "note": "n"})
        self.store.mode_upsert({"name": "old_name", "definition": "d"})
        self.store.mode_upsert({"name": "other_mode"})
        self.store.mode_link("old_name", a["id"], True)
        self.store.label_set({"trace_id": "t-a1", "mode": "old_name", "label": 1})
        with self.assertRaises(ApiError) as cm:
            self.store.mode_rename("old_name", "other_mode")
        self.assertEqual(cm.exception.status, 409)
        with self.assertRaises(ApiError):
            self.store.mode_rename("old_name", "Bad Name")
        m = self.store.mode_rename("old_name", "new_name")
        self.assertEqual(m["name"], "new_name")
        self.assertEqual(m["created_from"], [a["id"]])
        self.assertTrue(any(h.get("field") == "name" and h.get("old") == "old_name" for h in m["history"]))
        self.assertFalse((self.dir / "labels" / "old_name.jsonl").exists())
        rec = json.loads((self.dir / "labels" / "new_name.jsonl").read_text().splitlines()[0])
        self.assertEqual(rec["mode"], "new_name")

    def test_deleting_annotation_unlinks_it_from_modes(self):
        self.sample(["t-a1"])
        a = self.store.annotation_upsert({"trace_id": "t-a1", "note": "n"})
        self.store.mode_upsert({"name": "m_one"})
        self.store.mode_link("m_one", a["id"], True)
        self.store.annotation_delete(a["id"])
        pats = json.loads((self.dir / "patterns.json").read_text())["modes"]
        self.assertEqual(pats[0]["created_from"], [])

    # -- labels --------------------------------------------------------------
    def test_label_requires_mode_and_sampled_trace_and_flips(self):
        self.sample(["t-a1"])
        with self.assertRaises(ApiError):
            self.store.label_set({"trace_id": "t-a1", "mode": "m_one", "label": 1})
        self.store.mode_upsert({"name": "m_one"})
        with self.assertRaises(ApiError):
            self.store.label_set({"trace_id": "t-b1", "mode": "m_one", "label": 1})  # not sampled
        with self.assertRaises(ApiError):
            self.store.label_set({"trace_id": "t-a1", "mode": "m_one", "label": 2})
        rec = self.store.label_set({"trace_id": "t-a1", "mode": "m_one", "label": 1, "evidence": "e"})
        self.assertFalse(rec["langfuse_synced"])  # offline: never reaches Langfuse
        self.store.label_set({"trace_id": "t-a1", "mode": "m_one", "label": 0, "close_negative": True})
        lines = (self.dir / "labels" / "m_one.jsonl").read_text().splitlines()
        self.assertEqual(len(lines), 1)  # one record per trace and mode
        self.assertEqual(json.loads(lines[0])["label"], 0)
        self.assertTrue(json.loads(lines[0])["close_negative"])

    # -- suggestions ---------------------------------------------------------
    def test_suggestions_never_override_decisions_and_accept_creates_annotation(self):
        self.sample(["t-a1"])
        self.store.suggestions_replace([{"id": "s1", "trace_id": "t-b1", "mode": "m", "quote": "user text t-b1", "idx": "0", "start": 0, "end": 4}])
        out = self.store.suggestion_decide("s1", "accept")
        self.assertEqual(out["annotation"]["source"], "accepted_suggestion")
        entry = [e for e in json.loads((self.dir / "sample_manifest.json").read_text())["entries"] if e["trace_id"] == "t-b1"]
        self.assertEqual(entry[0]["batch"], 3)  # unsampled trace joins batch 3 only on acceptance
        self.store.suggestions_replace([{"id": "s1", "trace_id": "t-b1", "mode": "other", "quote": "x"}])
        cur = json.loads((self.dir / "suggestions.json").read_text())[0]
        self.assertEqual(cur["status"], "accepted")
        self.assertEqual(cur["mode"], "m")  # unchanged
        self.store.suggestions_replace([{"id": "s2", "trace_id": "t-c1", "mode": "m", "quote": "q"}])
        self.store.suggestion_decide("s2", "reject", "different failure")
        s2 = [s for s in json.loads((self.dir / "suggestions.json").read_text()) if s["id"] == "s2"][0]
        self.assertEqual(s2["status"], "rejected")
        with self.assertRaises(ApiError):
            self.store.suggestion_decide("s2", "accept")

    # -- progress ------------------------------------------------------------
    def test_progress_counts(self):
        self.sample(["t-a1", "t-b1"], 1)
        self.sample(["t-c1"], 4)
        self.store.annotation_upsert({"trace_id": "t-a1", "kind": "no_failure"})
        n = self.store.annotation_upsert({"trace_id": "t-c1", "note": "late"})
        self.store.mode_upsert({"name": "late_mode"})
        self.store.mode_link("late_mode", n["id"], True)
        self.store.label_set({"trace_id": "t-a1", "mode": "late_mode", "label": 0})
        p = self.store.progress()
        self.assertEqual((p["total_sampled"], p["total_reviewed"], p["unreviewed"]), (3, 2, 1))
        self.assertEqual(p["batches"][1]["reviewed"], 1)
        self.assertEqual(p["missing_judgments"], 2)
        self.assertEqual(p["new_modes_first_seen_in_batch_4"], ["late_mode"])


class SamplingTest(unittest.TestCase):
    def test_uniform_is_deterministic_and_clusters_are_disjoint(self):
        a = sampling.uniform_picks(TRACES, 3, 7, "u")
        b = sampling.uniform_picks(TRACES, 3, 7, "u")
        self.assertEqual(a, b)
        taken = {x["trace_id"] for x in a}
        reps = sampling.cluster_representatives([t for t in TRACES if t["trace_id"] not in taken], 3, 7, k=2)
        self.assertEqual(len(reps), 3)
        self.assertFalse(taken & {x["trace_id"] for x in reps})

    def test_dimension_picks_spread_across_values(self):
        picks = sampling.dimension_picks(TRACES, "role", 6, 7)
        roles = [p["reason"] for p in picks]
        for r in ("role=shopper", "role=merchant", "role=support"):
            self.assertEqual(roles.count(r), 2)

    def test_apply_refuses_overlap_and_dry_run_writes_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            sampling.apply(d, TRACES, 1, [{"trace_id": "t-a1", "reason": "r"}], 7, {}, dry_run=True)
            self.assertFalse((d / "sample_manifest.json").exists())
            sampling.apply(d, TRACES, 1, [{"trace_id": "t-a1", "reason": "r"}], 7, {}, dry_run=False)
            with self.assertRaises(SystemExit):
                sampling.apply(d, TRACES, 2, [{"trace_id": "t-a1", "reason": "r"}], 7, {}, dry_run=False)


class SamplingFrameTest(unittest.TestCase):
    def test_frame_flags_and_exclude_sampled_sessions(self):
        from analysis.review_app import data as data_mod

        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            cache, state = d / "traces.json", d / "state"
            data_mod.write_cache(TRACES, "test", cache)
            (d / "scen.jsonl").write_text("".join(json.dumps({"id": f"sc-s-{c}"}) + "\n" for c in "abcde"))  # drops s-f
            (d / "exclude.json").write_text(json.dumps([{"trace_id": "t-e1", "session_id": "s-e"}]))  # drops s-e
            base = ["--state-dir", str(state), "--traces-file", str(cache),
                    "--scenario-ids-file", str(d / "scen.jsonl"), "--exclude-ids-file", str(d / "exclude.json")]
            self.assertEqual(sampling.main(base + ["batch3", "--trace-ids", "t-a1", "--reason", "seed"]), 0)
            self.assertEqual(sampling.main(base + ["batch4", "--n", "10", "--exclude-sampled-sessions"]), 0)
            man = json.loads((state / "sample_manifest.json").read_text())
            b4 = [e for e in man["entries"] if e["batch"] == 4]
            # s-a is already sampled (so t-a2 is out), s-e is excluded, s-f is outside the frame
            self.assertEqual({e["trace_id"] for e in b4}, {"t-b1", "t-c1", "t-d1", "t-d2"})
            self.assertTrue(all(e["restriction"] == "only sessions with no turn already in the sample" for e in b4))
            self.assertIn("frame", man["frame"])
            self.assertIn("excluded", man["frame"])


class HttpSmokeTest(unittest.TestCase):
    def test_http_roundtrip_and_origin_check(self):
        with tempfile.TemporaryDirectory() as d:
            store = Store(Path(d), {"source": "test", "fetched_at": "now", "traces": TRACES}, offline=True)
            store.manifest_add(["t-a1"], 1, "t")
            srv = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(store))
            threading.Thread(target=srv.serve_forever, daemon=True).start()
            base = f"http://127.0.0.1:{srv.server_address[1]}"
            try:
                html = urllib.request.urlopen(base + "/").read().decode()
                self.assertIn("Cartwheel", html)
                state = json.load(urllib.request.urlopen(base + "/api/state"))
                self.assertEqual(len(state["sessions"]), 6)
                self.assertNotIn("sessions", json.load(urllib.request.urlopen(base + "/api/state?sessions=0")))

                def post(path, body, headers=None):
                    req = urllib.request.Request(base + path, json.dumps(body).encode(), {"Content-Type": "application/json", **(headers or {})})
                    return urllib.request.urlopen(req)

                r = json.load(post("/api/annotation", {"trace_id": "t-a1", "note": "hello", "quote": "q", "idx": "0"}))
                self.assertEqual(r["note"], "hello")
                with self.assertRaises(urllib.error.HTTPError) as cm:
                    post("/api/annotation", {"trace_id": "t-a1", "note": "x"}, {"Origin": "http://evil.example"})
                self.assertEqual(cm.exception.code, 403)
                with self.assertRaises(urllib.error.HTTPError) as cm:
                    post("/api/annotation", {"trace_id": "t-b1", "note": "not sampled"})
                self.assertEqual(cm.exception.code, 400)
            finally:
                srv.shutdown()
                srv.server_close()


if __name__ == "__main__":
    unittest.main()
