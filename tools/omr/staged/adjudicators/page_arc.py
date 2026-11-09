"""ROADMAP 2.274 step 2 -- the witnessed page-ink arc runs, bound to notes (ADJUDICATE; flag `OMR_PAGE_ARC_WRITE`, default OFF). The rule is `page_arc_bind`'s docstring."""
from __future__ import annotations

from typing import Any, Dict, List

from ..adjudicate import Checkable, Evidence, Mode, Ruling, decision
from .. import record as R
from ..record import Kind, Outcome, Q, Scope
from .ownership import _bind_detail


@decision(
    quantity=Q.PAGE_ARC_BINDING,
    checkable=Checkable.MIXED,
    checked_by=(
        "a TIE's two bound heads sound ONE pitch -- EXPORT compares the two placed pitches and refuses (and counts) a pair that differs",
        "the two ends of one run are two DIFFERENT heads of the run's own staff, in one voice (EXPORT refuses one head at both ends and two voices)",
    ),
    implicates=(Q.PAGE_ARC_BINDING, Q.ARC_KIND, Q.TIE_PAIR, Q.NOTEHEAD_STAFF_POSITION),
    composed_from=(Q.PAGE_ARC, Q.GLYPH_BOX, Q.NOTEHEAD_STAFF_POSITION),
    scope=Kind.PAGE,
    wants=(Q.PAGE_ARC, Q.ARC_BOX, Q.NOTEHEAD_STAFF_POSITION, Q.GLYPH_BOX, Q.STEM, Q.ARC_OWNER, Q.ARC_IS_NOT_AN_ARC, Q.GLYPH_OWNER,
           Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, Q.CELL_BOX, Q.NOTEHEAD_POSITION, Q.ACCIDENTAL_STAFF_POSITION, Q.ACCIDENTAL_OWNER, Q.CELL_STAFF_SPACE, Q.SYSTEM_ARC),
    subjects_from=Q.PAGE_ARC,
    reasons=("bound", "none_bound", "no_witnessed_run"),
    mode=Mode.ADDITIVE,
)
def adjudicate_page_arc_binding(ev: Evidence) -> Ruling:
    """ROADMAP 2.274 step 2: ONE page-wide pass, AFTER the heads are read, over the page's `Q.PAGE_ARC` runs that a detector arc box WITNESSES. Each run's two ends are
    bound to notes by the SAME code as a detector curve (`ownership._bind_detail`, 2.223's body, moved), with the closest-note rule for an end that stops short
    (`page_arc_bind.closest_binder`), and the kind follows by Sean's tie rule on the two bound heads. The detector's class is not an input. A run that binds both ends to two
    different heads and reads a kind is `written`; any other is `abstained` with the reason (an end unbound, two columns about equally near, a chord end that cannot choose,
    one head at both ends, same pitch with heads between, a step unread ...), and the old path keeps the mark. A run with one end bound and the other off the system's edge is
    `abstained` with `edge` set: EXPORT may join it to the run that picks up on the next system. One verdict per page; `detail["runs"]` one entry per run
    (see `Q.PAGE_ARC_BINDING`)."""
    from .. import page_arc_bind as PB
    page = ev.subject
    rows = [r for r in ev.rows(Q.PAGE_ARC, scope=Scope.SELF_AND_DESCENDANTS, subject=page)
            if r.value == "run" and (r.detail or {}).get("ends") and (r.detail or {}).get("space_page_px")]
    details = [dict(r.detail or {}) for r in rows]
    peers = [dict(ends=dt.get("ends"), staff=dt.get("staff") or [0, 0]) for dt in details]
    out: List[Dict[str, Any]] = []
    used: List[str] = []
    for i, r in enumerate(rows):
        dt = details[i]
        entry: Dict[str, Any] = {"ordinal": dt.get("ordinal"), "row": r.id, "status": PB.NOT_WITNESSED, "witnesses": []}
        out.append(entry)
        sp = float(dt["space_page_px"])
        ws = []
        for w in dt.get("witnesses") or ():
            try:
                wsub = R.Subject.from_key(str(w))
            except Exception:
                continue
            anv = ev.verdict(Q.ARC_IS_NOT_AN_ARC, subject=wsub)
            if anv is not None and anv.outcome is Outcome.DECIDED and anv.value is True:
                continue          # a box ADJUDICATE refused as an arc (a staff line, a barline) witnesses nothing
            ws.append(str(w))
        if not ws:
            entry["why"] = "no_usable_witness" if dt.get("witnesses") else "no_detector_box"
            continue
        entry["witnesses"] = ws
        # the staff: the witnessing boxes' decided owner where they agree, else the staff nearest the run's middle (the row's own `staff`)
        owners = []
        for w in ws:
            ov = ev.verdict(Q.ARC_OWNER, subject=R.Subject.from_key(w))
            if ov is not None and ov.outcome is Outcome.DECIDED and isinstance(ov.value, str) and ov.value:
                owners.append(ov.value)
        st = dt.get("staff") or [0, 0]
        own_row = R.Subject(Kind.STAFF, page.page, int(st[0]), int(st[1])).to_key()
        if owners and len(set(owners)) == 1:
            home = owners[0]
            entry["home_from"] = "witness_owner"
        else:
            home = own_row
            entry["home_from"] = "run_staff" if not owners else "witnesses_disagree"
        entry["home"] = home
        d = PB.curve_detail(dt, sp)
        if d is None:
            entry.update(status=PB.ABSTAINED, why="no_ends")
            continue
        binder = PB.closest_binder(PB.facing_ends(peers, i, st))
        b = _bind_detail(ev, "", d, home, "page_arc/%s" % r.id, r.id,
                         lambda heads_, sp_, usable_, end_pitch_, alt_, _b=binder, _d=d: _b(heads_, sp_, usable_, end_pitch_, alt_, _d))
        entry["left"], entry["right"] = b.get("left"), b.get("right")
        used.append(r.id)
        if b.get("kind") in ("tie", "slur") and b.get("start") and b.get("stop") and b["start"] != b["stop"]:
            entry.update(status=PB.WRITTEN, kind=b["kind"], start=b["start"], stop=b["stop"], relation=b.get("relation"),
                         crosses_barline=b.get("crosses_barline"), rule=b.get("rule"),
                         closest=[s_ for s_ in ("left", "right") if b[s_].get("via_closest")])
            used.extend(b.get("head_ids") or ())
        else:
            why = b.get("why") or next((b[s_].get("unbound") for s_ in ("left", "right") if b[s_].get("unbound")), None) or "no_kind"
            entry.update(status=PB.ABSTAINED, why=why)
            for s_ in ("left", "right"):
                if b[s_].get("unbound"):
                    entry.setdefault("unbound", {})[s_] = {k: v for k, v in b[s_].items() if k in ("unbound", "candidates", "margin_spaces")}
            if why == "system_edge":
                side = "left" if b["left"].get("edge") else "right"
                other = b["right"] if side == "left" else b["left"]
                if other.get("head") and not (b["left"].get("edge") and b["right"].get("edge")):
                    e = dt["ends"][0 if side == "left" else 1]
                    entry.update(edge=side, edge_head=str(other["head"]), x_end=float(e[0]), sp=sp, staff_key=home)
            if b.get("relation") is not None:
                entry["relation"] = b.get("relation")
    n_w = sum(1 for e in out if e["status"] == PB.WRITTEN)
    n_a = sum(1 for e in out if e["status"] == PB.ABSTAINED)
    if not any(e["witnesses"] for e in out):
        return Ruling.abstain("no_witnessed_run", runs=out)
    return Ruling(value={"runs": len(out), "written": n_w, "abstained": n_a, "not_witnessed": len(out) - n_w - n_a},
                  reason="bound" if n_w else "none_bound", used=tuple(dict.fromkeys(used)), detail={"runs": out})
