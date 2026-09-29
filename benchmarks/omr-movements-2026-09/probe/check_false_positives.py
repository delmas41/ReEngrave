"""Manager's control (2026-09-28, before merge): run ONLY
adjudicate_movement_start -- never a full re-decision -- over the frozen
GATHER log of each single-movement acceptance record, and report every
system that fires >=1 cue. Run from the repo root, or adjust the
sys.path.insert below."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.omr.staged import record_io
from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401 -- registers movement_start
from tools.omr.staged.record import Log, Q, Subject, DOCUMENT
from tools.library.score_library import library_root

_REPO_ROOT = Path(__file__).resolve().parents[3]
# `library_root()` resolves to the MAIN checkout even from a worktree
# (CLAUDE.md §5a) -- `_REPO_ROOT / "library"` would not exist there.
_LIBRARY = library_root() / "_shared-records"

RECORDS = {
    "brahms1-breitkopf": str(_LIBRARY / "brahms1-breitkopf-mvt1-whole-20260928.record.json"),
    "beethoven5-litolff": str(_LIBRARY / "beethoven5-litolff-mvt1-whole-20260928.record.json"),
    "engraved-p0p2": str(_REPO_ROOT / "benchmarks" / "omr-staged-engraved-2026-09"
                        / "out" / "engraved-p0p2-20260928.record.json"),
}


def build_log(result: dict) -> Log:
    """A fresh Log holding ONLY this record's GATHER rows (observations +
    abstentions) -- movement_start reads GATHER only, so its verdicts (if
    any are already on this record) are irrelevant and never copied in."""
    log = Log()
    rec = result.get("record") or {}
    for o in rec.get("observations") or ():
        sub = Subject.from_key(o["subject"])
        log.observe(sub, o["quantity"], o["value"], reader=o["reader"],
                    frame=o["frame"], score=o.get("score"),
                    **(o.get("detail") or {}))
    for a in rec.get("abstentions") or ():
        sub = Subject.from_key(a["subject"])
        log.abstain(sub, a["quantity"], reader=a["reader"], frame=a["frame"],
                    reason=a["reason"], **(a.get("detail") or {}))
    return log


def main():
    spec = adjudicate.REGISTRY[Q.MOVEMENT_SPANS]
    for name, path in RECORDS.items():
        print(f"\n########## {name} ({path}) ##########")
        result = record_io.load_record(path)
        log = build_log(result)
        log.freeze()
        # ⚠️ ONLY this one decision -- adjudicate_one runs a single spec on
        # a single subject, never the full ORDER.
        verdict = adjudicate.adjudicate_one(log, spec, DOCUMENT)
        print(f"outcome={verdict.outcome} reason={verdict.reason} "
             f"value={verdict.value}")
        cues_by_system = (verdict.detail or {}).get("cues_by_system") or {}
        fired_any = {k: v for k, v in cues_by_system.items()
                    if any(v.values())}
        print(f"systems checked: {len(cues_by_system)}; "
             f"systems firing >=1 cue: {len(fired_any)}")
        for sys_key, cues in sorted(fired_any.items()):
            fired = sorted(k for k, v in cues.items() if v)
            print(f"  {sys_key}: {fired}")
        if verdict.detail.get("boundaries"):
            print("  BOUNDARIES DECIDED:", verdict.detail["boundaries"])


if __name__ == "__main__":
    main()
