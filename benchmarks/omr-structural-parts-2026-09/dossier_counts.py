"""Phase 2 count source: how many players a condensed staff carries, from the WORK.

`OMR_CONDENSED_PARTS` is inert without a count (proved in Phase 1: flag on with
no source is byte-identical on 20/20 rows). The PAGE cannot supply it — settled,
do not retry: the same printed `Viola` is 1 part in Litolff/Simrock/Breitkopf
and 2 in Peters, a label rule is 74/74 on Beethoven/Brahms and +2,181 on
Dvořák, and eleven page-side signals separate the populations no better than
chance. So the count comes from the WORK, which is what Sean actually has when
transcribing a score he can identify.

⚠️ THE RULE IS A RATIO, NOT A COUNT, and that is what makes it survive contact
with three different encoding conventions. A dossier lists PARTS; a page prints
STAVES; the players on one staff is parts ÷ staves FOR THAT INSTRUMENT.

    Beethoven   `Flute 1`, `Flute 2`      2 parts / 1 staff  -> 2   split
    Beethoven   `Violin 1`, `Violin 2`    2 parts / 2 staves -> 1   DO NOT split
    Dvořák      `Oboi I. II.`             1 part  / 1 staff  -> 1   do not split
    Mahler      `Vier Flöten.` ×2         2 parts / 1 staff  -> 2   split

The `Violin` row is why a plain count of same-named parts is wrong and was not
built: Beethoven's two violin parts are two PRINTED STAVES, and a rule that
counted parts alone would split each of them again. The ratio self-corrects it
without a special case, and it reproduces the Dvořák refusal — the row that
killed the label rule — for the same reason: one part over one staff is one.

Both sides are normalised through `instruments.lookup`, the SAME lexicon the
margin reader uses, so `Bb Clarinet`, `Clarinetti I. II. A` and `Drei
Klarinetten in A` all land on Clarinet without a per-work table.

⚠️ ABSTENTION IS THE DEFAULT, and the predicate is per-staff. Phase 1 found
that `staff["instrument_source"]` is a SLOT-level fact that survives
propagation across a mis-joined slot, so it is NOT a claim that a label was
printed on that staff in that system. This module therefore abstains unless the
instrument is one the ratio divides exactly, and reports every abstention with
its reason rather than defaulting to a guess. A rule keyed on label presence
must never REFUSE on silence — 115 of 407 staves print no label at all, by
publisher convention.

⚠️ WHAT THIS ARM IS. Dossiers are generated from the same Gradus MusicXML the
scan benchmark scores against, so a dossier-fed figure is a CEILING / REAL-USE
arm and is never a benchmark figure — the same handling `orchestral_eval` gives
dossier seeding. It is reported separately and labelled, always.

FIXTURE PROVENANCE. 20-row transcriptions from
`.claude/worktrees/reconciliation/benchmarks/omr-scan-e2e-2026-09/fixtures/`,
suffix `.reconciliation.omr.json`. The main checkout's `fixtures/` still holds
the ELEVEN-row era's `.restamp-composed` set.

    python3 benchmarks/omr-structural-parts-2026-09/dossier_counts.py --json dossier-counts.json
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.omr.instruments import lookup  # noqa: E402

DEFAULT_FIXTURES = Path(
    "/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/reconciliation"
    "/benchmarks/omr-scan-e2e-2026-09/fixtures")
SUFFIX = ".reconciliation.omr.json"
DOSSIERS = ROOT / "data/dossiers"
WORKS = ROOT / "benchmarks/omr-scan-e2e-2026-09/works.json"

#: row_id prefix -> dossier id. The scan rows name a work and a movement; the
#: dossier ids are the same minus the edition and page. Bach Brandenburg 3 has
#: NO dossier, which is a coverage fact and is reported, not worked around.
ROW_TO_DOSSIER = {
    "beethoven-sym5-mvt1": "beethoven-sym5-mvt1",
    "brahms-sym1-mvt1": "brahms-sym1-mvt1",
    "dvorak-sym9-mvt1": "dvorak-sym9-mvt1",
    "mahler-sym5-mvt1": "mahler-sym5-mvt1",
}


def dossier_for(row_id: str) -> str | None:
    for prefix, dos in ROW_TO_DOSSIER.items():
        if row_id.startswith(prefix):
            return dos
    return None


def canonical(text: str | None) -> str | None:
    """A printed or encoded name -> the lexicon's canonical instrument name."""
    if not text:
        return None
    m = lookup(text)
    return m.instrument.name if m else None


def parts_by_instrument(dossier: dict) -> tuple[Counter, list[str]]:
    """How many reference PARTS each instrument has. Unmatched names reported."""
    counts: Counter = Counter()
    unmatched: list[str] = []
    for part in dossier.get("parts", []):
        name = canonical(part.get("name"))
        if name:
            counts[name] += 1
        else:
            unmatched.append(part.get("name") or "")
    return counts, unmatched


def staves_by_instrument(system: dict) -> Counter:
    """How many STAVES this system prints for each instrument, as read."""
    counts: Counter = Counter()
    for staff in system.get("staves", []):
        name = canonical(staff.get("instrument"))
        if name:
            counts[name] += 1
    return counts


def counts_for_system(system: dict, parts: Counter) -> list[dict]:
    """Per staff of this system: players, or an abstention with its reason."""
    staves = staves_by_instrument(system)
    out = []
    for i, staff in enumerate(system.get("staves", [])):
        name = canonical(staff.get("instrument"))
        rec = {"position": i, "instrument": name,
               "instrument_source": staff.get("instrument_source")}
        if name is None:
            rec.update(players=1, abstained="staff instrument unreadable")
        elif name not in parts:
            rec.update(players=1, abstained="instrument not in the dossier")
        elif parts[name] % staves[name]:
            rec.update(players=1, parts=parts[name], staves=staves[name],
                       abstained="parts do not divide evenly by staves")
        else:
            rec.update(players=parts[name] // staves[name],
                       parts=parts[name], staves=staves[name], abstained=None)
        out.append(rec)
    return out


