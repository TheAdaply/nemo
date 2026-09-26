"""A derived index must not supply text absent from its cited source."""

import sqlite3
import tempfile
import unittest
from pathlib import Path

from nemo_memory.retrieval import index_directory, search_index


class CitationIntegrityTest(unittest.TestCase):
    def test_corrupt_passage_text_cannot_be_cited_as_unchanged_source(self):
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            root = work / "selected"
            root.mkdir()
            source = root / "note.md"
            source.write_text(
                "The amber notebook records approved plans.\n"
                "The violet archive retains the agenda.\n",
                encoding="utf-8",
            )
            db = work / "index.sqlite"
            self.assertEqual(index_directory(str(root), str(db)), {"files": 1, "passages": 2})

            # Change only the derived passage, then make FTS match its fabricated term.
            with sqlite3.connect(db) as connection:
                connection.execute(
                    "UPDATE passages SET text = ? WHERE path = ? AND start_line = ?",
                    ("The fabricatedcobalt notebook records approved plans.", "note.md", 1),
                )
                connection.execute("INSERT INTO passage_fts(passage_fts) VALUES ('rebuild')")

            self.assertEqual(
                search_index("fabricatedcobalt", str(db)),
                [],
                "search cited index text that is absent from the unchanged source line",
            )


if __name__ == "__main__":
    unittest.main()
