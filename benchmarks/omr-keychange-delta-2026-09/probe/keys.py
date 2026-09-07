"""Per-part, per-staff key-signature timelines out of a reference encoding.

Stdlib only, same reason `tools/omr/training/musicxml_truth.py` is: this must
run in a worktree with no music21 venv. It reads what that module deliberately
does not — `<key>`, `<transpose>` and `<staves>` — and records enough context
to CLASSIFY a part that stays silent at a key change rather than average it
away.

What a MusicXML key signature actually is, and every part of it that bites:

- `<key>` lives inside `<attributes>`, which may appear at the head of a
  measure OR anywhere inside it. Both are read.
- `<key number="N">` scopes the signature to staff N of a multi-staff part.
  A `<key>` with no `number` applies to EVERY staff of the part. A piano part
  is two staves and one signature; a condensed orchestral part can be two
  staves with two.
- A NON-TRADITIONAL key is spelled `<key-step>`/`<key-alter>` with no
  `<fifths>` at all. It has no position on the circle of fifths, so it has no
  delta; it is recorded as `nontraditional`, never as 0.
- `<transpose>` is per part (or per staff, same `number` convention) and CAN
  CHANGE MID-PART — a horn player switching crooks. Where it does, the written
  delta is NOT the concert delta and the shared-delta identity is broken by
  construction. Recorded so those bars can be named rather than counted as
  failures of the rule.
- `<forward>`/`<backup>` are irrelevant here (we want presence of notes, not
  onsets) but `<note><rest/></note>` vs a sounding note is not: a part resting
  through a key change often prints no signature.
"""
from __future__ import annotations

import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from xml.etree import ElementTree as ET


def read_xml_bytes(path: Path) -> bytes:
    """Follows `musicxml_truth._read_xml_bytes` — .mxl is a zip."""
    if path.suffix.lower() == ".mxl" or zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as zf:
            names = zf.namelist()
            root = None
            if "META-INF/container.xml" in names:
                container = ET.fromstring(zf.read("META-INF/container.xml"))
                for rf in container.iter():
                    if rf.tag.endswith("rootfile") and rf.get("full-path"):
                        root = rf.get("full-path")
                        break
            if root is None or root not in names:
                candidates = [n for n in names
                              if n.lower().endswith((".xml", ".musicxml"))
                              and not n.startswith("META-INF/")]
                if not candidates:
                    raise ValueError(f"{path}: no MusicXML inside the archive")
                root = candidates[0]
            return zf.read(root)
    return path.read_bytes()


