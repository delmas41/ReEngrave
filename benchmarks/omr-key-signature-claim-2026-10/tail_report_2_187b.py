"""2.187b: read the DUMP_TAIL output of `known_flats_2_187.py` (REAL gather rows -> the new key tail judge -> ADJUDICATE of each page's slice).
usage: tail_report_2_187b.py FLATS.tail.json FLATS.json
Prints (1) per Litolff known flat: refused / narrowed (blue) / left alone (still a rest); (2) every notehead-class tail box the judge NARROWED
(a note turned blue); (3) staves per plate by where their written key came from (`key_tail_context`); (4) the READ slots' fixed-order check."""
import collections, json, sys
sys.path.insert(0, ".")
from tools.omr.staged import key_object as KO

T = json.load(open(sys.argv[1]))
R = json.load(open(sys.argv[2]))
KN = {"litolff": {f["g"] for f in json.load(open("benchmarks/omr-key-signature-claim-2026-10/key_flats_written_as_rests_litolff.json"))}}
print("== known Litolff flats (20)")
cnt = collections.Counter()
seen = {}
for t in T:
    for g, e in t["boxes"].items():
        if t["doc"] == "litolff" and g in KN["litolff"]:
            v = (e.get("verdicts") or {}).get("rest_is_not_a_rest") or {}
            tag = "REFUSED(read slot)" if v.get("reason") == "claimed_by:key_signature" else "BLUE(narrowed)" if v.get("outcome") == "narrowed" else "left alone"
            seen.setdefault(g, []).append((t["part"], tag, e.get("tail") and {k: e["tail"].get(k) for k in ("shape", "step", "h", "basis")}))
for g in sorted(KN["litolff"]):
    rows = seen.get(g, [])
    best = sorted(rows, key=lambda r: ("REFUSED" not in r[1], "BLUE" not in r[1]))[0][1] if rows else "not in a key claim"
    cnt[best] += 1
    print(g, best, rows[:2])
print(cnt)
print("== notehead-class boxes the tail judge NARROWED (a real note turned blue)")
n_nb, n_tot = 0, 0
for t in T:
    if t["part"] not in ("placed", "none_read"):
        continue
    for g, e in t["boxes"].items():
        if not e.get("cls", "").startswith("notehead") or e.get("tail") is None:
            continue
        n_tot += 1
        v = (e.get("verdicts") or {}).get("notehead_is_not_a_notehead") or {}
        if v.get("outcome") == "narrowed" and v.get("reason", "").startswith("claim_narrowed"):
            n_nb += 1
            print("  ", t["doc"], g, e["cls"], e["tail"], t.get("ctx"))
print("noteheads in a tail:", n_tot, "turned blue:", n_nb)
print("== staves by where the written key came from")
by = collections.Counter()
seen_staff = set()
for t in T:
    if t["staff"] in seen_staff:
        continue
    seen_staff.add(t["staff"])
    c = t.get("ctx") or {}
    by[(t["doc"], c.get("source") or "error", c.get("why") or "", "written=%s" % c.get("written"))] += 1
for k, v in sorted(by.items(), key=str):
    print("  ", k, v)
print("== READ slots in the fixed order (flat keys: the written type is flat; step of the ink centre vs the table)")
ok = bad = 0
for t in T:
    if t["part"] != "read" or not t["clef"]:
        continue
    for rp in (t["ko"] or {}).get("read_pieces", []):
        if not rp or "step" not in rp:
            continue
        e = KO.expected_step(t["clef"], "b", rp["slot"])
        if e is None:
            continue
        d = abs(rp["step"] - (e - KO.glyph_offset_steps("b", rp["h"])))
        if d <= KO.POS_TOL_STEPS:
            ok += 1
        else:
            bad += 1
print("read pieces matching the fixed order (flat table):", ok, " not matching (a place to look again, never a rest):", bad)
