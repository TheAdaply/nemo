"""A failed first build must not prevent retrying the same selected index."""

import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from nemo_memory import retrieval


class FailedBuildRetryTest(unittest.TestCase):
    def test_retry_after_fts_creation_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            root = work / "selected"
            root.mkdir()
            (root / "note.md").write_text("The amberwidget is ready.\n", encoding="utf-8")
            db = work / "index.sqlite"
            original_connect = sqlite3.connect
            injected = False

            class FailingConnection(sqlite3.Connection):
                def execute(self, sql, *args, **kwargs):
                    nonlocal injected
                    if not injected and sql.startswith("CREATE VIRTUAL TABLE passage_fts"):
                        injected = True
                        raise sqlite3.OperationalError("injected FTS creation failure")
                    return super().execute(sql, *args, **kwargs)

            def connect_with_failure(*args, **kwargs):
                return original_connect(*args, factory=FailingConnection, **kwargs)

            with (
                patch.object(retrieval.sqlite3, "connect", side_effect=connect_with_failure),
                self.assertRaises(retrieval.RetrievalError),
            ):
                retrieval.index_directory(str(root), str(db))

            self.assertTrue(injected, "failure must occur during FTS table creation")
            partial_db_remained = db.exists()
            self.assertEqual(retrieval.index_directory(str(root), str(db)),
                             {"files": 1, "passages": 1})
            hits = retrieval.search_index("amberwidget", str(db))
            self.assertEqual([(hit["path"], hit["start_line"], hit["text"]) for hit in hits],
                             [("note.md", 1, "The amberwidget is ready.")])
            self.assertFalse(partial_db_remained, "failed first build left an unusable DB")


if __name__ == "__main__":
    unittest.main()
