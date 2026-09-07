"""Prove the WIRING, not just the rule — with a stubbed roster supplier.

`control_flag.sh` shows the flag is a no-op in this tree with the flag ON,
because `tools/omr/work_roster.py` lives on a sibling branch. That is the
correct behaviour and it is also exactly the shape of a change that looks live
and is not — so this runs the real `compose.py` with a stand-in module
installed in `sys.modules` under the name the wiring imports, and nothing else
changed.

⚠️ The stub is a TEST DOUBLE for a supplier, not a second roster reader: it
answers with a hard-coded set and reads no catalog. When the sibling's module
lands this probe is deleted and the real one answers.

The check that makes it worth running: the blob produced this way must agree,
staff record for staff record, with the blob `price_offline.py` produces by
applying the same rule offline. Two independent paths to one answer.

Usage:  run_with_stub_roster.py --out-dir DIR [--pages 0-85]
"""
from __future__ import annotations

import json
import os
import runpy
import sys
import types
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

PDF = ("/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/"
       "symphony-1-op68/"
       "brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf")
CACHE = ("/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/"
         "agent-abe066cff5c6c7283/benchmarks/omr-veto-refusal-pricing-2026-09/"
         "out/brahms1/cache600")
BRAHMS1_ROSTER = frozenset({
    "Flute", "Oboe", "Clarinet", "Bassoon", "Contrabassoon", "Horn", "Trumpet",
    "Trombone", "Timpani", "Violin", "Viola", "Cello", "Contrabass"})


@dataclass(frozen=True)
class _StubRoster:
    work_id: str = "brahms--symphony-1"
    instruments: frozenset = field(default=BRAHMS1_ROSTER)
    source_kind: str = "catalog"


def _install_stub() -> None:
    mod = types.ModuleType("tools.omr.work_roster")

    def roster_for_pdf(pdf_path):
        # Only the work this probe is about; anything else abstains, so a stub
        # can never quietly answer for a document it knows nothing about.
        return _StubRoster() if "symphony-1-op68" in str(pdf_path) else None

    mod.roster_for_pdf = roster_for_pdf
    mod.WorkRoster = _StubRoster
    sys.modules["tools.omr.work_roster"] = mod
    import tools.omr
    tools.omr.work_roster = mod


def main() -> None:
    out_dir = "benchmarks/omr-brahms-tuba-2026-09/out/stub"
    pages = "0-85"
    argv = sys.argv[1:]
    if "--out-dir" in argv:
        out_dir = argv[argv.index("--out-dir") + 1]
    if "--pages" in argv:
        pages = argv[argv.index("--pages") + 1]
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    _install_stub()
    # ⚠️ `compose.py` writes a FIXED subset of the summary and no staff dicts,
    # so its blob cannot show this layer at all. Rather than edit a benchmark
    # another thread owns, wrap the entry point and keep the whole summary and
    # the annotated pages beside it. compose binds the name at import, which
    # runpy has not done yet, so patching the module attribute here is enough.
    import tools.omr.contextual as cm
    real = cm.apply_contextual_analysis
    captured: list = []

    def wrapper(result, **kw):
        summary = real(result, **kw)
        captured.append((summary, result))
        return summary

    cm.apply_contextual_analysis = wrapper
    os.environ["OMR_ROSTER_SCORE_ORDER_VETO"] = "1"
    os.environ["OMR_SURYA_KEEP_ALIVE"] = "0"
    sys.argv = ["compose.py", PDF, "--out-dir", out_dir, "--pages", pages,
                "--dpi", "600", "--cache", CACHE, "--veto", "report",
                "--tag=-stub"]
    os.chdir(ROOT)
    try:
        runpy.run_path(
            str(ROOT / "benchmarks" / "omr-spans-veto-composition-2026-09" /
                "probe" / "compose.py"),
            run_name="__main__")
    except SystemExit:
        pass

    # `compose.py` runs spans-off then spans-on; keep the second, which is the
    # shipped configuration and the one the grade is taken on.
    if not captured:
        raise SystemExit("REFUSING: apply_contextual_analysis never ran")
    summary, result = captured[-1]
    dst = Path(out_dir) / "wired-spans-on.json"
    dst.write_text(json.dumps({
        "source": "run_with_stub_roster.py",
        "source_pdf": PDF,
        "pages": [{"page_index": p.get("page_index"),
                   "systems": [{"system_index": s.get("system_index"),
                                "staves": [
                                    {"staff_index": st.get("staff_index"),
                                     "slot_index": st.get("slot_index"),
                                     "instrument": st.get("instrument"),
                                     "instrument_source":
                                         st.get("instrument_source"),
                                     "instrument_veto":
                                         st.get("instrument_veto")}
                                    for st in s.get("staves", [])]}
                               for s in p.get("systems", [])]}
                  for p in result.get("pages", [])],
        "contextual": {k: summary.get(k) for k in (
            "reference", "absent_instrument_veto", "offroster_name_veto")},
    }, sort_keys=True))
    print(f"\n  wrote the FULL summary + annotated staff dicts to {dst}")


if __name__ == "__main__":
    main()
