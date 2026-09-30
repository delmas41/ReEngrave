"""Prove `merge_class_head.py`'s graft is anchored on BASE, not on the fine-tune.

Everything here is synthetic: a tiny fake "YOLO head" (nc=6 classes, no real
weights, no real checkpoint) built as a handful of registered parameters on a
`torch.nn.Module`, saved and reloaded through the exact code path the real
tool uses (`torch.save({"model": ...}, path)` / `torch.load(...)["model"]`).
No path in this file is machine-local; everything lives under pytest's
`tmp_path`.

The bug this guards against (found 2026-09-29, `benchmarks/omr-weights-ab-
2026-09/`): the plain `--ft`/`--base` graft used to start from the FINE-TUNE's
entire state dict and patch only the non-kept classes' `cv3` rows from base —
so `model.22.cv2.*` (box regression), the DFL layer, the backbone/neck, and
even the KEPT classes' own already-correct rows were the fine-tune's, not
base's. A tensor diff of the shipped production graft
(`hollow-graft-shift09-2026-09-04.pt`) against its recorded base and donor
fine-tune confirmed production was built this way (589/595 tensors bit-
identical to the fine-tune). The fix anchors the whole graft on `--base` and
writes only the kept classes' `cv3` rows onto it.

Run: `python3 -m pytest benchmarks/omr-labeling-survey-2026-09/test_merge_class_head.py`
"""
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

import torch
import torch.nn as nn

_BENCH = Path(__file__).resolve().parent


