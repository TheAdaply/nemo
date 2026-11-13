"""Executable public-CLI contract for issue #3: canonical source IDs, revisions and metadata.

The tenant in these fixtures is a synthetic scope label. It is not authentication.
"""

import hashlib
import json
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
FIXTURE = REPO / "fixtures" / "synthetic-sources"
HARBOR = "notion:synthetic-acme:page-harbor-001"
ORBIT = "notion:synthetic-acme:page-orbit-002"
SLACK = "slack:synthetic-acme:C100SYNTH%2F1757000000.000100"
SOURCE_KEYS = {
    "id", "provider", "native_id", "tenant", "title", "author", "created_at",
    "uri", "visibility", "revision",
}


class SourceContractCLITest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.root = self.work / "documents"
        shutil.copytree(FIXTURE / "documents", self.root)
        self.manifest = self.work / "sources.json"
        shutil.copy(FIXTURE / "sources.json", self.manifest)
        self.db = self.work / "index.sqlite"

    def run_cli(self, *args):
        return subprocess.run(
            [sys.executable, "-m", "nemo_memory", *map(str, args), "--json"],
            cwd=REPO, text=True, capture_output=True, timeout=20, check=False,
        )

    def cli(self, *args):
        result = self.run_cli(*args)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def cli_error(self, *args):
        result = self.run_cli(*args)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        return result.stderr.lower()

    def index(self):
        return self.cli("index", self.root, "--db", self.db, "--sources", self.manifest)

    def search(self, query):
        return self.cli("search", query, "--db", self.db)

    def records(self):
        return json.loads(self.manifest.read_text(encoding="utf-8"))

    def write_records(self, records):
        self.manifest.write_text(json.dumps(records), encoding="utf-8")

    def test_identically_titled_documents_keep_distinct_ids_and_metadata(self):
        self.assertEqual(self.index(), {"files": 3, "passages": 7})
        hits = self.search('"Launch plan"')
        by_id = {hit["source"]["id"]: hit for hit in hits}
        self.assertEqual(set(by_id), {HARBOR, ORBIT})
        self.assertEqual({hit["source"]["title"] for hit in hits}, {"Launch plan"})

        harbor = by_id[HARBOR]
        raw = (self.root / "notion" / "harbor-launch.md").read_bytes()
        self.assertEqual(harbor["source"], {
            "id": HARBOR,
            "provider": "notion",
            "native_id": "page-harbor-001",
            "tenant": "synthetic-acme",
            "title": "Launch plan",
            "author": "Mara Vale",
            "created_at": "2026-09-01T09:30:00+00:00",
            "uri": "https://notion.example/synthetic-acme/page-harbor-001",
            "visibility": "notion:synthetic-acme/teamspace/harbor",
            "revision": "sha256:" + hashlib.sha256(raw).hexdigest(),
        })
        # the passage cites an inclusive line span of exactly that revision
        self.assertEqual(harbor["revision"], harbor["source"]["revision"])
        lines = raw.decode("utf-8").splitlines()
        self.assertEqual(harbor["text"], "\n".join(lines[harbor["start_line"] - 1:harbor["end_line"]]))
        self.assertEqual(by_id[ORBIT]["source"]["author"], "Ivo Renn")
        self.assertEqual(by_id[ORBIT]["source"]["native_id"], "page-orbit-002")

    def test_absent_uri_and_visibility_are_explicit_nulls_not_guesses(self):
        self.index()
        hit = self.search("lighthouse")[0]
        self.assertEqual(set(hit["source"]), SOURCE_KEYS)
        self.assertEqual(hit["source"]["id"], SLACK)
        self.assertEqual(hit["source"]["native_id"], "C100SYNTH/1757000000.000100")
        self.assertIsNone(hit["source"]["uri"])
        self.assertIsNone(hit["source"]["visibility"])
        self.assertEqual(hit["source"]["created_at"], "2026-09-04T16:13:20+00:00")

    def test_reimporting_identical_sources_is_idempotent(self):
        first_index = self.index()
        first_hits = [self.search(query) for query in ('"Launch plan"', "lighthouse", "tidewater")]
        self.assertEqual(self.index(), first_index)
        self.assertEqual(
            [self.search(query) for query in ('"Launch plan"', "lighthouse", "tidewater")],
            first_hits,
        )

    def test_revised_source_keeps_its_id_and_the_old_citation_stops_resolving(self):
        self.index()
        old = self.search("tidewater")[0]
        self.assertEqual(old["source"]["id"], HARBOR)

        # The provider-native page is revised and its export lands at a new path.
        (self.root / "notion" / "harbor-launch.md").unlink()
        revised = self.root / "notion" / "harbor-launch-v2.md"
        revised.write_text(
            "# Launch plan\nThe harbor crew ships the saltmarsh release on Monday.\n", encoding="utf-8"
        )
        records = self.records()
        records[0]["path"] = "notion/harbor-launch-v2.md"
        self.write_records(records)
        self.assertEqual(self.index(), {"files": 3, "passages": 6})

        self.assertEqual(self.search("tidewater"), [])
        new = self.search("saltmarsh")[0]
        self.assertEqual(new["source"]["id"], HARBOR)
        self.assertEqual(new["revision"], "sha256:" + hashlib.sha256(revised.read_bytes()).hexdigest())
        self.assertNotEqual(new["revision"], old["revision"])
        # no hit of any query may still cite the replaced revision
        for query in ('"Launch plan"', "harbor", "checklist", "Mara"):
            for hit in self.search(query):
                self.assertNotEqual(hit["revision"], old["revision"], query)
        self.assertEqual(
            {hit["source"]["id"] for hit in self.search('"Launch plan"')}, {HARBOR, ORBIT}
        )

    def test_source_dropped_from_manifest_is_no_longer_returned(self):
        self.index()
        self.assertTrue(self.search("starlane"))
        self.write_records([record for record in self.records() if record["native_id"] != "page-orbit-002"])
        self.assertEqual(self.index(), {"files": 2, "passages": 4})
        self.assertEqual(self.search("starlane"), [])
        self.assertEqual({hit["source"]["id"] for hit in self.search('"Launch plan"')}, {HARBOR})

    def test_only_manifest_listed_files_are_indexed(self):
        (self.root / "unlisted.md").write_text("The unlistedmarker memo is private.\n", encoding="utf-8")
        self.assertEqual(self.index()["files"], 3)
        self.assertEqual(self.search("unlistedmarker"), [])

    def test_invalid_manifest_is_rejected_and_the_previous_index_survives(self):
        self.index()
        good = self.records()

        def changed(index, **fields):
            records = json.loads(json.dumps(good))
            for key, value in fields.items():
                if value is None:
                    del records[index][key]
                else:
                    records[index][key] = value
            return records

        cases = {
            "duplicate id": changed(1, native_id="page-harbor-001"),
            "missing provider": changed(0, provider=None),
            "missing native id": changed(0, native_id=None),
            "missing tenant": changed(0, tenant=None),
            "missing title": changed(0, title=None),
            "empty tenant": changed(0, tenant=" "),
            "path outside root": changed(0, path="../sources.json"),
            "absolute path": changed(0, path=str(self.manifest)),
            "missing file": changed(0, path="notion/absent.md"),
            "naive time": changed(0, created_at="2026-09-01T09:30:00"),
            "not a time": changed(0, created_at="last Tuesday"),
            "uri without scheme": changed(0, uri="notion.example/page"),
            "unknown field": changed(0, principal="mara"),
            "not a list": {"sources": good},
        }
        for name, records in cases.items():
            with self.subTest(case=name):
                self.write_records(records)
                error = self.cli_error("index", self.root, "--db", self.db, "--sources", self.manifest)
                self.assertRegex(error, r"source|manifest")
                # the failed import must not have replaced the earlier index
                self.assertEqual(self.search("tidewater")[0]["source"]["id"], HARBOR)
                self.assertEqual(self.search("starlane")[0]["source"]["id"], ORBIT)

    def test_directory_index_without_manifest_reports_file_sources_without_guessing(self):
        self.assertEqual(self.cli("index", self.root, "--db", self.db), {"files": 3, "passages": 7})
        hit = self.search("lighthouse")[0]
        self.assertIn("source", hit)
        raw = (self.root / "slack" / "retro-reminder.txt").read_bytes()
        self.assertEqual(hit["source"], {
            "id": "file:local:slack%2Fretro-reminder.txt",
            "provider": "file",
            "native_id": "slack/retro-reminder.txt",
            "tenant": "local",
            "title": "retro-reminder.txt",
            "author": None,
            "created_at": None,
            "uri": None,
            "visibility": None,
            "revision": "sha256:" + hashlib.sha256(raw).hexdigest(),
        })
        self.assertEqual(hit["path"], "slack/retro-reminder.txt")

    def test_index_built_before_source_ids_asks_for_a_rebuild_and_can_be_replaced(self):
        # The shape `nemo index` wrote before this contract (schema version 1).
        with closing(sqlite3.connect(self.db)) as connection, connection:
            connection.execute("CREATE TABLE metadata (root TEXT NOT NULL)")
            connection.execute("INSERT INTO metadata(root) VALUES (?)", (str(self.root.resolve()),))
            connection.execute("CREATE TABLE sources (path TEXT PRIMARY KEY, revision TEXT NOT NULL)")
            connection.execute(
                "CREATE TABLE passages (id INTEGER PRIMARY KEY, path TEXT NOT NULL, "
                "start_line INTEGER NOT NULL, end_line INTEGER NOT NULL, text TEXT NOT NULL)"
            )
            connection.execute(
                "CREATE VIRTUAL TABLE passage_fts USING fts5("
                "text, content='passages', content_rowid='id', tokenize='unicode61')"
            )
            connection.execute("PRAGMA application_id = 0x4E454D4F")
            connection.execute("PRAGMA user_version = 1")
        self.assertIn("rebuild", self.cli_error("search", "lighthouse", "--db", self.db))
        self.assertEqual(self.index(), {"files": 3, "passages": 7})
        self.assertEqual(self.search("lighthouse")[0]["source"]["id"], SLACK)


if __name__ == "__main__":
    unittest.main()
