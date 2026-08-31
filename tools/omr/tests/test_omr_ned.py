"""OMR-NED bridge: the CSV contract, and that edits land in the right category.

Two tiers on purpose. The parsing tests run anywhere, because `_omrned_worker`
imports musicdiff and music21 lazily inside functions and so is importable on
the host's 3.9. The scoring tests need `.venv-omrned` and skip without it, so a
machine that has never bootstrapped the venv still gets a green suite.
"""
from __future__ import annotations

import pytest

from tools.omr import _omrned_worker as worker
from tools.omr import omr_ned


# ── the CSV contract ────────────────────────────────────────────────────────

# musicdiff writes header / rows / "Total:" / THE HEADER AGAIN. Cells are
# joined on ", " with no quoting. Trimmed to five categories; the real file has
# forty-odd, but the shape under test is the shape that broke.
HEADER = (", gtpath, predpath, wrong note OMR-ED, "
          "wrong note % contribution to OMR-NED, wrong clef OMR-ED, "
          "wrong clef % contribution to OMR-NED, gt numsyms, pred numsyms, "
          "total numsyms (in both scores), OMR-ED (OMR Edit Distance), "
          "OMR-NED (OMR-ED / total numsyms)")
ROW = ", /t/gt/a.musicxml, /t/pred/a.musicxml, 4, 66.7, 2, 33.3, 72, 72, 144, 6, 0.041666"
TOTAL = "Total:, , , 4, 66.7, 2, 33.3, 72, 72, 144, 6, 0.041666"


def write_csv(tmp_path, body):
    path = tmp_path / "output.csv"
    path.write_text("\n".join(body) + "\n")
    return path


def test_parses_row_and_total(tmp_path):
    rows, total = worker._parse_csv(write_csv(tmp_path, [HEADER, ROW, TOTAL, HEADER]))

    assert len(rows) == 1
    row = rows[0]
    assert row["omr_ed"] == 6
    assert row["truth_symbols"] == 72
    assert row["pred_symbols"] == 72
    assert row["omr_ned"] == pytest.approx(0.041666)
    assert row["categories"] == {"wrong note": 4, "wrong clef": 2}
    assert total["omr_ed"] == 6


def test_repeated_header_footer_is_not_a_row(tmp_path):
    """The footer's first cell is EMPTY, so a `cells[0] == 'gtpath'` guard misses
    it and the header gets parsed as data — which is exactly how this broke."""
    rows, _ = worker._parse_csv(write_csv(tmp_path, [HEADER, ROW, TOTAL, HEADER]))
    assert len(rows) == 1
    assert all("gtpath" not in str(r.get("truth_staged", "")) for r in rows)


def test_zero_categories_are_dropped(tmp_path):
    """Forty zero-count categories per row is noise; only real edits are kept."""
    clean = ", /t/gt/a.musicxml, /t/pred/a.musicxml, 0, 0., 0, 0., 72, 72, 144, 0, 0.0"
    rows, _ = worker._parse_csv(write_csv(tmp_path, [HEADER, clean, HEADER]))
    assert rows[0]["categories"] == {}
    assert rows[0]["omr_ned"] == 0.0


def test_empty_csv_is_not_a_crash(tmp_path):
    assert worker._parse_csv(write_csv(tmp_path, [])) == ([], {})


def test_safe_stem_removes_the_comma_that_would_shift_columns():
    # musicdiff never quotes, so a comma in a staged name silently shifts every
    # column right and every number after it is read off the wrong header.
    assert "," not in worker._safe_stem("Mahler, Symphony 5")
    assert worker._safe_stem("beethoven-sym5_mvt1") == "beethoven-sym5_mvt1"
    assert worker._safe_stem("///") == "score"


# ── scoring, when the venv exists ───────────────────────────────────────────

needs_venv = pytest.mark.skipif(
    not omr_ned.available(),
    reason="no musicdiff venv; run `python3 -m tools.omr.omr_ned --bootstrap`",
)