def _load_merge_class_head():
    """Import the script as a module without needing it on sys.path by name
    (the parent directory has hyphens in it, so a plain `import` can't find
    it by dotted path)."""
    spec = importlib.util.spec_from_file_location(
        "merge_class_head", _BENCH / "merge_class_head.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["merge_class_head"] = mod
    spec.loader.exec_module(mod)
    return mod


NC = 6  # tiny synthetic class space
IN_CH = 4  # tiny synthetic feature width
CLS_LAYERS = ["model.22.cv3.0.2", "model.22.cv3.1.2", "model.22.cv3.2.2"]
# One tensor standing in for the shared box-regression branch, one for the
# backbone/neck — neither is per-class, and neither should EVER move.
CV2_KEY = "model.22.cv2.0.2.weight"
BACKBONE_KEY = "model.0.conv.weight"


class FakeYoloHead(nn.Module):
    """A stand-in for `ckpt["model"]`: just enough registered parameters to
    exercise the graft's key set, tagged so a per-class row's origin
    (base vs. fine-tune) is legible from its value alone.

    `tag` is baked into every element: base uses 1000 + class_index,
    the fine-tune uses 2000 + class_index, so `tensor[c].mean()` says
    unambiguously which donor a row came from.
    """

    def __init__(self, tag: float):
        super().__init__()
        for layer in CLS_LAYERS:
            w = torch.zeros(NC, IN_CH, 1, 1)
            b = torch.zeros(NC)
            for c in range(NC):
                w[c] = tag + c
                b[c] = tag + c
            self.register_parameter(
                layer.replace(".", "__") + "__weight", nn.Parameter(w))
            self.register_parameter(
                layer.replace(".", "__") + "__bias", nn.Parameter(b))
        # non-per-class tensors: constant, tagged the same way, but with a
        # single value (no class dimension) so "did this move" is a single
        # bit-exact check.
        self.register_parameter(
            CV2_KEY.replace(".", "__"),
            nn.Parameter(torch.full((IN_CH, IN_CH, 1, 1), tag)))
        self.register_parameter(
            BACKBONE_KEY.replace(".", "__"),
            nn.Parameter(torch.full((3, 3, 3, 3), tag)))

    def state_dict(self, *a, **kw):  # noqa: D401 - match nn.Module's signature
        sd = super().state_dict(*a, **kw)
        # expose the real dotted names the script expects, not the
        # underscore-mangled ones parameter registration required (nn.Module
        # parameter names may not contain ".")
        return {k.replace("__", "."): v for k, v in sd.items()}

    def load_state_dict(self, sd, *a, **kw):
        remangled = {k.replace(".", "__"): v for k, v in sd.items()}
        return super().load_state_dict(remangled, *a, **kw)


def _write_class_names(path: Path) -> list[str]:
    names = [f"class{i}" for i in range(NC)]
    path.write_text(json.dumps(names))
    return names


def _save_ckpt(model: nn.Module, path: Path) -> None:
    torch.save({"model": model}, str(path))


class MergeClassHeadDirectionTest(unittest.TestCase):
    def setUp(self):
        self.mcg = _load_merge_class_head()

    def _fixture(self, tmp_path: Path):
        names_path = tmp_path / "classes.json"
        names = _write_class_names(names_path)
        self.mcg.CLASS_NAMES_JSON = names_path  # no repo/cwd dependency

        base_path = tmp_path / "base.pt"
        ft_path = tmp_path / "ft.pt"
        out_path = tmp_path / "out.pt"
        _save_ckpt(FakeYoloHead(tag=1000.0), base_path)
        _save_ckpt(FakeYoloHead(tag=2000.0), ft_path)

        labels_root = tmp_path / "labels"
        labels_root.mkdir()
        (labels_root / "catalog-versions.txt").write_text("")

        return names, base_path, ft_path, out_path, labels_root

    def _run(self, tmp_path, keep_names):
        names, base_path, ft_path, out_path, labels_root = self._fixture(tmp_path)
        argv = [
            "merge_class_head.py",
            "--ft", str(ft_path),
            "--base", str(base_path),
            "--out", str(out_path),
            "--labels-root", str(labels_root),
            "--keep", *keep_names,
        ]
        old_argv = sys.argv
        sys.argv = argv
        try:
            rc = self.mcg.main()
        finally:
            sys.argv = old_argv
        self.assertEqual(rc, 0)
        out_sd = torch.load(str(out_path), map_location="cpu",
                             weights_only=False)["model"].state_dict()
        return names, out_sd

    def test_kept_class_rows_come_from_the_fine_tune(self, tmp_path=None):
        with tempfile.TemporaryDirectory() as td:
            tmp_path = Path(td)
            keep = ["class1", "class4"]
            names, out_sd = self._run(tmp_path, keep)
            kept_idx = {1, 4}
            for layer in CLS_LAYERS:
                w = out_sd[f"{layer}.weight"]
                b = out_sd[f"{layer}.bias"]
                for c in kept_idx:
                    self.assertTrue(
                        torch.equal(w[c], torch.full((IN_CH, 1, 1), 2000.0 + c)),
                        f"{layer}.weight[{c}] should be the fine-tune's row")
                    self.assertEqual(b[c].item(), 2000.0 + c,
                                      f"{layer}.bias[{c}] should be the fine-tune's")

    def test_non_kept_class_rows_stay_bit_exact_to_base(self):
        with tempfile.TemporaryDirectory() as td:
            tmp_path = Path(td)
            keep = ["class1", "class4"]
            names, out_sd = self._run(tmp_path, keep)
            non_kept = set(range(NC)) - {1, 4}
            for layer in CLS_LAYERS:
                w = out_sd[f"{layer}.weight"]
                b = out_sd[f"{layer}.bias"]
                for c in non_kept:
                    self.assertTrue(
                        torch.equal(w[c], torch.full((IN_CH, 1, 1), 1000.0 + c)),
                        f"{layer}.weight[{c}] should be BASE's row, untouched")
                    self.assertEqual(b[c].item(), 1000.0 + c,
                                      f"{layer}.bias[{c}] should be BASE's")

    def test_box_regression_and_backbone_never_move(self):
        """This is the regression test for the actual bug: before the fix,
        these two tensors (neither is per-class) came out as the FINE-TUNE's
        (tag 2000), because the old code started from `ft`'s whole state
        dict. They must be BASE's (tag 1000) — bit-exact, not merely close."""
        with tempfile.TemporaryDirectory() as td:
            tmp_path = Path(td)
            keep = ["class1", "class4"]
            names, out_sd = self._run(tmp_path, keep)
            self.assertTrue(
                torch.equal(out_sd[CV2_KEY], torch.full((IN_CH, IN_CH, 1, 1), 1000.0)),
                "box-regression head must stay BASE's, not the fine-tune's")
            self.assertTrue(
                torch.equal(out_sd[BACKBONE_KEY], torch.full((3, 3, 3, 3), 1000.0)),
                "backbone/neck must stay BASE's, not the fine-tune's")

    def test_bias_shift_applies_to_the_grafted_row_not_bases(self):
        with tempfile.TemporaryDirectory() as td:
            tmp_path = Path(td)
            names, base_path, ft_path, out_path, labels_root = self._fixture(tmp_path)
            argv = [
                "merge_class_head.py",
                "--ft", str(ft_path),
                "--base", str(base_path),
                "--out", str(out_path),
                "--labels-root", str(labels_root),
                "--keep", "class1",
                "--bias-shift", "0.9",
            ]
            old_argv = sys.argv
            sys.argv = argv
            try:
                rc = self.mcg.main()
            finally:
                sys.argv = old_argv
            self.assertEqual(rc, 0)
            out_sd = torch.load(str(out_path), map_location="cpu",
                                 weights_only=False)["model"].state_dict()
            for layer in CLS_LAYERS:
                b = out_sd[f"{layer}.bias"]
                # grafted-in value (2001.0, the fine-tune's class-1 row) minus
                # the shift — NOT base's class-1 row (1001.0) minus the shift.
                self.assertAlmostEqual(b[1].item(), 2001.0 - 0.9, places=3)


class SelfCheckTest(unittest.TestCase):
    """The graft tool's own SELF-CHECK (2026-09-29) must be able to fail
    (CLAUDE.md rule 7): a file where a NON-head tensor moved is refused."""

    def setUp(self):
        self.mcg = _load_merge_class_head()

    def test_self_check_passes_on_a_correct_graft_and_fails_on_a_drifted_one(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            names = _write_class_names(d / "classes.json")
            base = d / "base.pt"
            _save_ckpt(FakeYoloHead(tag=1000.0), base)
            # correct: identical to base -> passes with no rows grafted
            good = d / "good.pt"
            _save_ckpt(FakeYoloHead(tag=1000.0), good)
            self.assertEqual(self.mcg.verify_graft(good, base, [], names), 0)
            # drifted: the whole model from a different checkpoint -> refused
            bad = d / "bad.pt"
            _save_ckpt(FakeYoloHead(tag=2000.0), bad)
            self.assertEqual(self.mcg.verify_graft(bad, base, [0], names), 3)


if __name__ == "__main__":
    unittest.main()
