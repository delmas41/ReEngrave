"""What a missing, wrong, or right meter actually costs a page.

The question the metric cannot answer on its own: is an unread meter cosmetic —
one `<time>` element — or does it distort the notes?

Beethoven 3 i is the page to ask on, because all three answers happen to it. It
read `6/4` before 2026-09-01 (Bravura's `6` matches a Litolff `3`, on six staves
of twelve); it abstains now, and the exporter falls back to `4/4`; and the work
is a constant 3/4, so the right answer is known.

⚠️ **The three arms differ ONLY in the meter, and getting that right took a
second attempt.** The obvious construction — run the page again with
`--dossier`, which supplies the meter — was run first and is not a control: a
dossier also seeds every staff's clef and key signature, so the arm differs in
the pitches too and its bar checks (270) cannot be attributed to the meter. This
transcribes the page ONCE and then rewrites the meter on the built result before
each export. Same detections, same durations, same clefs; one field changes.

    python3 benchmarks/omr-timesig-2026-09/downstream_cost.py
"""
from __future__ import annotations

import argparse
import copy
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

BENCH = Path(__file__).resolve().parent
REPO = Path(__file__).resolve().parents[2]
OUT = BENCH / "out"
CORPUS = json.loads((BENCH / "corpus.json").read_text())
LIB = Path(CORPUS["library_root"])

CASE = next(c for c in CORPUS["cases"] if c["label"] == "beet3-p1")
PDF = LIB / CASE["pdf"]

#: label -> the meter every staff is given, or None to leave the page as the
#: pipeline built it (which is what the exporter's 4/4 fallback then sees).
ARMS = {
    "as-read": None,
    "wrong-6-4": {"numerator": 6, "denominator": 4, "raw": "6/4"},
    "right-3-4": {"numerator": 3, "denominator": 4, "raw": "3/4"},
    "common-4-4": {"numerator": 4, "denominator": 4, "raw": "4/4"},
}

BARCHECK = re.compile(r"barcheck failed", re.I)


def transcribe_once() -> dict:
    cached = OUT / "beet3_page.json"
    if cached.is_file():
        return json.loads(cached.read_text())
    from tools.omr.transcribe import DEFAULT_WEIGHTS, transcribe
    result = transcribe(pdf_path=PDF, pages=[CASE["page"]], weights=DEFAULT_WEIGHTS)
    OUT.mkdir(exist_ok=True)
    cached.write_text(json.dumps(result, indent=1, default=str))
    return result


def with_meter(result: dict, meter: dict | None) -> dict:
    out = copy.deepcopy(result)
    if meter is None:
        return out
    for page in out["pages"]:
        for system in page["systems"]:
            for staff in system["staves"]:
                staff["time_signature"] = dict(meter)
                for measure in staff["measures"]:
                    measure["time_signature"] = dict(meter)
    return out


def score(label: str, result: dict) -> dict:
    from tools.omr.export import to_lilypond
    OUT.mkdir(exist_ok=True)
    ly = OUT / f"beet3_{label}.ly"
    ly.write_text(to_lilypond(result))
    proc = subprocess.run(["lilypond", "-o", str(OUT / f"beet3_{label}"), str(ly)],
                          capture_output=True, text=True, cwd=OUT)
    log = proc.stdout + proc.stderr
    (OUT / f"beet3_{label}.lilylog").write_text(log)
    page = result["pages"][0]
    meters = sorted({
        str((staff.get("time_signature") or {}).get("raw"))
        for system in page["systems"] for staff in system["staves"]})
    emitted = re.findall(r"\\time (\S+)", ly.read_text())
    return {
        "arm": label,
        "meter_on_staves": meters,
        "time_directives": dict(sorted(
            {m: emitted.count(m) for m in set(emitted)}.items())),
        "barcheck_failures": len(BARCHECK.findall(log)),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--arms", nargs="+", default=list(ARMS))
    args = ap.parse_args()

    base = transcribe_once()
    rows = [score(a, with_meter(base, ARMS[a])) for a in args.arms]
    (BENCH / "downstream_cost.json").write_text(json.dumps(rows, indent=2) + "\n")
    header = "\\time emitted"
    print(f"\n{'arm':<12}{'staff meters':<16}{header:<24}{'barcheck':>9}")
    for r in rows:
        print(f"{r['arm']:<12}{','.join(r['meter_on_staves'])[:14]:<16}"
              f"{str(r['time_directives'])[:22]:<24}{r['barcheck_failures']:>9}")


if __name__ == "__main__":
    main()