@pytest.fixture(scope="module")
def scores(tmp_path_factory):
    """Two parts, four bars, and three predictions differing in ONE known way."""
    m21 = pytest.importorskip("music21")
    from music21 import clef, key, meter, note, stream

    def build(*, bass_clef=True, wrong_pitch=False, bars=4):
        score = m21.stream.Score()
        specs = [(["C4", "E4", "G4", "E4"], clef.TrebleClef()),
                 (["C3", "G2", "C3", "E3"],
                  clef.BassClef() if bass_clef else clef.TrebleClef())]
        for pitches, staff_clef in specs:
            part = stream.Part()
            for i in range(bars):
                measure = stream.Measure(number=i + 1)
                if i == 0:
                    measure.append(staff_clef)
                    measure.append(meter.TimeSignature("4/4"))
                    measure.append(key.KeySignature(0))
                for pitch in pitches:
                    measure.append(note.Note(pitch, quarterLength=1.0))
                part.append(measure)
            score.append(part)
        if wrong_pitch:
            score.parts[0].recurse().notes[0].pitch.nameWithOctave = "D4"
        return score

    out = tmp_path_factory.mktemp("omrned")
    paths = {}
    for name, kwargs in (("truth", {}),
                         ("identical", {}),
                         ("clef", {"bass_clef": False}),
                         ("pitch", {"wrong_pitch": True}),
                         # A longer pair carrying the SAME single clef error, so
                         # pooling and averaging give different answers.
                         ("truth_long", {"bars": 24}),
                         ("clef_long", {"bass_clef": False, "bars": 24})):
        path = out / f"{name}.musicxml"
        build(**kwargs).write("musicxml", fp=str(path))
        paths[name] = path
    return paths


@needs_venv
def test_identical_scores_zero(scores):
    result = omr_ned.score_pair(pred=scores["identical"], truth=scores["truth"])
    assert result["omr_ned"] == 0.0
    assert result["omr_ed"] == 0
    assert result["categories"] == {}


@needs_venv
def test_wrong_clef_is_charged_to_the_clef(scores):
    """The project's signature failure — a bass staff read as treble — has to
    show up as a clef error and not be absorbed into the note count, or the
    breakdown is useless for the thing it was adopted to measure."""
    result = omr_ned.score_pair(pred=scores["clef"], truth=scores["truth"])
    assert result["categories"] == {"wrong clef": 2}
    assert result["omr_ned"] > 0


@needs_venv
def test_wrong_pitch_is_charged_to_the_note(scores):
    result = omr_ned.score_pair(pred=scores["pitch"], truth=scores["truth"])
    assert set(result["categories"]) == {"wrong note"}


@needs_venv
def test_score_is_symmetric_but_arguments_are_keyword_only(scores):
    """OMR-NED sums both sides, so a swap does NOT change the number — which is
    why the API refuses positional arguments rather than trusting call sites."""
    forward = omr_ned.score_pair(pred=scores["clef"], truth=scores["truth"])
    backward = omr_ned.score_pair(pred=scores["truth"], truth=scores["clef"])
    assert forward["omr_ned"] == pytest.approx(backward["omr_ned"])

    with pytest.raises(TypeError):
        omr_ned.score_pair(scores["clef"], scores["truth"])  # type: ignore[misc]


@needs_venv
def test_batch_pools_rather_than_averages(scores):
    """The corpus score is one edit-sum over one symbol-sum, the way the Sheet
    Music Benchmark defines it — not the mean of the per-work scores."""
    # Same single clef error in both, but one score is six times longer, so a
    # mean over the pair and a pooled ratio cannot coincide.
    result = omr_ned.score_batch([
        ("short", scores["clef"], scores["truth"]),
        ("long", scores["clef_long"], scores["truth_long"]),
    ])
    assert result["n_scored"] == 2
    pooled = result["overall_omr_ed"] / (
        result["overall_pred_symbols"] + result["overall_truth_symbols"])
    assert result["overall_omr_ned"] == pytest.approx(pooled)

    by_name = {p["name"]: p for p in result["pairs"]}
    assert by_name["long"]["truth_symbols"] > by_name["short"]["truth_symbols"]
    # The denser score dominates: pooling sits nearer its (lower) score than the
    # unweighted mean does.
    mean = sum(p["omr_ned"] for p in result["pairs"]) / 2
    assert result["overall_omr_ned"] < mean
    assert result["overall_omr_ned"] > by_name["long"]["omr_ned"]

    # Every requested pair comes back under the caller's own name, even though
    # musicdiff sorts its CSV by score rather than by input order.
    assert set(by_name) == {"short", "long"}


@needs_venv
def test_missing_file_is_a_clear_error(scores, tmp_path):
    with pytest.raises(omr_ned.OmrNedError):
        omr_ned.score_pair(pred=tmp_path / "nope.musicxml", truth=scores["truth"])
