"""2.263: from a saved record's verdicts, every DECIDED accidental_owner verdict that carries a family reading (the accidental the file may write),
with the head it alters, whether a Q.ACCIDENTAL verdict stands on that head, and what `accidental_family.guess_of` says (the blue flag).
usage: python3 benchmarks/omr-accidental-family-2026-10/margin_owners.py RECORD OUT.jsonl [RECORD OUT ...]   (run from the repo root)"""
import json, pathlib, sys
sys.path.insert(0, ".")
from tools.omr.staged import judged as J
from tools.omr.staged import accidental_family as AF


def main(rec, out):
    owners, acc_by_head, n = [], {}, 0
    for v in J.iter_array(pathlib.Path(rec), "verdicts"):
        q = v.get("quantity")
        if q == "accidental_owner" and v.get("outcome") == "decided":
            fam = (v.get("detail") or {}).get("family")
            oi = (v.get("detail") or {}).get("one_ink")
            owners.append((v["subject"], v.get("value"), fam, v.get("reason"), v["id"], oi))
        elif q == "accidental" and v.get("outcome") == "decided":
            acc_by_head[v["subject"]] = v.get("value")
    with open(out, "w") as fh:
        for sub, head, fam, reason, vid, oi in owners:
            g = AF.guess_of(fam) if fam else None
            fh.write(json.dumps({"subject": sub, "head": head, "vid": vid, "reason": reason, "family": fam, "blue_by_family": g is not None,
                                 "written": acc_by_head.get(head), "one_ink": bool(oi), "one_ink_margin": (oi or {}).get("margin")}) + "\n")
            n += 1
    print(pathlib.Path(rec).name, "decided owners", n, "with family", sum(1 for o in owners if o[2]),
          "blue_by_family", sum(1 for o in owners if o[2] and AF.guess_of(o[2]) is not None),
          "of which with a written accidental on the head", sum(1 for o in owners if o[2] and AF.guess_of(o[2]) is not None and o[1] in acc_by_head), flush=True)


if __name__ == "__main__":
    for i in range(1, len(sys.argv), 2):
        main(sys.argv[i], sys.argv[i + 1])
