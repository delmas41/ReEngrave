"""ROADMAP 2.240 step 3 -- the later stages read the page owner (benchmarks/page-ledger-2026-10/FINDINGS.md "step 3")."""
import ast
import pathlib
import unittest

from tools.omr.staged import page_owner as PO
from tools.omr.staged.record import ABSTAIN

SRC = pathlib.Path(PO.__file__)


class AbstainVocabulary(unittest.TestCase):
    def test_every_abstain_reason_page_owner_files_is_declared(self):
        """Step 2 r2 filed `owner_box_not_one_head` without declaring it: a gather with OMR_PAGE_OWNER ON raised on the first wide head
        box (Litolff pp. 2,4,6,16). Every literal reason `mark_owner` abstains with, and the span abstention, must be in ABSTAIN."""
        tree = ast.parse(SRC.read_text())
        words = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "out" and node.args \
                    and isinstance(node.args[0], ast.Constant) and node.args[0].value == "abstain":
                words.add(node.args[2].value)
            if isinstance(node, ast.Call) and getattr(node.func, "attr", None) == "abstain":
                for kw in node.keywords:
                    if kw.arg == "reason" and isinstance(kw.value, ast.Constant):
                        words.add(kw.value.value)
        self.assertIn("owner_box_not_one_head", words)
        self.assertTrue(words)
        missing = sorted(w for w in words if w not in ABSTAIN.all())
        self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()
