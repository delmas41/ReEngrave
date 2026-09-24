"""ROADMAP 2.9b — the per-staff table, scored against SEAN'S OWN ADJUDICATION.

    python3 .../part_report.py <tag> --truth beethoven5|brahms1|engraved
    python3 .../part_report.py <tag> --truth beethoven5 --page 3   # count page

⚠️⚠️ **THE TRUTH HERE IS A HUMAN'S, NOT A DOSSIER'S.** Sean, 2026-09-23, on
2.9's four system-header crops: *"all 4 of those crops are pieces with 3 flats
and the staffs that have fewer flats are transposing clefs."* Both works are
in C minor, so every non-transposing staff prints **three flats**, a B-flat
clarinet prints **one**, and horn / trumpet / timpani print **none** (`[C81]`).
That is a fact about the PLATE, read off the plate by the one person in the
project who reads these plates — not `data/dossiers/*.json`, which CLAUDE.md
§8 refuses in any measurement path and which is already known wrong about
Brahms' `Pk.`

⚠️ **WHY IT SCORES BY SLOT AND NOT BY MARGIN LABEL.** `report.py` scores a
staff only where its own system printed a label, which on Litolff is 76 of 331
staff-systems. 2.9b's part tier reaches every staff with a decided slot (320 of
331), so a report keyed on the label would be blind to most of what the rule
did. The instrument comes from `Q.SLOT_INDEX`'s own detail (the name the
document-wide reference gives that part) and the TRANSPOSITION from
`resolve_label` over the labels that part carries ANYWHERE — a part is one
instrument with one transposition, and a part whose labelled staves disagree
about the instrument is left UNSCORED rather than guessed at.

⚠️ **AND IT SCORES WHAT THE FILE CARRIES, not only what the verdict says.**
MusicXML carries the last stated key forward, so an abstained staff is not
automatically wrong: it is wrong only if what the part carries INTO that
system is not the true key. The `carried` column is computed the way
`export.py` computes it — the part's runs in document order, a None leaving
the previous value standing — and `--check-carry` compares that column
against the exported file so the reimplementation cannot drift.
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import sys
import xml.etree.ElementTree as ET

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))

from tools.omr.staged.record_io import load_record            # noqa: E402
from tools.omr.key_consensus import (MAY_DIFFER_NOT_A_WITNESS,  # noqa: E402
                                     NO_SIGNATURE_CONVENTION,
                                     resolve_label)

#: The concert key of both scanned movements, and of the engraved fixture's
#: 24 bars. Beethoven 5 mvt 1 and Brahms 1 mvt 1 are both C minor.
CONCERT = -3

#: The engraved fixture is a RENDER of an encoding that gives its trumpets and
#: timpani a signature, so `[C81]` does not describe it and its truth is the
#: file it was rendered from. Kept apart from the two plates rather than
#: folded in: they are different kinds of truth.
ENGRAVED_WRITTEN = {"Horn": 0, "Trumpet": -3, "Timpani": -3, "Clarinet": -1}


def _fields(subject: str):
    p = subject.split("/")
    return int(p[1]), int(p[2]), int(p[3])


def _load(tag_or_path, arm=None):
    path = (HERE / "out" / f"{tag_or_path}-{arm}.json") if arm else tag_or_path
    return load_record(path)["record"]


def read_staves(rec: dict):
    """One row per staff-system: slot, name, offset, verdict, decider."""
    labels = {}
    for o in rec["observations"]:
        if o["quantity"] == "margin_label":
            labels[_fields(o["subject"])] = str(o["value"])
    slots, keys = {}, {}
    for v in rec["verdicts"]:
        if v["quantity"] == "slot_index":
            slots[v["subject"]] = v
        elif v["quantity"] == "key_signature":
            keys[v["subject"]] = v

    # ── the PART's transposition, from the labels it carries ANYWHERE ───────
    by_slot_labels = collections.defaultdict(set)
    names = {}
    for sub, sv in slots.items():
        if sv["outcome"] != "decided" or not isinstance(sv["value"], int):
            continue
        slot = int(sv["value"])
        name = (sv.get("detail") or {}).get("instrument")
        if name and slot not in names:
            names[slot] = str(name)
        text = labels.get(_fields(sub))
        if text:
            by_slot_labels[slot].add(text)
    offsets = {}
    for slot, texts in by_slot_labels.items():
        resolved = {resolve_label(t)[:2] for t in texts
                    if resolve_label(t)[2]}
        resolved = {r for r in resolved if r[0] is not None}
        if len(resolved) == 1:
            offsets[slot] = resolved.pop()

    rows = []
    for sub, kv in keys.items():
        page, system, staff = _fields(sub)
        sv = slots.get(sub)
        slot = (int(sv["value"])
                if sv and sv["outcome"] == "decided"
                and isinstance(sv["value"], int) else None)
        name, offset = offsets.get(slot, (names.get(slot), None))
        rows.append({
            "subject": sub, "page": page, "system": system, "staff": staff,
            "slot": slot, "name": name or names.get(slot), "offset": offset,
            "value": kv.get("value") if kv["outcome"] == "decided" else None,
            "outcome": kv["outcome"], "reason": kv.get("reason"),
            "decider": kv.get("decider"),
            "inferred": bool((kv.get("detail") or {}).get("inferred")),
        })
    rows.sort(key=lambda r: (r["page"], r["system"], r["staff"]))
    return rows


def truth_for(row, kind: str):
    """What the PLATE prints on this staff, or None where we may not say."""
    name, offset = row["name"], row["offset"]
    if name is None:
        return None
    if kind == "engraved":
        return ENGRAVED_WRITTEN.get(name, CONCERT)
    if name in NO_SIGNATURE_CONVENTION:
        return 0
    if name in MAY_DIFFER_NOT_A_WITNESS:
        return None
    if offset is None:
        # ⚠️ A part no label ever named may still be non-transposing, and
        # assuming so is exactly the default `key_consensus` refuses. Only a
        # part whose OWN label was read is scored.
        return None
    return CONCERT + int(offset)


def carried(rows):
    """What the FILE carries on each staff — `export.py`'s own carry rule."""
    out = {}
    last = {}
    for r in rows:
        slot = r["slot"]
        if r["value"] is not None:
            last[slot] = r["value"]
        out[r["subject"]] = last.get(slot)
    return out


