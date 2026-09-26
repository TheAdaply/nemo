"""Indexing must stay within the chosen root when a parent path changes."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from nemo_memory import retrieval


class SymlinkRaceTest(unittest.TestCase):
    def test_parent_symlink_swap_does_not_index_outside_content(self):
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            chosen = work / "chosen"
            docs = chosen / "docs"
            held = chosen / "held"
            outside = work / "outside"
            docs.mkdir(parents=True)
            outside.mkdir()
            (docs / "memo.md").write_text("insideword\n", encoding="utf-8")
            (outside / "memo.md").write_text("secretword\n", encoding="utf-8")
            db = work / "index.sqlite"
            original_open = os.open
            race_triggered = False

            def swap_parent_before_open(path, flags, *args, **kwargs):
                nonlocal race_triggered
                if not race_triggered and Path(path).name == "memo.md":
                    docs.rename(held)
                    docs.symlink_to(outside, target_is_directory=True)
                    race_triggered = True
                return original_open(path, flags, *args, **kwargs)

            try:
                with patch.object(retrieval.os, "open", side_effect=swap_parent_before_open):
                    retrieval.index_directory(str(chosen), str(db))
            finally:
                if docs.is_symlink():
                    docs.unlink()
                if held.exists():
                    held.rename(docs)

            self.assertTrue(race_triggered, "the final memo.md open must trigger the swap")
            self.assertEqual(
                [hit["path"] for hit in retrieval.search_index("insideword", str(db))],
                ["docs/memo.md"],
            )
            self.assertEqual(retrieval.search_index("secretword", str(db)), [])


if __name__ == "__main__":
    unittest.main()
