"""Why does `Bässe` still read as a singer on the Mahler scan?

`instruments.AMBIGUOUS_ALIASES` lists `basse` as ("Bass voice", "Contrabass")
and `score_layouts.resolve_ambiguous_label` exists to settle it by POSITION —
its docstring names this exact case, measured on Beethoven 5's `Basso`. On
Mahler 5 p.2 the run reports `ambiguous_labels_resolved: 0` and the bottom staff
exports as `Bass voice`, so something between the two abstains.

This captures the `LayoutFit` the run actually built and asks it directly what
it proposes, and with what support, at the ordinal the label sits on.

⚠️ The monkeypatch is PROBE-SIDE. It wraps `fit_layouts` to record its return
value and calls straight through; no pipeline behaviour changes and nothing
under `tools/` is edited. Asserting that the captured fit came from the run
being probed — rather than rebuilding one here from remembered inputs — is the
whole point: a fit reconstructed from different inputs would answer a different
question and look identical.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO))

def main() -> int:
    import argparse

    from tools.library.score_library import library_root
    from tools.omr import contextual, score_layouts

    ap = argparse.ArgumentParser()
    ap.add_argument("--reading", required=True,
                    help="a stored .omr.json — the contextual pass re-runs over "
                         "ITS page dicts, so the fit is that run's own")
    ap.add_argument("--pdf", required=True,
                    help="path under library/, or absolute")
    ap.add_argument("--dpi", type=int, default=600)
    args = ap.parse_args()

    stored = Path(args.reading)
    pdf = Path(args.pdf)
    if not pdf.is_absolute():
        pdf = library_root() / pdf

    captured: dict = {}
    real_fit = score_layouts.fit_layouts

    def spy(*a, **kw):
        fit = real_fit(*a, **kw)
        captured["fit"] = fit
        captured["args"] = (a, kw)
        return fit

    contextual.fit_layouts = spy          # contextual imported it by name
    score_layouts.fit_layouts = spy

    from tools.omr.assist import Assist
    summary = contextual.apply_contextual_analysis(
        result=json.loads(stored.read_text()),
        pdf_path=pdf, dpi=args.dpi, dossier=None, assist=Assist("none"))

    fit = captured.get("fit")
    print("captured a fit:", fit is not None)

    # ⚠️ What the fit was HANDED, not what came back. `_ambiguous_label_slots`
    # is supposed to withhold an unsettleable alias so the aligner is not asked
    # to place a voice in an orchestra; if the withholding did not happen, an
    # empty ballot means "voice is unplaceable", and if it did, it means "the
    # DP never reached this ordinal". Those are different bugs with the same
    # symptom, and only the input separates them.
    a, kw = captured.get("args", ((), {}))
    handed = kw.get("labels") or {}
    n_staves = kw.get("n_staves", a[0] if a else None)
    print(f"\nfit_layouts(n_staves={n_staves}) label map, "
          f"{len(handed)} of {n_staves} slots:")
    for slot in range(n_staves or 0):
        mark = "" if slot in handed else "   <-- WITHHELD from the prior"
        print(f"  slot {slot:3d} -> {handed.get(slot)}{mark}")
    print("layout:", summary.get("layout"),
          "named slots:", summary.get("layout_named_slots"))
    print("ambiguous_labels_resolved:", summary.get("ambiguous_labels_resolved"))

    ref = summary.get("reference") or []
    print(f"\nslots: {len(ref)}")
    for s in ref:
        # The serialized slot calls it `slot`; the dataclass calls it `index`.
        idx = (s.get("slot", s.get("index")) if isinstance(s, dict)
               else s.index)
        inst = s.get("instrument") if isinstance(s, dict) else s.instrument
        proposed = fit.instrument_for(idx) if fit else None
        support = fit.support_for(idx) if fit else {}
        top = sorted(support.items(), key=lambda kv: -kv[1])[:3]
        print(f"  slot {idx:3d} instrument={str(inst):16s} "
              f"fit_proposes={str(proposed):14s} support={top}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
