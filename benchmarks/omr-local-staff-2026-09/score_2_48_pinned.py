"""2.48 PINNED comb -- step 4 full count-page re-gather score (ROADMAP
2.48, Sean's design #3). Adapted from `gather_only_judge.py` (the
GATHER+ADJUDICATE-only judge, 2026-10-01) with this lane's own BASE and
ARM records in place of the seeded lane's.

BASE = a fresh `acceptance_quick --doc beethoven5-litolff` gather on THIS
SAME tree/worktree with `lane-2.48-seeded`'s own `measure_extractor.py`
(`62116487`) swapped in -- "Base vs arm on ONE tree" (CLAUDE.md §6b): the
only methodologically sound base is one gathered fresh here, not an older
record from a concurrent worktree that may no longer reproduce.
ARM = this branch (the pinned comb), gathered on the SAME tree right after,
`measure_extractor.py` restored.
"""
import sys, json, collections

REPO_ROOT = "/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-aa0df8922b4769f2c"
sys.path.insert(0, REPO_ROOT)
from tools.omr.acceptance_quick import _FAMILY_MAPS, _reference_root, _load_works_row, _union_bars
from tools.omr.pitch_resolver import diatonic_index, _CLEF_ANCHORS

DOCS = {
    "beethoven5-litolff": dict(
        base=f"{REPO_ROOT}/benchmarks/acceptance/quick/out_base_2_48/out/beethoven5-litolff/beethoven5-litolff-p3.record.json",
        arm=f"{REPO_ROOT}/benchmarks/acceptance/quick/out_arm_2_48_pinned/out/beethoven5-litolff/beethoven5-litolff-p3.record.json",
        works_row_id="beethoven-sym5-mvt1-984073-p3",
    ),
}
_LETTER_ORDER = {"C": 0, "D": 1, "E": 2, "F": 3, "G": 4, "A": 5, "B": 6}


def pitch_height(p):
    return p[1] * 7 + _LETTER_ORDER.get(p[0], 0)


def position_from_pitch(letter, octave, clef):
    anchor = _CLEF_ANCHORS.get(clef)
    if anchor is None:
        return None
    return diatonic_index(*anchor) - diatonic_index(letter, octave)


def parse_ref_pitch(s):
    if not s:
        return None
    step, rest, i = s[0], s[1:], 0
    if i < len(rest) and rest[i] in "+-":
        i += 1
        if i < len(rest) and rest[i].isdigit():
            i += 1
    try:
        return step, int(rest[i:])
    except ValueError:
        return None


def truth_onset_groups(ref_bars, bar):
    by_onset = {}
    for ev in ref_bars.get(str(bar), ()):
        if ev.pitch is None:
            continue
        p = parse_ref_pitch(ev.pitch)
        if p is not None:
            by_onset.setdefault(ev.onset, []).append(p)
    return [by_onset[k] for k in sorted(by_onset)]


def load_record(path):
    return json.loads(open(path).read())["record"]


def decided(rec, sub, q):
    for v in rec.get("verdicts", []):
        if v["subject"] == sub and v["quantity"] == q and v.get("outcome") == "decided":
            return v["value"]
    return None


def notehead_pos_obs(rec, sub):
    rows = [o for o in rec["observations"]
           if o["subject"] == sub and o["quantity"] == "notehead_staff_position"]
    return float(rows[-1]["value"]) if rows else None


def score_doc(doc_id, cfg, arm_name):
    rec = load_record(cfg[arm_name])
    works_row = _load_works_row(cfg["works_row_id"])
    ref_root = _reference_root(works_row["reference"]["catalog_path"])
    family_map = _FAMILY_MAPS[doc_id]
    family_by_pnum = {int(ids[0][1:]): fam for fam, (ids, _r) in family_map.items()}

    staff_keys = sorted({o["subject"] for o in rec["observations"] if o["quantity"] == "staff_lines"})
    tally = collections.Counter()
    per_head = {}
    for staff_key in staff_keys:
        p = staff_key.split("/")
        page_idx, system, staff = int(p[1]), int(p[2]), int(p[3])
        ordinal = decided(rec, staff_key, "staff_ordinal")
        if ordinal is None or (ordinal + 1) not in family_by_pnum:
            continue
        family = family_by_pnum[ordinal + 1]
        clef = decided(rec, staff_key, "clef")
        measure_partition = decided(rec, staff_key, "measure_partition")
        system_key = f"system/{page_idx}/{system}"
        printed_bar = decided(rec, system_key, "printed_bar_number")
        if measure_partition is None:
            continue
        ref_ids = family_map[family][1]
        ref_bars = _union_bars(ref_ids, ref_root)
        for cell in range(measure_partition):
            cell_key_prefix = f"glyph/{page_idx}/{system}/{staff}/{cell}/"
            dets = [o for o in rec["observations"]
                   if o["quantity"] == "glyph_box" and o["subject"].startswith(cell_key_prefix)
                   and o["value"] and str(o["value"][0]).startswith("notehead")]
            if not dets:
                continue
            dets_sorted = sorted(dets, key=lambda o: (
                o["detail"]["bbox_page_px"][0], o["detail"]["bbox_page_px"][1]))
            if clef is None or printed_bar is None:
                for o in dets_sorted:
                    per_head[o["subject"]] = "unscored"
                    tally["unscored"] += 1
                continue
            bar = printed_bar + cell
            groups = truth_onset_groups(ref_bars, bar)
            flat = []
            for g in groups:
                flat.extend(sorted(g, key=pitch_height, reverse=True))
            if len(flat) != len(dets_sorted):
                for o in dets_sorted:
                    per_head[o["subject"]] = "unscored"
                    tally["unscored"] += 1
                continue
            for o, truth in zip(dets_sorted, flat):
                sub = o["subject"]
                pos = notehead_pos_obs(rec, sub)
                if pos is None:
                    per_head[sub] = "unscored"
                    tally["unscored"] += 1
                    continue
                expected_pos = position_from_pitch(truth[0], truth[1], clef)
                if expected_pos is None:
                    per_head[sub] = "unscored"
                    tally["unscored"] += 1
                    continue
                verdict = "right" if round(pos) == expected_pos else "wrong"
                per_head[sub] = verdict
                tally[verdict] += 1
    return tally, per_head


def main():
    for doc_id, cfg in DOCS.items():
        bt, bh = score_doc(doc_id, cfg, "base")
        at, ah = score_doc(doc_id, cfg, "arm")
        print(f"=== {doc_id} ===")
        print(f"  base (lane-2.48-seeded, this tree): {dict(bt)}")
        print(f"  arm  (lane-2.48-pinned):             {dict(at)}")
        common = sorted(set(bh) & set(ah))
        changed = [(s, bh[s], ah[s]) for s in common if bh[s] != ah[s]]
        rtw = [c for c in changed if c[1] == "right" and c[2] != "right"]
        wtr = [c for c in changed if c[1] != "right" and c[2] == "right"]
        print(f"  changed: {len(changed)}  right->wrong: {len(rtw)}  wrong->right: {len(wtr)}")
        for c in changed:
            print(f"    {c}")


if __name__ == "__main__":
    main()