def _strip_ns(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _find(el: ET.Element, name: str) -> ET.Element | None:
    for child in el:
        if _strip_ns(child.tag) == name:
            return child
    return None


def _text(el: ET.Element | None) -> str:
    return "" if el is None or el.text is None else el.text.strip()


#: A `<key>` scoped to no staff applies to all of them.
ALL_STAVES = 0


@dataclass
class StaffTimeline:
    """One (part, staff) pair's key signature at every measure ordinal."""

    part_id: str
    part_name: str
    staff: int                       # 1-based; 1 for a single-staff part
    #: ordinal -> fifths, ONLY where a `<key>` element was written there.
    stated: dict[int, int] = field(default_factory=dict)
    #: ordinals carrying a `<key>` with no `<fifths>` (non-traditional).
    nontraditional: set[int] = field(default_factory=set)
    #: ordinals where `<transpose>` was (re)stated, -> (diatonic, chromatic)
    transpose: dict[int, tuple[int, int]] = field(default_factory=dict)
    #: ordinals holding at least one SOUNDING note (not a rest) on this staff.
    sounding: set[int] = field(default_factory=set)
    #: ordinals holding any `<note>` at all on this staff (rests included).
    any_note: set[int] = field(default_factory=set)

    def effective(self, n_measures: int) -> list[int | None]:
        """fifths in effect at each ordinal, carried forward. None = unknown."""
        out: list[int | None] = []
        cur: int | None = None
        for i in range(n_measures):
            if i in self.stated:
                cur = self.stated[i]
            elif i in self.nontraditional:
                cur = None
            out.append(cur)
        return out

    def transpose_at(self, ordinal: int) -> tuple[int, int] | None:
        best = None
        for o, t in self.transpose.items():
            if o <= ordinal and (best is None or o > best):
                best = o
        return self.transpose[best] if best is not None else None


@dataclass
class ScoreKeys:
    path: str
    n_measures: int
    staves: list[StaffTimeline]
    #: measure `number` attribute per ordinal, as printed (first part's).
    measure_numbers: list[str]
    #: parts whose measure count differs from the first part's.
    ragged_parts: list[str]
    #: True where any part declared `<staves>` > 1.
    has_multistaff: bool


def load_keys(path: str | Path) -> ScoreKeys:
    p = Path(path)
    root = ET.fromstring(read_xml_bytes(p))
    if _strip_ns(root.tag) == "score-timewise":
        raise ValueError("timewise MusicXML is not handled")

    names: dict[str, str] = {}
    part_list = _find(root, "part-list")
    if part_list is not None:
        for sp in part_list:
            if _strip_ns(sp.tag) == "score-part":
                names[sp.get("id") or ""] = _text(_find(sp, "part-name"))

    timelines: list[StaffTimeline] = []
    n_measures = 0
    measure_numbers: list[str] = []
    ragged: list[str] = []
    has_multistaff = False
    first_count: int | None = None

    for part in root:
        if _strip_ns(part.tag) != "part":
            continue
        pid = part.get("id") or ""
        pname = names.get(pid, pid)
        measures = [m for m in part if _strip_ns(m.tag) == "measure"]
        if first_count is None:
            first_count = len(measures)
            measure_numbers = [m.get("number") or "" for m in measures]
        elif len(measures) != first_count:
            ragged.append(pname or pid)
        n_measures = max(n_measures, len(measures))

        n_staves = 1
        # per-staff records, built lazily as staff numbers are met
        per_staff: dict[int, StaffTimeline] = {}
        pending_all: list[tuple[int, str, object]] = []  # ordinal, kind, value

        def staff_rec(num: int) -> StaffTimeline:
            if num not in per_staff:
                per_staff[num] = StaffTimeline(pid, pname, num)
            return per_staff[num]

        for ordinal, measure in enumerate(measures):
            cur_staff_default = 1
            for node in measure:
                tag = _strip_ns(node.tag)
                if tag == "attributes":
                    st = _find(node, "staves")
                    if st is not None:
                        try:
                            n_staves = max(n_staves, int(_text(st)))
                        except ValueError:
                            pass
                        if n_staves > 1:
                            has_multistaff = True
                    for child in node:
                        ctag = _strip_ns(child.tag)
                        if ctag == "key":
                            num = child.get("number")
                            fifths_el = _find(child, "fifths")
                            target = int(num) if num and num.isdigit() else ALL_STAVES
                            if fifths_el is None:
                                pending_all.append((ordinal, "nontrad", target))
                            else:
                                try:
                                    val = int(_text(fifths_el))
                                except ValueError:
                                    pending_all.append((ordinal, "nontrad", target))
                                else:
                                    pending_all.append(
                                        (ordinal, "key", (target, val)))
                        elif ctag == "transpose":
                            num = child.get("number")
                            target = int(num) if num and num.isdigit() else ALL_STAVES
                            try:
                                dia = int(_text(_find(child, "diatonic")) or 0)
                            except ValueError:
                                dia = 0
                            try:
                                chrom = int(_text(_find(child, "chromatic")) or 0)
                            except ValueError:
                                chrom = 0
                            pending_all.append(
                                (ordinal, "transpose", (target, dia, chrom)))
                elif tag == "note":
                    st_el = _find(node, "staff")
                    snum = cur_staff_default
                    if st_el is not None:
                        try:
                            snum = int(_text(st_el))
                        except ValueError:
                            pass
                    rec = staff_rec(snum)
                    rec.any_note.add(ordinal)
                    if _find(node, "rest") is None:
                        rec.sounding.add(ordinal)

        # Make sure every declared staff exists even if it holds no notes.
        for s in range(1, max(n_staves, 1) + 1):
            staff_rec(s)

        for ordinal, kind, value in pending_all:
            if kind == "key":
                target, val = value  # type: ignore[misc]
                targets = list(per_staff) if target == ALL_STAVES else [target]
                for t in targets:
                    staff_rec(t).stated[ordinal] = val
            elif kind == "nontrad":
                target = value  # type: ignore[assignment]
                targets = list(per_staff) if target == ALL_STAVES else [target]
                for t in targets:
                    staff_rec(t).nontraditional.add(ordinal)
            else:
                target, dia, chrom = value  # type: ignore[misc]
                targets = list(per_staff) if target == ALL_STAVES else [target]
                for t in targets:
                    staff_rec(t).transpose[ordinal] = (dia, chrom)

        timelines.extend(per_staff[k] for k in sorted(per_staff))

    return ScoreKeys(
        path=str(p),
        n_measures=n_measures,
        staves=timelines,
        measure_numbers=measure_numbers,
        ragged_parts=ragged,
        has_multistaff=has_multistaff,
    )
