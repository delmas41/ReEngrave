"""2.302: OFF vs ON replay outputs (replay.py), through the 2.299 reader (`key_kind_slots.read`), staff by staff.
    PYTHONPATH=. python3 benchmarks/key-object-counts-flats-2026-11/compare.py PLATE OFF.json ON.json [--judged]

The clef given to the reader is the detector's clef BOX clef (`clef_measured`): the READ clef (ADJUDICATE) is not in a gather replay, so a staff whose box names
no clef is `no_clef` here though ADJUDICATE may read one. Truth for the judged starts: Sean's answers (2.292 r1, 2.299 r1)."""
import json
import sys

from tools.omr.staged import key_kind_slots as KKS

# Sean's answers: staff key -> fifths (2.292 r1 tiles 1-10,12; 2.299 r1 tiles 1-12). 2.292 tile 11 was cut off: not judged.
TRUTH = {
    "litolff": {"2/0/3": -3, "4/1/10": -3, "11/1/9": -3, "4/0/6": -3, "2/1/9": -3, "6/0/4": 0, "6/1/3": -3, "6/1/6": 0, "8/1/8": -3,
                "2/0/1": -3, "1/0/10": -3, "16/0/1": -3, "2/0/0": -3, "4/0/7": -3, "4/1/7": -3, "8/1/9": -3, "16/0/0": -3, "2/0/10": -3, "6/1/11": -3},
    "brahms": {"4/1/8": 0, "4/1/7": 0, "4/1/12": -3, "4/1/10": -3},
}


def res_of(v):
    ko = {"system_count": v["N"], "read_pieces": v["pieces"], "more_than_system": v["more"], "own_slots": v["own"]}
    return KKS.read({"ko": ko, "space": v["space"]}, v["clef"])


def main():
    plate, a, b = sys.argv[1:4]
    off, on = json.load(open(a)), json.load(open(b))
    judged = TRUTH.get(plate, {})
    n_read_off = n_read_on = 0
    rows = []
    for k in sorted(off, key=lambda s: tuple(int(x) for x in s.split("/"))):
        ro, rn = res_of(off[k]), res_of(on[k])
        n_read_off += ro["standing"] == "READ"
        n_read_on += rn["standing"] == "READ"
        f_o, f_n = KKS.fifths_of(ro), KKS.fifths_of(rn)
        rows.append((k, ro, rn, f_o, f_n))
    print("%s: staff-systems READ by the 2.299 reader: OFF %d  ON %d  (of %d)" % (plate, n_read_off, n_read_on, len(off)))
    wrong = 0
    print("changed staves (own slots / N / reader):")
    for k, ro, rn, f_o, f_n in rows:
        if (off[k]["own"], off[k]["N"], ro["why"]) != (on[k]["own"], on[k]["N"], rn["why"]) or f_o != f_n:
            t = judged.get(k)
            tag = "" if t is None else ("  JUDGED=%s %s" % (t, "OK" if (f_n is None or f_n == t) else "WRONG"))
            wrong += (t is not None and f_n is not None and f_n != t)
            print("  %-8s OFF own %s N %s %-26s %s | ON own %s N %s %-26s %s%s" % (k, off[k]["own"], off[k]["N"], ro["why"], f_o, on[k]["own"], on[k]["N"], rn["why"], f_n, tag))
    print("READ with a key different from Sean's judged: %d" % wrong)
    if "--judged" in sys.argv:
        print("judged staff starts (truth fifths):")
        for k, ro, rn, f_o, f_n in rows:
            if k in judged:
                print("  %-8s truth %2s  OFF own %s %-26s %s | ON own %s %-26s %s  extra=%s" % (k, judged[k], off[k]["own"], ro["why"], f_o, on[k]["own"], rn["why"], f_n,
                                                                                         len(on[k].get("extra") or [])))


if __name__ == "__main__":
    main()