def score(rows, kind: str):
    carry = carried(rows)
    tally = collections.Counter()
    for r in rows:
        t = truth_for(r, kind)
        if t is None:
            tally["unscored"] += 1
            continue
        if r["inferred"]:
            tally["inferred_right" if r["value"] == t else "inferred_wrong"] += 1
            continue
        if r["value"] is None:
            tally["abstained"] += 1
            tally["abstained_carries_right" if carry[r["subject"]] == t
                  else "abstained_carries_wrong"] += 1
        elif r["value"] == t:
            tally["right"] += 1
        else:
            tally["wrong"] += 1
    return tally


def parts_opening(rows, kind: str):
    """`(slot, name, first key the file states, truth)` per part."""
    out = {}
    for r in rows:
        if r["slot"] is None or r["slot"] in out or r["value"] is None:
            continue
        out[r["slot"]] = (r["name"], r["value"], truth_for(r, kind))
    return out


def changes_written(rows):
    """Every place the file's `<key>` CHANGES, per part."""
    out = []
    last = {}
    for r in rows:
        if r["value"] is None:
            continue
        slot = r["slot"]
        if slot in last and last[slot] != r["value"]:
            out.append((slot, r["name"], (r["page"], r["system"]),
                        last[slot], r["value"]))
        last[slot] = r["value"]
    return out


def _xml_keys(path):
    root = ET.parse(path).getroot()
    out = []
    for part in root.iter("part"):
        seq = []
        for measure in part.findall("measure"):
            for attrs in measure.findall("attributes"):
                f = attrs.findtext("key/fifths")
                if f is not None:
                    seq.append(int(f))
        out.append(seq)
    return out


