"""The CLI's `--direction-text` must leave the environment its say.

`transcribe()` takes `read_direction_text` as a THREE-state parameter — `True`,
`False`, or `None` meaning "the caller has no opinion, ask
`_direction_text_default()`, which reads `OMR_DIRECTION_TEXT`". The web app
(`backend/modules/local_omr.py`) passes nothing and so has always honoured the
variable; the CLI declared `--direction-text` with
`argparse.BooleanOptionalAction` and `default=True`, which is not the same as
"no opinion" — argparse fills the namespace with an explicit `True`, `main()`
forwards it, and the `None` branch is unreachable from a command line. Someone
running `OMR_DIRECTION_TEXT=0 python3 -m tools.omr.transcribe …` paid for the
OCR anyway and was told nothing.

These tests assert the wiring, not the flag function — `_direction_text_default`
itself is correct and is covered in `test_transcribe_helpers.py`. What was
broken is the one hop between `ap.parse_args` and the gate, so that is what is
measured here: `main()` is driven with a stub in place of `transcribe` and the
kwarg it was handed is read back.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tools.omr import transcribe as T


@pytest.fixture()
def blank_pdf(tmp_path: Path) -> Path:
    """A one-page PDF — `main()` counts pages before it calls anything."""
    fitz = pytest.importorskip("fitz")
    doc = fitz.open()
    doc.new_page()
    path = tmp_path / "blank.pdf"
    doc.save(str(path))
    doc.close()
    return path


@pytest.fixture()
def fake_weights(tmp_path: Path) -> Path:
    """`main()` only checks that an explicit `--weights` path EXISTS.

    Passing one keeps the test off the real 88 MB checkpoint (gitignored, and
    absent in a fresh worktree), so this measures the argparse wiring and not
    whether the machine happens to be provisioned.
    """
    path = tmp_path / "weights.pt"
    path.write_bytes(b"not a real checkpoint")
    return path


def _direction_kwarg(monkeypatch, pdf: Path, weights: Path, tmp_path: Path,
                     extra: list[str]):
    """Run `main()` with `transcribe` stubbed; return `read_direction_text`."""
    seen: dict[str, object] = {}

    def _stub(**kwargs):
        seen.update(kwargs)
        return {"pages": [], "runtime": {}}

    monkeypatch.setattr(T, "transcribe", _stub)
    rc = T.main([str(pdf), "--weights", str(weights), "--quiet",
                 "--out", str(tmp_path / "out.json"), *extra])
    assert rc == 0, "main() bailed before reaching transcribe()"
    assert "read_direction_text" in seen
    return seen["read_direction_text"]


class TestTheCliDefersToTheEnvironment:
    def test_no_flag_expresses_no_opinion(self, monkeypatch, blank_pdf,
                                          fake_weights, tmp_path):
        """The regression. A bare CLI run must forward `None`, not `True`.

        `None` is the only value that reaches `_direction_text_default()`, so
        anything else is the environment variable being silently ignored.
        """
        assert _direction_kwarg(monkeypatch, blank_pdf, fake_weights, tmp_path,
                                []) is None

    def test_the_env_then_decides_and_can_say_off(self, monkeypatch, blank_pdf,
                                                  fake_weights, tmp_path):
        """What the `None` is FOR — the gate's own expression, evaluated here.

        The gate at the reader is
        `_direction_text_default() if read_direction_text is None else …`, so a
        forwarded `None` plus `OMR_DIRECTION_TEXT=0` is a reader that does not
        run. A forwarded `True` would win over the environment instead, which
        is exactly the defect.
        """
        monkeypatch.setenv("OMR_DIRECTION_TEXT", "0")
        passed = _direction_kwarg(monkeypatch, blank_pdf, fake_weights,
                                  tmp_path, [])
        assert (T._direction_text_default() if passed is None else passed) \
            is False

    def test_the_env_default_is_still_on(self, monkeypatch, blank_pdf,
                                         fake_weights, tmp_path):
        """Deferring must not turn the reader OFF — it is on by default."""
        monkeypatch.delenv("OMR_DIRECTION_TEXT", raising=False)
        passed = _direction_kwarg(monkeypatch, blank_pdf, fake_weights,
                                  tmp_path, [])
        assert (T._direction_text_default() if passed is None else passed) \
            is True


class TestAnExplicitFlagStillWins:
    """Deferring by default may not cost the flag its meaning: someone who
    types `--no-direction-text` on a machine with `OMR_DIRECTION_TEXT=1` set
    must still get silence, and vice versa."""

    def test_explicit_on_beats_an_env_that_says_off(self, monkeypatch,
                                                    blank_pdf, fake_weights,
                                                    tmp_path):
        monkeypatch.setenv("OMR_DIRECTION_TEXT", "0")
        assert _direction_kwarg(monkeypatch, blank_pdf, fake_weights, tmp_path,
                                ["--direction-text"]) is True

    def test_explicit_off_beats_an_env_that_says_on(self, monkeypatch,
                                                    blank_pdf, fake_weights,
                                                    tmp_path):
        monkeypatch.setenv("OMR_DIRECTION_TEXT", "1")
        assert _direction_kwarg(monkeypatch, blank_pdf, fake_weights, tmp_path,
                                ["--no-direction-text"]) is False


def test_no_other_cli_flag_shadows_an_env_knob():
    """Anti-drift: the same defect, arriving on a different flag.

    A `BooleanOptionalAction` whose default is not `None` cannot express "the
    caller has no opinion", so any FUTURE tri-state parameter wired to one will
    reproduce this bug exactly. `--direction-text` is the only such action in
    the parser today; this fails if a second appears without a `None` default.
    """
    import argparse

    parser_actions = []

    real_add = argparse.ArgumentParser.add_argument

    def _spy(self, *args, **kwargs):
        if kwargs.get("action") is argparse.BooleanOptionalAction:
            parser_actions.append((args[0], kwargs.get("default", "MISSING")))
        return real_add(self, *args, **kwargs)

    argparse.ArgumentParser.add_argument = _spy
    try:
        with pytest.raises(SystemExit):
            T.main(["--help"])
    finally:
        argparse.ArgumentParser.add_argument = real_add

    assert parser_actions, "no BooleanOptionalAction found — did the spy miss?"
    offenders = [name for name, default in parser_actions if default is not None]
    assert not offenders, (
        f"BooleanOptionalAction flags with a non-None default: {offenders}. "
        "Such a flag always passes an explicit value, so a tri-state gate "
        "behind it can never consult its environment variable."
    )
