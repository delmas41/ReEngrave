"""Per-head trace for the 14 right->wrong + 1 wrong->right heads found by
gather_only_judge.py (GATHER+ADJUDICATE-only judge, 2026-10-01). Reuses
that judge's own pairing/reference logic (no re-derivation) to attach,
for each of the 15 subjects: base vs comb Q.NOTEHEAD_STAFF_POSITION, the
reference position (via ADJUDICATE's own clef), distance from the staff,
chord-or-single (ADJUDICATE event grouping), detector box, and bar/system
context -- read straight off the two records, no recomputation of either
reader's own shift.
"""
import sys, json

sys.path.insert(0, "/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a3ef66441824adfff")
sys.path.insert(0, "/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-aa614525a6a8a7cfc/benchmarks/omr-local-staff-2026-09")
from tools.omr.acceptance_quick import _FAMILY_MAPS, _reference_root, _load_works_row, _union_bars
from gather_only_judge import (
    parse_ref_pitch, position_from_pitch, pitch_height, truth_onset_groups,
)

SUBJECTS = [
    ("glyph/1/0/7/1/1", "right", "wrong"),
    ("glyph/1/0/8/1/6", "wrong", "right"),
    ("glyph/2/0/2/4/1", "right", "wrong"),
    ("glyph/2/0/3/0/5", "right", "wrong"),
    ("glyph/2/0/3/0/7", "right", "wrong"),
    ("glyph/2/0/3/3/2", "right", "wrong"),
    ("glyph/2/0/7/0/4", "right", "wrong"),
    ("glyph/2/0/7/10/3", "right", "wrong"),
    ("glyph/2/0/7/2/2", "right", "wrong"),
    ("glyph/3/0/0/2/4", "right", "wrong"),
    ("glyph/3/0/8/0/3", "right", "wrong"),
    ("glyph/3/0/8/0/4", "right", "wrong"),
    ("glyph/3/0/8/0/5", "right", "wrong"),
    ("glyph/3/0/8/0/8", "right", "wrong"),
    ("glyph/3/1/0/6/0", "right", "wrong"),
]

BASE_PATH = sys.argv[1]
ARM_PATH = sys.argv[2]
WORKS_ROW_ID = "beethoven-sym5-mvt1-984073-p3"
DOC_ID = "beethoven5-litolff"


def load(path):
    return json.loads(open(path).read())["record"]


def decided(rec, sub, q):
    for v in rec.get("verdicts", []):
        if v["subject"] == sub and v["quantity"] == q and v.get("outcome") == "decided":
            return v["value"]
    return None


def narrowed_candidates(rec, sub, q):
    for v in rec.get("verdicts", []):
        if v["subject"] == sub and v["quantity"] == q and v.get("outcome") == "narrowed":
            return v.get("candidates")
    return None


def obs(rec, sub, q):
    rows = [o for o in rec["observations"] if o["subject"] == sub and o["quantity"] == q]
    return rows[-1] if rows else None


def staff_key_of(sub):
    p = sub.split("/")
    return f"staff/{p[1]}/{p[2]}/{p[3]}"


def cell_key_of(sub):
    p = sub.split("/")
    return f"cell/{p[1]}/{p[2]}/{p[3]}/{p[4]}"


def system_key_of(sub):
    p = sub.split("/")
    return f"system/{p[1]}/{p[2]}"


def event_glyphs(rec, cell_key, glyph_idx):
    for v in rec.get("verdicts", []):
        if v["subject"] == cell_key and v["quantity"] == "event" and v.get("outcome") == "decided":
            for ev in v["value"].get("events", []):
                if glyph_idx in ev.get("glyphs", []):
                    return ev
    return None


def head_info(rec, sub):
    out = {}
    gb = obs(rec, sub, "glyph_box")
    if gb:
        out["box"] = gb["value"]
        out["detail"] = {k: gb.get("detail", {}).get(k) for k in ("bbox_page_px",)}
    pos = obs(rec, sub, "notehead_staff_position")
    out["pos"] = float(pos["value"]) if pos else None
    out["pos_detail"] = pos.get("detail") if pos else None
    nc = obs(rec, sub, "notehead_class")
    out["notehead_class"] = nc["value"] if nc else None
    staff_key = staff_key_of(sub)
    out["clef"] = decided(rec, staff_key, "clef")
    out["staff_ordinal"] = decided(rec, staff_key, "staff_ordinal")
    sysk = system_key_of(sub)
    out["printed_bar_number"] = decided(rec, sysk, "printed_bar_number")
    glyph_idx = int(sub.split("/")[-1])
    ev = event_glyphs(rec, cell_key_of(sub), glyph_idx)
    out["event"] = ev
    out["chord"] = (ev is not None and len(ev.get("glyphs", [])) > 1)
    owner = decided(rec, sub, "glyph_owner")
    out["glyph_owner"] = owner
    return out


