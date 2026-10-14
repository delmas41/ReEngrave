# ROADMAP 2.107 probe. The BASE arm on one tree: the staged CLI with the letter look patched to a no-op.
import os
"""The BASE arm on THE SAME TREE: `staged` CLI with the 2.107 letter look turned
into a no-op by monkeypatch (no flag exists, CLAUDE.md rule 9). Same args as
the arm's `acceptance_quick` gather."""
import sys
sys.path.insert(0, '.')
import tools.omr.staged.gather as G
G.gather_letter_look = lambda *a, **k: {}
from tools.omr.staged.__main__ import main
sys.exit(main(sys.argv[1:]))
