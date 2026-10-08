"""ROADMAP 2.58d -- read-only extraction for the stem-owner replay.

ONE `record_io.load_record` of a 10-07 day record -> a pickle holding exactly what `adjudicate_glyph_owner` and
`reconcile_group_owners` read (the decision's own `wants`, the ledger-ladder rows beside them, the mark groups, the
instrument / clef / not-a-ledger / not-a-note verdicts, the record's own `glyph_owner` verdicts as the CONTROL), and the
contested heads' page boxes + their own staff's spacing, which `stem_owner_measure.py` needs to read the page raster.

  python3 benchmarks/omr-local-staff-2026-09/stem_owner_extract.py <record.json> <out.pkl>

No GATHER row is written; nothing is read but the record.
"""
import pickle
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from tools.omr.staged.record_io import load_record  # noqa: E402

OBS = {"glyph_ladder", "glyph_band_distance", "glyph_conf", "notehead_staff_position", "human_box_verdict",
       "glyph_box", "wedge_box", "staff_lines", "staff_spacing", "ledger_rung_ink", "ledger_owner_density",
       "far_head_owner_ledger", "staff_extent", "staff_skew", "mark_group", "notehead_class", "stem_direction"}
VERD = {"instrument", "clef", "ledger_is_not_a_ledger", "notehead_is_not_a_notehead", "glyph_owner"}


def main(src, dst):
    res = load_record(src)
    rec = res["record"]
    sup = {v["supersedes"] for v in rec["verdicts"] if v.get("supersedes")}
    obs = [o for o in rec["observations"] if o["quantity"] in OBS]
    abst = [a for a in rec["abstentions"] if a["quantity"] in OBS]
    verd = [v for v in rec["verdicts"] if v["quantity"] in VERD]
    for v in verd:
        v["_superseded"] = v["id"] in sup
    print(len(obs), len(abst), len(verd), "keys of an abstention:", sorted(abst[0]) if abst else None, flush=True)
    pickle.dump({"obs": obs, "abst": abst, "verdicts": verd}, open(dst, "wb"))


if __name__ == "__main__":
    main(*sys.argv[1:3])
