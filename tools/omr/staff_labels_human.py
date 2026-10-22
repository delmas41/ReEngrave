"""Ask a person about the staves the free readers could not resolve.

The tier that is authoritative rather than merely accurate. Its answers are worth
more than a reader's twice over: they settle the page, and they can be BANKED as
ground truth, which is the binding constraint on measuring anything here — the
whole clef corpus is 69 staves across four pages, and Mahler could not be scored
at all for want of a hand-read page.

## It asks about very little

Not every staff — only the ones a trigger fired on, and every trigger is already
computed by the layer:

* a label was READ and the lexicon could not resolve it (`unresolved_labels`);
* a staff carries no label at all, in a system the readers did not cover.

On Beethoven 5 p.48 that is **one question**, and answering it takes the page from
14 of 17 clefs to 17 of 17 — the same as the paid tier, because the staff in
question heads the trombone block and one label decides three clefs.

## Confirm, don't type

Every question offers the best reading anyone has as the default, so the common
case is pressing return. A human answer PINS, and a careless one pins hard and
silently — the whole point of defaulting to the machine's reading is that a
person correcting is a much rarer event than a person confirming, and rare events
deserve the typing.

Provenance is recorded on every answer: what was proposed, what was given, and
whether it was confirmed or corrected. An answer banked as ground truth should
never be mistaken for one verified against the print.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

from .assist import Assist
from .instruments import lookup
from .staff_labels import StaffLabel
from .staff_labels_vision import build_margin_crop
from .types import PageWithStaves, Staff

logger = logging.getLogger(__name__)

HELP = """
    <return>  accept the reading shown
    <text>    the label as PRINTED, e.g. "Tr. Alt."
    s         skip this staff
    S         skip the rest of this system
    v         hand the rest of the run to vision
    n         stop asking; keep what the free readers found
    ?         this help
"""


def _questions(pws: PageWithStaves, staves: list[Staff],
               have: dict[int, StaffLabel]) -> list[tuple[Staff, str | None, str]]:
    """`(staff, text read, why we are asking)` for the staves worth a question."""
    out = []
    for staff in staves:
        label = have.get(staff.staff_index)
        if label is not None and label.matched:
            continue
        if label is not None and label.text.strip():
            out.append((staff, label.text.strip(),
                        "read, but the lexicon could not resolve it"))
        else:
            out.append((staff, None, "no label read here"))
    return out


def _crop_path(pws: PageWithStaves, staves: list[Staff],
               out_dir: Path, system_index: int) -> Path | None:
    """Write the margin the human should look at, and return where it went."""
    crop = build_margin_crop(pws, staves)
    if crop is None:
        return None
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"margin-system{system_index}.png"
    path.write_bytes(crop.png)
    return path


def read_staff_labels_human(
    pws: PageWithStaves,
    have: list[StaffLabel],
    assist: Assist,
    *,
    out_dir: Path,
    page_index: int = 0,
    stream=None,
    out=None,
) -> list[StaffLabel]:
    """Ask about the unresolved staves; return the labels the answers add.

    Returns only what the human supplied — the caller merges. Switching to
    another mode part-way returns whatever was answered before the switch, and
    `assist.mode` carries the change.
    """
    stream = stream or sys.stdin
    out = out or sys.stderr
    if not (hasattr(stream, "isatty") and stream.isatty()):
        logger.warning("assist mode is 'human' but there is no terminal to ask "
                       "on; the free readers' answer stands for page %s", page_index)
        return []

    by_index = {lab.staff_index: lab for lab in have}
    by_system: dict[int, list[Staff]] = {}
    for staff in sorted(pws.staves, key=lambda s: s.top_y):
        by_system.setdefault(staff.system_index, []).append(staff)

    added: list[StaffLabel] = []
    for system_index, staves in sorted(by_system.items()):
        questions = _questions(pws, staves, by_index)
        if not questions:
            continue
        path = _crop_path(pws, staves, out_dir, system_index)
        print(f"\n  page {page_index}, system {system_index}: "
              f"{len(questions)} staff/staves to settle", file=out)
        if path:
            print(f"  the margin is at {path}", file=out)

        for staff, text, why in questions:
            ordinal = staves.index(staff)
            proposal = text or ""
            shown = f" [{proposal}]" if proposal else ""
            print(f"\n    staff {ordinal} of {len(staves)} — {why}", file=out)
            print(f"    what is printed beside it?{shown} "
                  f"(? for help) ", end="", file=out, flush=True)
            answer = (stream.readline() or "").strip()

            while answer == "?":
                print(HELP, file=out)
                print("    what is printed beside it?"
                      f"{shown} ", end="", file=out, flush=True)
                answer = (stream.readline() or "").strip()

            if answer == "n":
                assist.switch("none", f"stopped asking at page {page_index}")
                return added
            if answer == "v":
                assist.switch("vision", f"handed over at page {page_index}")
                return added
            if answer == "S":
                break
            if answer == "s":
                continue

            given = answer or proposal
            if not given:
                continue
            hit = lookup(given)
            assist.answers.append({
                "page_index": page_index, "system_index": system_index,
                "ordinal": ordinal, "staff_index": staff.staff_index,
                "proposed": text, "given": given,
                "action": "confirmed" if not answer else "corrected",
                "resolves_to": hit.instrument.name if hit else None,
                "source": "human",
            })
            if hit is None:
                print(f"    note: {given!r} still resolves to nothing — kept, but "
                      f"it will not reach the join until an alias exists for it",
                      file=out)
            added.append(StaffLabel(
                staff_index=staff.staff_index, text=given,
                instrument=hit.instrument if hit else None,
                fifths_offset=hit.fifths_offset if hit else 0,
                y_center_px=(staff.top_y + staff.bottom_y) / 2.0,
                confidence=hit.confidence if hit else "none",
                alias=hit.alias if hit else "",
            ))
    return added


def write_ground_truth(assist: Assist, path: Path,
                       extra: dict[str, Any] | None = None) -> Path | None:
    """Bank the human answers in the shape the benchmarks already read.

    This is the reason the human tier is worth building even though the vision
    tier is cheaper: review effort becomes benchmark data. The provenance is kept
    explicit — `source: human`, and whether each was confirmed or corrected — so
    a banked answer is never mistaken for one verified against the print.
    """
    import json

    if not assist.answers:
        return None
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "_about": "Margin labels supplied by a person during a review, with "
                  "provenance. NOT verified against the print unless the "
                  "`action` says corrected and someone looked — a confirmed "
                  "answer is the machine's reading that a human did not object "
                  "to, which is weaker evidence than a hand reading.",
        "assist": assist.summary,
        "answers": assist.answers,
    }
    payload.update(extra or {})
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    return path
