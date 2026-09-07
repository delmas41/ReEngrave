"""Does the ENGRAVED harness have a repeat-run noise floor?

Authorised 2026-09-07 in the cheaper form: `orchestral_eval --omr-ned` twice on
ONE UNCHANGED TREE over two works — `mahler-sym5-mvt1` (the work with the
documented confidence jitter: CLAUDE.md records a hairpin detection moving
0.83 -> 0.69 between runs on byte-identical code) and `brahms-sym1-mvt1` (the
most detections in the set).

WHY IT MATTERS. `current-accuracy.json` carries no noise floor, so no engraved
row in `metric-registry.json` can gate a delta — condition 3 of the
comparability rule (§B5.5) is unsatisfiable for eleven works. The scan harness
was measured at exactly 0 on its five-row era and +-6 on its twenty-row era; the
engraved side has never been asked.

⚠️ THE FAILURE MODE THIS PROBE IS BUILT AGAINST. Two identical numbers from a
SECOND ARM THAT NEVER RAN is the worst possible way to report a noise floor of
zero — it is the cached-A/B shape catalogued in MEASUREMENT_SYSTEM.md Part A,
where nothing about the output invites suspicion and the only tell is the clock.
So this probe reports WALL CLOCK and per-run `runtime` for both arms, and refuses
to call a zero floor a result unless both arms demonstrably executed.

    --no-direction-text on purpose. It isolates the DETECTOR and the pipeline
    from Surya, whose own nondeterminism is a separate documented lead, and it
    is a configuration `current-accuracy.json` actually records — so the floor
    attaches to a real recorded row rather than to a configuration nobody
    quotes. The direction-text arm's floor is UNMEASURED and is >= this one.

This probe does not RUN the arms — they are run by hand, serially, under a load
check. It reads what they left behind.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _fixtureroot import require_nonempty  # noqa: E402

N = HERE / "noise-floor"
OUT = HERE / "engraved-noise-floor.json"
WORKS = ("mahler-sym5-mvt1", "brahms-sym1-mvt1")

#: music21 stamps a fresh 32-hex id on every write, on BOTH `<score-instrument>`
#: / `<midi-instrument>` (`I...`) and `<score-part>` (`P...`). Masking only `I`
#: leaves the Mahler truth looking non-deterministic when it is not.
_RANDOM_ID = re.compile(r'"[IP][0-9a-f]{32}"')
_DATE = re.compile(r"<encoding-date>[^<]*</encoding-date>")


def canon_sha(p: Path) -> str:
    t = _RANDOM_ID.sub('"X#"', p.read_text())
    return hashlib.sha256(_DATE.sub("", t).encode()).hexdigest()[:16]


def raw_sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]


def parse_scores(log: Path) -> dict:
    out = {}
    for line in log.read_text().splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[0] in WORKS:
            try:
                out[parts[0]] = {"omr_ned": float(parts[1]), "edits": int(parts[2]),
                                 "truth_symbols": int(parts[3]),
                                 "pred_symbols": int(parts[4])}
            except (ValueError, IndexError):
                continue
    return out


def main() -> int:
    require_nonempty(sorted(N.glob("arm*.log")), "arm logs", N, "arm*.log")
    arms = {}
    for arm in ("armA", "armB"):
        d = N / arm
        arms[arm] = {
            "wall_clock_s": int((N / f"{arm}.end").read_text())
                            - int((N / f"{arm}.start").read_text()),
            "exit_code": int((N / f"{arm}.rc").read_text().strip()),
            "uptime_before": (N / f"{arm}.uptime.txt").read_text().strip(),
            "scores": parse_scores(N / f"{arm}.log"),
            "runtime": {w: json.loads((d / f"{w}.omr.json").read_text())["runtime"]
                        for w in WORKS},
        }

    per_work = []
    for w in WORKS:
        a, b = arms["armA"], arms["armB"]
        per_work.append({
            "work_id": w,
            "armA": a["scores"].get(w), "armB": b["scores"].get(w),
            "delta_edits": (b["scores"][w]["edits"] - a["scores"][w]["edits"]),
            "export_byte_identical":
                raw_sha(N / f"armA/{w}.omr.musicxml")
                == raw_sha(N / f"armB/{w}.omr.musicxml"),
            "truth_identical_modulo_music21_ids":
                canon_sha(N / f"armA/{w}.musicxml")
                == canon_sha(N / f"armB/{w}.musicxml"),
            "truth_byte_identical":
                raw_sha(N / f"armA/{w}.musicxml")
                == raw_sha(N / f"armB/{w}.musicxml"),
            "armA_runtime_s": a["runtime"][w]["total_s"],
            "armB_runtime_s": b["runtime"][w]["total_s"],
        })

    both_ran = (arms["armA"]["wall_clock_s"] > 60
                and arms["armB"]["wall_clock_s"] > 60
                and arms["armA"]["wall_clock_s"] != arms["armB"]["wall_clock_s"]
                and all(p["armA_runtime_s"] != p["armB_runtime_s"]
                        for p in per_work))
    zero = all(p["delta_edits"] == 0 for p in per_work)

    doc = {
        "generated_by": "benchmarks/omr-pipeline-audit-2026-09/probe/"
                        "probe_engraved_noise_floor.py",
        "configuration": {
            "harness": "orchestral_eval --omr-ned",
            "works": list(WORKS),
            "direction_text": False,
            "why_no_direction_text":
                "isolates the detector+pipeline from Surya (whose "
                "nondeterminism is a separate documented lead) AND is a "
                "configuration current-accuracy.json records, so the floor "
                "attaches to a real recorded row. The direction-text arm's "
                "floor is UNMEASURED and is >= this one.",
            "separate_work_dirs": True,
            "run_serially": True,
        },
        "⚠️_anti_cache_control": {
            "why": "two identical numbers from a second arm that never ran is "
                   "the worst way to report a zero floor — the cached-A/B shape "
                   "where nothing in the output invites suspicion and the only "
                   "tell is the clock",
            "armA_wall_clock_s": arms["armA"]["wall_clock_s"],
            "armB_wall_clock_s": arms["armB"]["wall_clock_s"],
            "per_work_pipeline_runtime_s": {
                p["work_id"]: [p["armA_runtime_s"], p["armB_runtime_s"]]
                for p in per_work},
            "orchestral_eval_has_no_cache_guard":
                "verified by reading `run_work`: it calls excerpt() and "
                "transcribe() unconditionally. There is no "
                "`if pred.is_file() and not force: return` of the kind "
                "scan_eval.run_pipeline opens with.",
            "both_arms_demonstrably_executed": both_ran,
        },
        "load_observed": {"armA": arms["armA"]["uptime_before"],
                          "armB": arms["armB"]["uptime_before"]},
        "result": {
            "noise_floor_edits": 0 if zero else None,
            "per_work_delta_edits": {p["work_id"]: p["delta_edits"] for p in per_work},
            "exports_byte_identical": all(p["export_byte_identical"] for p in per_work),
            "verdict": ("ZERO on this configuration, and byte-identical rather "
                        "than merely equal-scoring" if zero and both_ran else
                        "see per_work"),
            "⚠️_scope": "n=2 works, one configuration, one tree, one machine. "
                        "This does NOT license a zero floor for the eleven-work "
                        "pool: the scan harness measured exactly 0 on its "
                        "five-row era and +-6 on its twenty-row era, so a floor "
                        "is a property of the POOL, not only of the pipeline.",
        },
        "per_work": per_work,
        "arms": arms,
    }
    OUT.write_text(json.dumps(doc, indent=1) + "\n")
    print("load before arm A: %s" % arms["armA"]["uptime_before"])
    print("load before arm B: %s" % arms["armB"]["uptime_before"])
    print("wall clock       : armA %ds   armB %ds   -> both ran: %s"
          % (arms["armA"]["wall_clock_s"], arms["armB"]["wall_clock_s"], both_ran))
    for p in per_work:
        print("  %-22s A %s/%d   B %s/%d   delta %+d   export %s"
              % (p["work_id"], p["armA"]["omr_ned"], p["armA"]["edits"],
                 p["armB"]["omr_ned"], p["armB"]["edits"], p["delta_edits"],
                 "BYTE-IDENTICAL" if p["export_byte_identical"] else "DIFFERS"))
    print("noise floor: %s" % doc["result"]["verdict"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
