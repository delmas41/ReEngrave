"""Guard tests (run: python3 -m pytest benchmarks/omr-test-leakage-2026-10/test_guard.py -q).  Not wired into tools/tests.
Known-bad: the 9 Litolff 984073 idx1 TEST cells found inside v13 by 2.110.  Known-clean: 9 neighbouring TEST cells of the
same page and Brahms p0 hand truth.  A guard that cannot fail proves nothing, so the last test makes it fail on purpose."""
import json, sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).parent))
import leakage_guard as g

HERE = Path(__file__).parent
ROWS = {r["cell_id"]: r for r in json.load(open(g.REPO / "benchmarks/omr-labeling-hollow4-test-litolff-p1-2026-10/cells.json"))}
V13 = "v13-2026-09-03-complete-v7-beet5-bolero"


def cells(sub):
    out = []
    for p in sorted((HERE / "fixtures" / sub).glob("*.png")):
        r = ROWS[p.stem]
        out.append(g.Cell(p.stem, p, (g.edition_key(r["pdf"]), r["page"], r["system_index"], r["staff_index"], r["measure_index"]), "test", r["staff_line_ys_canonical"]))
    return out


@pytest.fixture(scope="module")
def v13():
    return g.load_version(g.MAIN / "data" / "user-labeled", V13)


def test_catches_all_nine(v13):
    r = g.check_leak(cells("leaked9"), v13)
    assert len(r["key"]) == 9 and len(r["near"]) == 9 and len(r["exact"]) >= 1
    assert {t.split("/")[1] for t, _ in r["key"]} == {"beet5-p2-sys0-" + c.split("sys0-")[1] for c in (x.name for x in cells("leaked9"))}


def test_clean_pair_is_zero(v13):
    r = g.check_leak(cells("clean9"), v13)
    assert (len(r["exact"]), len(r["key"]), len(r["near"])) == (0, 0, 0)


def test_brahms_p0_hand_truth_is_clean_against_production():
    hp = json.load(open(g.REPO / "data/hand-truth/pages/imslp317803/0.json"))
    test = [g.Cell(c["id"], None, ("imslp317803", 0, c["system"], c["staff"], c["measure"]), "ts2") for c in hp["cells"] if c["kind"] == "measure"]
    r = g.check_leak(test, g.load_mix("production"), near=False)
    assert not r["key"] and not r["exact"]


def test_refuse_if_leaked_raises(v13):
    with pytest.raises(SystemExit):
        g.refuse_if_leaked(cells("leaked9"), v13)


def test_guard_can_fail_on_clean_pair(v13):
    # control: with the near threshold at zero the clean pair is flagged, so a 0 above is the data, not a dead check
    r = g.check_leak(cells("clean9"), v13, near_threshold=0.0)
    assert r["near"]
