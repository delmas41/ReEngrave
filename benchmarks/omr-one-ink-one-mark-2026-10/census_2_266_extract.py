"""2.266: stream a saved record once; keep every DECIDED accidental_owner verdict (the accidental the file may write) with BOTH readings of its ink:
the accidental_family reading (type from the strokes, margin) and the 2.186 one-ink merge (detector winner, rivals, margin), plus what the owner
verdict's alteration is (= what is written) and whether the head's Q.ACCIDENTAL stands. Measurement only: no gather, no OCR.
usage (repo root): python3 benchmarks/omr-one-ink-one-mark-2026-10/census_2_266_extract.py RECORD OUT.jsonl [RECORD OUT.jsonl ...]"""
import json, pathlib, sys
sys.path.insert(0, ".")
from tools.omr.staged import judged as J


def main(rec, out):
    owners, acc = [], {}
    for v in J.iter_array(pathlib.Path(rec), "verdicts"):
        q = v.get("quantity")
        if q == "accidental_owner" and v.get("outcome") == "decided":
            d = v.get("detail") or {}
            owners.append(dict(subject=v["subject"], head=v.get("value"), vid=v["id"], reason=v.get("reason"), alteration=d.get("alteration"),
                               detector_class=d.get("detector_class"), family=d.get("family"), one_ink=d.get("one_ink"),
                               shape_check=d.get("shape_check")))
        elif q == "accidental" and v.get("outcome") == "decided":
            acc[v["subject"]] = v.get("value")
    with open(out, "w") as fh:
        for o in owners:
            o["written"] = acc.get(o["head"])
            fh.write(json.dumps(o) + "\n")
    print(pathlib.Path(rec).name, "decided owners", len(owners), flush=True)


if __name__ == "__main__":
    for i in range(1, len(sys.argv), 2):
        main(sys.argv[i], sys.argv[i + 1])