def check_carry(rows, xml_path) -> int:
    """⚠️ THE CONTROL FOR THIS SCRIPT'S OWN CARRY, AND IT CAN FAIL.

    Everything above reimplements what `export.py` does with a None key, so
    it is measuring this script until it has been shown to agree with the
    file. Per part, the sequence of DISTINCT `<key>` values the file states
    must equal the sequence the record-derived carry produces.

    ⚠️ ONE PART IS EXPECTED TO DIFFER ON A CONDENSED SCORE and the reason is
    named rather than tolerated: `collapse_slot_index_to_family_block` files
    `condensed_with_slot`, and `export._condensed_double` places the Cello
    slot's runs on the Contrabass part as well — so that part's `<key>`
    sequence is TWO slots interleaved and no per-slot walk can produce it.
    Any OTHER mismatch is this script being wrong.
    """
    by_slot = collections.defaultdict(list)
    for r in rows:
        if r["value"] is None or r["slot"] is None:
            continue
        if not by_slot[r["slot"]] or by_slot[r["slot"]][-1] != r["value"]:
            by_slot[r["slot"]].append(r["value"])
    mine = [by_slot[k] for k in sorted(by_slot)]
    root = ET.parse(xml_path).getroot()
    theirs = []
    for part in root.iter("part"):
        s = []
        for m in part.findall("measure"):
            for a in m.findall("attributes"):
                f = a.findtext("key/fifths")
                if f is not None and (not s or s[-1] != int(f)):
                    s.append(int(f))
        theirs.append(s)
    same = sum(1 for a, b in zip(mine, theirs) if a == b)
    print(f"   CARRY CONTROL: {same} of {len(mine)} parts reproduce the "
          f"file's own `<key>` sequence exactly")
    for i, (a, b) in enumerate(zip(mine, theirs)):
        if a != b:
            print(f"      part {i} DIFFERS: record {len(a)} states, "
                  f"file {len(b)} — condensed doubling?")
    return same


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("tag")
    ap.add_argument("--truth", required=True,
                    choices=["beethoven5", "brahms1", "engraved"])
    ap.add_argument("--page", type=int, default=None,
                    help="print the per-staff table for this pdf page only")
    ap.add_argument("--arms", default="base,arm")
    a = ap.parse_args()

    tables = {}
    for arm in a.arms.split(","):
        rec = _load(a.tag, arm)
        rows = read_staves(rec)
        tables[arm] = rows
        print(f"== {a.tag} [{arm}]  {len(rows)} staff-systems")
        print(f"   reasons {dict(collections.Counter(r['reason'] for r in rows))}")
        print(f"   inferred {sum(1 for r in rows if r['inferred'])}")
        print(f"   score {dict(score(rows, a.truth))}")
        opens = parts_opening(rows, a.truth)
        ok = sum(1 for _n, v, t in opens.values() if t is not None and v == t)
        scored = sum(1 for _n, _v, t in opens.values() if t is not None)
        print(f"   parts opening right: {ok} of {scored} scored "
              f"({len(opens)} parts)")
        for slot in sorted(opens):
            name, v, t = opens[slot]
            mark = "" if t is None or v == t else "  <-- WRONG"
            print(f"      slot {slot:2d} {str(name)[:20]:20s} opens {v:>3} "
                  f"truth {t}{mark}")
        ch = changes_written(rows)
        print(f"   key CHANGES written: {len(ch)}")
        for slot, name, sys_key, was, now in ch[:40]:
            print(f"      slot {slot:2d} {str(name)[:16]:16s} at {sys_key} "
                  f"{was} -> {now}")
        xml = HERE / "out" / f"{a.tag}-{arm}.musicxml"
        if xml.exists():
            text = xml.read_text()
            seqs = _xml_keys(xml)
            n_changes = sum(sum(1 for x, y in zip(s, s[1:]) if x != y)
                            for s in seqs)
            print(f"   file: {text.count('<note>')} <note>, "
                  f"{text.count('<key>')} <key>, {n_changes} key CHANGES")
            check_carry(rows, xml)
        cov = HERE / "out" / f"{a.tag}-{arm}.coverage.json"
        if cov.exists():
            c = json.loads(cov.read_text()).get("status_census") or {}
            print(f"   census balanced={c.get('balanced')} "
                  f"unaccounted={c.get('unaccounted')}")

    if a.page is not None:
        print(f"\n== per-staff table, pdf page {a.page}")
        carries = {arm: carried(rows) for arm, rows in tables.items()}
        arms = list(tables)
        base_rows = {r["subject"]: r for r in tables[arms[0]]}
        for r in tables[arms[-1]]:
            if r["page"] != a.page:
                continue
            b = base_rows.get(r["subject"], {})
            t = truth_for(r, a.truth)
            print(f"  sys{r['system']} staff{r['staff']:2d} "
                  f"{str(r['name'])[:14]:14s} truth={t} | "
                  f"base {str(b.get('value')):>4} {str(b.get('reason'))[:24]:24s}"
                  f" carry {carries[arms[0]].get(r['subject'])} | "
                  f"arm {str(r['value']):>4} {str(r['reason'])[:26]:26s}"
                  f" carry {carries[arms[-1]].get(r['subject'])}"
                  + ("  INFERRED" if r["inferred"] else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
