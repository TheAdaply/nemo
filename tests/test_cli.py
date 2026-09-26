"""Executable public-CLI contract for issue #2's offline retrieval slice."""

import hashlib
import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
FIXTURE = REPO / "fixtures" / "synthetic"


class RetrievalCLITest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.root = self.work / "documents"
        self.root.mkdir()
        self.db = self.work / "index.sqlite"

    def cli(self, *args, expected_success=True):
        result = subprocess.run(
            [sys.executable, "-m", "nemo_memory", *map(str, args), "--json"],
            cwd=REPO,
            text=True,
            capture_output=True,
            timeout=20,
            check=False,
        )
        if expected_success:
            self.assertEqual(result.returncode, 0, result.stderr)
            return json.loads(result.stdout)
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertNotIn("Traceback", result.stderr)
        return result.stderr.lower()

    def test_index_and_rank_exact_id_and_quoted_phrase_with_verifiable_citation(self):
        self.assertEqual(self.cli("index", self.root, "--db", self.db), {"files": 0, "passages": 0})
        target = self.root / "projects" / "orbit.md"
        target.parent.mkdir()
        source = "# Project ORBIT-742\nThe copper lantern review is approved.\nThe current owner is Mara Vale.\n"
        target.write_text(source, encoding="utf-8")
        (self.root / "distractor.txt").write_text(
            "Project ORBIT-743 schedules a copper lantern rehearsal.\n", encoding="utf-8"
        )
        (self.root / "ignore.csv").write_text("ORBIT-742 copper lantern review", encoding="utf-8")
        indexed = self.cli("index", self.root, "--db", self.db)
        self.assertEqual(indexed["files"], 2)
        self.assertGreaterEqual(indexed["passages"], 2)
        for query, matching_line in (("ORBIT-742", 1), ('"copper lantern review"', 2)):
            with self.subTest(query=query):
                hits = self.cli("search", query, "--db", self.db)
                self.assertTrue(hits, query)
                first = hits[0]
                self.assertEqual(first["path"], "projects/orbit.md")
                self.assertEqual(first["revision"], "sha256:" + hashlib.sha256(target.read_bytes()).hexdigest())
                start, end = first["start_line"], first["end_line"]
                self.assertIsInstance(start, int)
                self.assertIsInstance(end, int)
                self.assertTrue(1 <= start <= matching_line <= end <= len(source.splitlines()))
                self.assertEqual(first["text"], "\n".join(source.splitlines()[start - 1 : end]))
                self.assertTrue(math.isfinite(first["score"]))
                self.assertNotIsInstance(first["score"], bool)

    def test_reindex_replaces_changed_and_deleted_passages_across_processes(self):
        changed = self.root / "current.md"
        removed = self.root / "retired.txt"
        changed.write_text("The amberchronicle is active.\n", encoding="utf-8")
        removed.write_text("The retiredchronicle is archived.\n", encoding="utf-8")
        self.cli("index", self.root, "--db", self.db)
        self.assertEqual(self.cli("search", "amberchronicle", "--db", self.db)[0]["path"], "current.md")
        self.assertEqual(self.cli("search", "retiredchronicle", "--db", self.db)[0]["path"], "retired.txt")

        changed.write_text("The jadechronicle is active.\n", encoding="utf-8")
        removed.unlink()
        self.assertEqual(self.cli("index", self.root, "--db", self.db)["files"], 1)
        self.assertEqual(self.cli("search", "amberchronicle", "--db", self.db), [])
        self.assertEqual(self.cli("search", "retiredchronicle", "--db", self.db), [])
        current = self.cli("search", "jadechronicle", "--db", self.db)
        self.assertEqual(current[0]["path"], "current.md")
        self.assertEqual(current[0]["text"], "The jadechronicle is active.")
        self.assertEqual(current[0]["revision"], "sha256:" + hashlib.sha256(changed.read_bytes()).hexdigest())

    def test_root_confinement_and_useful_missing_or_malformed_index_errors(self):
        outside = self.work / "outside"
        outside.mkdir()
        (outside / "private.md").write_text("Outside-only secretmarker.\n", encoding="utf-8")
        (self.root / "inside.md").write_text("Inside-only publicmarker.\n", encoding="utf-8")
        (self.root / "linked.md").symlink_to(outside / "private.md")
        self.assertEqual(self.cli("index", self.root, "--db", self.db)["files"], 1)
        self.assertEqual(self.cli("search", "secretmarker", "--db", self.db), [])
        self.assertEqual(self.cli("search", "publicmarker", "--db", self.db)[0]["path"], "inside.md")

        for db in (self.work / "missing.sqlite", self.work / "corrupt.sqlite"):
            with self.subTest(db=db.name):
                if db.name == "corrupt.sqlite":
                    db.write_bytes(b"not a SQLite index")
                error = self.cli("search", "publicmarker", "--db", db, expected_success=False)
                self.assertRegex(error, r"index|database|db")

    def test_evaluator_scores_controlled_qrels_and_unanswerable_separately(self):
        fixture = self.work / "toy"
        documents = fixture / "documents"
        documents.mkdir(parents=True)
        (documents / "answer.md").write_text("The aetherwidget is available.\n", encoding="utf-8")
        (fixture / "queries.json").write_text(
            json.dumps([
                {"id": "found", "query": "aetherwidget", "relevant_paths": ["answer.md"]},
                {"id": "absent", "query": "nevermentionedword", "relevant_paths": []},
            ]), encoding="utf-8"
        )
        self.assertEqual(self.cli("evaluate", fixture), {
            "query_count": 2,
            "recall_at_10": 1.0,
            "ndcg_at_10": 1.0,
            "unanswerable_count": 1,
            "unanswerable_false_hits": 0,
        })

    def test_frozen_synthetic_corpus_reports_retrieval_quality_and_absence(self):
        report = self.cli("evaluate", FIXTURE)
        self.assertEqual(report["query_count"], 5)
        self.assertEqual(report["unanswerable_count"], 1)
        self.assertEqual(report["unanswerable_false_hits"], 0)
        self.assertGreaterEqual(report["recall_at_10"], 0.75)
        self.assertGreaterEqual(report["ndcg_at_10"], 0.75)
        self.assertLessEqual(report["recall_at_10"], 1.0)
        self.assertLessEqual(report["ndcg_at_10"], 1.0)


if __name__ == "__main__":
    unittest.main()