# ── scoring against the hand-verified map ───────────────────────────────────

def _deref(rows: dict, row: dict, key: str):
    val = row.get(key)
    if isinstance(val, str) and val.startswith("same-as:"):
        return rows.get(val.split(":", 1)[1].strip(), {}).get(key)
    return val


def oracle_for(rows: dict, rid: str) -> dict[int, list[int]] | None:
    """{system_index: per-staff reference-part count}, from works.json."""
    row = rows[rid]
    staves = _deref(rows, row, "staves")
    if isinstance(staves, list):
        return {-1: [max(1, len(s.get("parts") or [1])) for s in staves]}
    sap = _deref(rows, row, "systems_as_printed")
    if isinstance(sap, dict):
        per = {int(k.split("_")[1]) - 1: [max(1, len(s.get("parts") or [1]))
                                          for s in v]
               for k, v in sap.items()
               if k.startswith("system_") and isinstance(v, list)}
        if per:
            return per
    cond = (row.get("condensation") or {}).get("staves_as_printed")
    if isinstance(cond, list):
        return {-1: [max(1, len(s.get("parts") or [1]))
                     for s in cond if s.get("lines") == 5]}
    return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fixtures", default=str(DEFAULT_FIXTURES))
    ap.add_argument("--json", default=None)
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()
    fixtures = Path(args.fixtures)

    rows_meta = {r["row_id"]: r for r in json.loads(WORKS.read_text())["rows"]}
    report: dict = {}

    print("COVERAGE FIRST\n")
    print(f"{'row':<34} {'dossier':<20} {'staves':>7} {'decided':>8} "
          f"{'abstained':>10} {'split>1':>8}")
    tot = Counter()
    for p in sorted(fixtures.glob(f"*{SUFFIX}")):
        rid = p.name[:-len(SUFFIX)]
        dos_id = dossier_for(rid)
        result = json.loads(p.read_text())
        systems = [s for pg in result.get("pages", [])
                   for s in pg.get("systems", []) if s.get("staves")]
        if dos_id is None:
            n = sum(len(s["staves"]) for s in systems)
            tot["staves"] += n
            tot["no_dossier"] += n
            report[rid] = {"dossier": None, "systems": []}
            print(f"{rid:<34} {'— NONE':<20} {n:>7} {0:>8} {n:>10} {0:>8}")
            continue
        dossier = json.loads((DOSSIERS / f"{dos_id}.json").read_text())
        parts, unmatched = parts_by_instrument(dossier)
        per_system = [counts_for_system(s, parts) for s in systems]
        flat = [r for sysrec in per_system for r in sysrec]
        dec = sum(1 for r in flat if r["abstained"] is None)
        spl = sum(1 for r in flat if r["abstained"] is None and r["players"] > 1)
        tot["staves"] += len(flat)
        tot["decided"] += dec
        tot["split"] += spl
        report[rid] = {"dossier": dos_id, "unmatched_parts": unmatched,
                       "systems": per_system}
        print(f"{rid:<34} {dos_id:<20} {len(flat):>7} {dec:>8} "
              f"{len(flat)-dec:>10} {spl:>8}")

    print(f"\n{'TOTAL':<34} {'':<20} {tot['staves']:>7} {tot['decided']:>8} "
          f"{tot['staves']-tot['decided']:>10} {tot['split']:>8}")
    rows_with = sum(1 for v in report.values() if v["dossier"])
    print(f"\nrows a dossier reaches: {rows_with}/{len(report)}    "
          f"staves decided: {tot['decided']}/{tot['staves']} "
          f"({tot['decided']/max(1,tot['staves']):.3f})")

    # ── accuracy against the hand-verified map, where one exists ──────────
    print("\n\nACCURACY, against works.json's hand-verified map "
          "(the oracle Phase 1 priced)\n")
    print(f"{'row':<34} {'compared':>9} {'exact':>7} {'over':>6} {'under':>6}")
    agree = Counter()
    for rid, rec in sorted(report.items()):
        if not rec["dossier"]:
            continue
        orc = oracle_for(rows_meta, rid)
        if orc is None:
            print(f"{rid:<34} {'— no map':>9}")
            continue
        n = ex = over = under = 0
        for si, sysrec in enumerate(rec["systems"]):
            truth = orc.get(si, orc.get(-1))
            if truth is None:
                continue
            for r in sysrec:
                if r["position"] >= len(truth):
                    continue
                t = truth[r["position"]]
                n += 1
                if r["players"] == t:
                    ex += 1
                elif r["players"] > t:
                    over += 1
                else:
                    under += 1
        agree["n"] += n; agree["ex"] += ex
        agree["over"] += over; agree["under"] += under
        print(f"{rid:<34} {n:>9} {ex:>7} {over:>6} {under:>6}")
    print(f"\n{'TOTAL':<34} {agree['n']:>9} {agree['ex']:>7} "
          f"{agree['over']:>6} {agree['under']:>6}   "
          f"exact {agree['ex']/max(1,agree['n']):.3f}")
    print("\n⚠️ OVER-counting is the harm: it splits a staff the reference "
          "does not,\n   inventing parts that pair with nothing. UNDER-counting "
          "only forgoes a gain.")

    if args.json:
        dest = Path(args.json)
        if not dest.is_absolute():
            dest = Path(__file__).resolve().parent / dest
        dest.write_text(json.dumps(report, indent=2) + "\n")
        print(f"\nwrote {dest}")


if __name__ == "__main__":
    main()