def reference_for(sub, clef, printed_bar):
    p = sub.split("/")
    page_idx, system, staff, cell = int(p[1]), int(p[2]), int(p[3]), int(p[4])
    glyph_idx = int(p[5])
    works_row = _load_works_row(WORKS_ROW_ID)
    ref_root = _reference_root(works_row["reference"]["catalog_path"])
    family_map = _FAMILY_MAPS[DOC_ID]
    family_by_pnum = {int(ids[0][1:]): fam for fam, (ids, _r) in family_map.items()}
    ordinal = staff
    # staff_ordinal is read directly below instead of recomputed from path;
    # caller passes it in via clef/printed_bar already resolved. Need pnum:
    return None  # placeholder, filled by caller using full record access


def main():
    base = load(BASE_PATH)
    arm = load(ARM_PATH)
    works_row = _load_works_row(WORKS_ROW_ID)
    ref_root = _reference_root(works_row["reference"]["catalog_path"])
    family_map = _FAMILY_MAPS[DOC_ID]
    family_by_pnum = {int(ids[0][1:]): fam for fam, (ids, _r) in family_map.items()}

    for sub, base_v, arm_v in SUBJECTS:
        bi = head_info(base, sub)
        ai = head_info(arm, sub)
        staff_key = staff_key_of(sub)
        ordinal = decided(base, staff_key, "staff_ordinal")
        clef = bi["clef"]
        printed_bar = bi["printed_bar_number"]
        cell_idx = int(sub.split("/")[4])
        ref_pos = None
        ref_pitch_str = None
        if ordinal is not None and (ordinal + 1) in family_by_pnum and clef and printed_bar is not None:
            family = family_by_pnum[ordinal + 1]
            ref_ids = family_map[family][1]
            ref_bars = _union_bars(ref_ids, ref_root)
            bar = printed_bar + cell_idx
            groups = truth_onset_groups(ref_bars, bar)
            flat = []
            for g in groups:
                flat.extend(sorted(g, key=pitch_height, reverse=True))
            # find this glyph's index among noteheads in the cell, sorted by x,y
            cell_prefix = f"glyph/{sub.split('/')[1]}/{sub.split('/')[2]}/{sub.split('/')[3]}/{cell_idx}/"
            dets = [o for o in base["observations"]
                    if o["quantity"] == "glyph_box" and o["subject"].startswith(cell_prefix)
                    and o["value"] and str(o["value"][0]).startswith("notehead")]
            dets_sorted = sorted(dets, key=lambda o: (
                o["detail"]["bbox_page_px"][0], o["detail"]["bbox_page_px"][1]))
            idx_in_cell = next((i for i, o in enumerate(dets_sorted) if o["subject"] == sub), None)
            if idx_in_cell is not None and idx_in_cell < len(flat):
                truth = flat[idx_in_cell]
                ref_pitch_str = f"{truth[0]}{truth[1]}"
                ref_pos = position_from_pitch(truth[0], truth[1], clef)

        print(f"--- {sub} ({base_v} -> {arm_v}) ---")
        print(f"  staff_ordinal={ordinal} clef={clef} bar={printed_bar}+{cell_idx} chord={bi['chord']} event={bi['event']}")
        print(f"  box(base)={bi.get('box')}  box(arm)={ai.get('box')}  same_box={bi.get('box')==ai.get('box')}")
        print(f"  base pos={bi['pos']}  (detail={bi['pos_detail']})")
        print(f"  arm  pos={ai['pos']}  (detail={ai['pos_detail']})")
        print(f"  reference pitch={ref_pitch_str}  expected_pos={ref_pos}")
        if bi['pos'] is not None and ref_pos is not None:
            print(f"  base rounded={round(bi['pos'])} match={round(bi['pos'])==ref_pos}  dist_from_staff_mid(base)={bi['pos']-4}")
        if ai['pos'] is not None and ref_pos is not None:
            print(f"  arm  rounded={round(ai['pos'])} match={round(ai['pos'])==ref_pos}  dist_from_staff_mid(arm)={ai['pos']-4}")
        if bi['pos'] is not None and ai['pos'] is not None:
            print(f"  shift (arm - base) = {ai['pos'] - bi['pos']:.4f} staff-steps")
        print()


if __name__ == "__main__":
    main()
