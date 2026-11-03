"""ROADMAP 2.254: cut a gathered `.record.json` into a PRIVATE slice directory for claim_readout / claim_order (the same rows
`claim_readout.cut_record` keeps), so this lane never writes the shared `library/_shared-records/claim-readout-slices-*` names another
lane's identically named record would collide with.

    python3 benchmarks/hairpin-reach-2026-11/cut_slice.py REC.record.json OUTDIR 19,25
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.omr.staged.judged import iter_array  # noqa: E402


def main(rec, out, pages):
    d = pathlib.Path(out)
    d.mkdir(parents=True, exist_ok=True)
    for kind in ("observations", "abstentions", "verdicts"):
        with open(d / ("%s.jsonl" % kind), "w") as fh:
            for it in iter_array(pathlib.Path(rec), kind):
                if kind == "verdicts" and it.get("quantity") != "stroke_owner":
                    continue
                fh.write(json.dumps(it, default=str) + "\n")
    (d / "stamp.json").write_text(json.dumps({"pages": [int(p) for p in pages.split(",")], "source": str(rec)}))


if __name__ == "__main__":
    main(*sys.argv[1:4])
