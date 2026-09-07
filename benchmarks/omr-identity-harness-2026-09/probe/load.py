"""One staff-record shape, out of the two artefact shapes identity is recorded in.

Identity leaves the pipeline in two committed forms and the two existing
scorers each read one of them:

    "staff"   a transcription (or `extract.py`'s slim copy of one):
              `pages[].systems[].staves[]` with `instrument`,
              `instrument_source`, `instrument_veto`, `slot_index`.
    "compose" a `compose.py` blob: `contextual.absent_instrument_veto` with
              `staff_slots` (page, system, staff -> slot), `slot_instruments`
              (slot -> instrument + source) and `vetoes`.  `pages` is a list of
              page NUMBERS; there are no staff dicts at all.

⚠️ **The two shapes are not two measurements.**  A name is stamped per SLOT and
a staff inherits it, so the compose shape is the same fact one join earlier.
`assert_shapes_agree()` proves it on the one artefact that carries both:
deriving each staff's source from `slot_instruments[slot].source` reproduces
the per-staff `instrument_source` on **1616 of 1616** Beethoven staff records,
0 disagreements.  That check is what licenses pooling arms recorded in
different shapes, and it runs in `selftest.py`.

⚠️ **Ordering.** `staff_index` is page-wide and ascending in printed order in
both shapes — verified against `staff_geometry.line_ys_page` on all 140 systems
of the Beethoven extract, 0 disagreements — so systems are ordered by
`staff_index` here regardless of shape.  A harness that got this wrong would
score a correct run as a permutation error.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

MAIN = Path("/Users/seanjohnson/Desktop/ReEngrave")


@dataclass
class Staff:
    page: int
    system: int
    staff_index: int
    ordinal: int          # position within its own system, 0 = top
    n_staves: int         # size of its system
    slot: int | None
    instrument: str | None
    source: str | None    # `instrument_source`: label / roster / score_order /
    #                       score_order_ambiguity / None
    vetoed: bool
    label_read: str | None = None   # what the margin reader resolved here


@dataclass
class Document:
    work: str
    arm: str
    path: str
    shape: str
    pages: list[int]
    staves: list[Staff]
    slot_instruments: dict = field(default_factory=dict)
    slot_sources: dict = field(default_factory=dict)
    contextual_keys: list = field(default_factory=list)

    @property
    def n_staff_records(self) -> int:
        return len(self.staves)


def _label_map(veto_blob) -> dict:
    """(page, staff_index) -> instrument the MARGIN reader resolved there.

    This is read-off-the-page evidence, independent of the slot join, and it is
    what makes a `self-contradiction` countable: a staff whose own printed
    label was resolved and which is exported as something else.
    """
    out = {}
    for e in veto_blob.get("label_evidence", []) or []:
        out[(e["page_index"], e["staff_index"])] = e.get("instrument")
    return out


def load(path: str | Path, work: str, arm: str) -> Document:
    p = Path(path)
    if not p.is_absolute():
        p = MAIN / p
    r = json.loads(p.read_text())
    ctx = r.get("contextual") or {}
    blob = ctx.get("absent_instrument_veto") or {}
    labels = _label_map(blob)
    slot_name = {s["slot"]: s["instrument"] for s in blob.get("slot_instruments", [])}
    slot_src = {s["slot"]: s.get("source") for s in blob.get("slot_instruments", [])}

    pages = r.get("pages")
    staff_shape = bool(pages) and isinstance(pages[0], dict)

    rows: list[Staff] = []
    if staff_shape:
        shape = "staff"
        page_nums = [p_["page_index"] for p_ in pages]
        for p_ in pages:
            for sy in p_.get("systems", []):
                sts = sorted(sy.get("staves", []), key=lambda s: s["staff_index"])
                for i, s in enumerate(sts):
                    rows.append(Staff(
                        page=p_["page_index"], system=sy.get("system_index"),
                        staff_index=s["staff_index"], ordinal=i,
                        n_staves=len(sts), slot=s.get("slot_index"),
                        instrument=s.get("instrument"),
                        source=s.get("instrument_source"),
                        vetoed=bool(s.get("instrument_veto")),
                        label_read=labels.get((p_["page_index"], s["staff_index"]))))
    else:
        shape = "compose"
        page_nums = list(pages or [])
        vet = {(v["page_index"], v["system_index"], v["staff_index"])
               for v in blob.get("vetoes", [])}
        bysys: dict[tuple[int, int], list[dict]] = {}
        for s in blob.get("staff_slots", []):
            bysys.setdefault((s["page_index"], s["system_index"]), []).append(s)
        for (pg, sy), sts in bysys.items():
            sts.sort(key=lambda s: s["staff_index"])
            for i, s in enumerate(sts):
                sl = s.get("slot")
                named = sl is not None and sl >= 0
                rows.append(Staff(
                    page=pg, system=sy, staff_index=s["staff_index"], ordinal=i,
                    n_staves=len(sts), slot=sl if named else None,
                    instrument=slot_name.get(sl) if named else None,
                    source=slot_src.get(sl) if named else None,
                    vetoed=(pg, sy, s["staff_index"]) in vet,
                    label_read=labels.get((pg, s["staff_index"]))))

    rows.sort(key=lambda s: (s.page, s.system, s.staff_index))
    return Document(work=work, arm=arm, path=str(p), shape=shape,
                    pages=page_nums, staves=rows,
                    slot_instruments=slot_name, slot_sources=slot_src,
                    contextual_keys=sorted(ctx))


def apply_veto(doc: Document) -> Document:
    """The veto-ON arm, derived: a vetoed staff loses its name.

    `OMR_ABSENT_INSTRUMENT_VETO=report` computes the veto list and applies
    nothing, and the vetoed set is not an input to slot assignment — so one
    `report` run carries both veto arms.  Deriving them is `compose.py`'s own
    documented construction, not an invention here.
    """
    out = []
    for s in doc.staves:
        if s.vetoed:
            s = Staff(**{**s.__dict__, "instrument": None, "source": None})
        out.append(s)
    return Document(**{**doc.__dict__, "arm": doc.arm + "+veto", "staves": out})
