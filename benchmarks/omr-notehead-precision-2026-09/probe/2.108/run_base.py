"""2.108 -- the BASE arm on this tree: the staged CLI with the off-staff reach set
to infinity, so `off_staff_glyph` can never fire and every verdict is what the
tree before the change decided. (One tree for base and arm: the A/B differs only
by this constant.)   python3 .../run_base.py <staged CLI args>"""
import sys

sys.path.insert(0, '.')
from tools.omr.staged import geometry  # noqa: E402

geometry.OFF_STAFF_REACH_SPACES = float('inf')
from tools.omr.staged.__main__ import main  # noqa: E402

sys.exit(main(sys.argv[1:]))
