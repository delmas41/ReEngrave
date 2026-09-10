"""No standing document has a sentence split by an inserted block.

⚠️⚠️ WHY THIS IS A TEST AND NOT A SCRIPT. It began as a throwaway `/tmp` check
run once by hand — which is the same "a habit, not a mechanism" failure this
week has now produced four times, most recently by a sibling session that
verified its own guard by hand in `/tmp` and never committed it. A check that
lives in someone's shell history protects nothing.

THE DEFECT IT CATCHES, measured: CLAUDE.md is edited by anchored string
replacement, and an insertion landed between `The bounded case (\\`stubs()\\`) IS`
and its own `resolved.`, orphaning the tail of a sentence somebody else wrote.
⚠️ `git blame` actively misleads here — it attributes the surviving line to its
original author and cannot attribute the SPLIT, so the tool a reader reaches
for says "not yours".

⚠️ THE FIRST VERSION OF THIS CHECK KEYED ON THE TAIL (`^[a-z]+\\.$`) and was
worthless in the direction that mattered: it matched the one orphan that
happened to be a single lowercase word and would have missed any tail of two
words or a capitalised one — a FALSE NEGATIVE, which is the dangerous
direction when the answer is zero. A sibling session independently sent back
the false-POSITIVE direction (prose resuming after a fenced code block).
Keying on the PRECEDING line fixes both: an orphan is a blank line whose last
non-blank predecessor was cut MID-SENTENCE.
"""

from __future__ import annotations

import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[3]

#: The documents this project keeps current by hand, and therefore edits by
#: anchored replacement. Benchmarks' own FINDINGS are included: they are the
#: files a later session quotes.
DOCS = ["CLAUDE.md", "NOTES.md", "PROJECT_STATUS.md", "PROJECT_BRIEF.md",
        "version_memory.md", "tools/omr/staged/ASSUMPTIONS.md"]

#: A line may legitimately end without sentence punctuation when it is a table
#: row, a heading, a list item, a fence, or already ends in a terminator.
_TERMINAL = re.compile(r'[.!?:;,|>*`)\]"”—-]\s*$')
_STRUCT = re.compile(r'^\s*(\||#{1,6}\s|[-*+]\s|\d+\.\s|```|---|>)')


def orphans(path: pathlib.Path):
    lines = path.read_text().split("\n")
    fence, out = False, []
    for i, line in enumerate(lines):
        if line.strip().startswith("```"):
            fence = not fence
            continue
        if fence or line.strip():
            continue
        j = i - 1
        while j >= 0 and not lines[j].strip():
            j -= 1
        k = i + 1
        while k < len(lines) and not lines[k].strip():
            k += 1
        if j < 0 or k >= len(lines):
            continue
        prev, nxt = lines[j], lines[k]
        if _STRUCT.match(prev) or prev.strip().startswith("```"):
            continue
        if _STRUCT.match(nxt) or nxt.strip().startswith("```"):
            continue
        if not _TERMINAL.search(prev) and re.match(r'^[a-z]', nxt.strip()):
            out.append((j + 1, prev.strip()[-60:], k + 1, nxt.strip()[:60]))
    return out


@pytest.mark.parametrize("rel", DOCS)
def test_no_standing_doc_has_a_split_sentence(rel):
    path = ROOT / rel
    if not path.is_file():
        pytest.skip(f"{rel} not present")
    found = orphans(path)
    assert not found, "\n".join(
        f"{rel}:{a} ends mid-sentence {p!r}\n  -> {rel}:{b} resumes {n!r}"
        for a, p, b, n in found)


class TestTheCheckItselfCanFail:
    """⚠️ A refusal check needs a POSITIVE control or it passes by finding
    nothing, and it needs its known false positive pinned or the next person
    re-widens it. Both here."""

    def test_it_FINDS_the_real_orphan(self, tmp_path):
        f = tmp_path / "a.md"
        f.write_text("the bounded case (`stubs()`) IS\n\nresolved.\n")
        assert len(orphans(f)) == 1

    def test_a_two_word_tail_is_found_too(self, tmp_path):
        """The false-negative the first version had: it keyed on the tail
        being ONE lowercase word."""
        f = tmp_path / "b.md"
        f.write_text("the clause is gone and its absence IS\n\npinned twice.\n")
        assert len(orphans(f)) == 1

    def test_prose_after_a_CODE_FENCE_is_not_an_orphan(self, tmp_path):
        """The false positive a sibling session sent back."""
        f = tmp_path / "c.md"
        f.write_text("text before.\n\n```\ncode\n```\n\nand prose resumes.\n")
        assert orphans(f) == []

    def test_a_normal_paragraph_break_is_not_an_orphan(self, tmp_path):
        f = tmp_path / "d.md"
        f.write_text("A sentence that ends properly.\n\nand another starts.\n")
        assert orphans(f) == []

    def test_a_table_row_is_not_an_orphan(self, tmp_path):
        f = tmp_path / "e.md"
        f.write_text("| a | b |\n\nand prose after the table.\n")
        assert orphans(f) == []
