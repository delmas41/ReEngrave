"""Shrink a verdict row to what the arc ledger reads (the full rows carry 2-100 KB of `considered` / `basis` each)."""
from __future__ import annotations

PB_KEYS = ("kind", "why", "start", "stop", "relation", "relation_source", "curve", "crosses_barline", "between", "dy_spaces",
           "left", "right", "junctions", "contested_end", "stem_tip_ends", "start_step", "stop_step", "local_dy_spaces", "home", "rule")


def slim_verdict(v: dict) -> dict:
    out = {k: v.get(k) for k in ("subject", "quantity", "outcome", "value", "reason", "decider")}
    d = v.get("detail") or {}
    q = v["quantity"]
    if q == "arc_kind":
        g = d.get("grammar") or {}
        pb = g.get("page_binding") or d.get("page_binding")
        sd = {"detector_class": d.get("detector_class")}
        if pb:
            sd["page_binding"] = {k: pb.get(k) for k in PB_KEYS if k in pb}
        tsr = g.get("tie_slur_rule")
        if tsr:
            sd["rule"] = tsr.get("rule")
            tn = tsr.get("two_note") or {}
            sd["two_note"] = {k: tn.get(k) for k in ("evaluated", "why", "start", "stop", "relation", "kind", "reason") if k in tn}
        sd["flanked_heads"] = g.get("flanked_heads")
        sa = g.get("system_arc")
        if sa:
            sd["system_arc_shape"] = sa.get("shape")
        out["detail"] = sd
    elif q == "tie_pair":
        out["detail"] = {k: d.get(k) for k in ("curve", "dy_spaces", "dx_spaces", "crosses_barline", "home_staff", "lefts", "rights",
                                              "pairs_at_one_position", "nearest_dy_spaces", "local_abstain", "candidates", "candidates_blocked")
                         if k in d}
        if v.get("candidates"):
            out["candidates"] = v["candidates"]
    elif q == "arc_is_not_an_arc":
        out["detail"] = {k: d.get(k) for k in ("ink_coverage", "ink_lines_in_box", "width_spaces", "height_spaces", "staff_line_refusal_overruled_by") if k in d}
    elif q == "arc_owner":
        out["detail"] = {k: d.get(k) for k in ("page_span", "page_span_reason") if k in d}
    return out
