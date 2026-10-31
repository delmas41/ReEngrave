"""ROADMAP 2.238: parity of the REWORKED stroke owner (`OMR_OWNER_SHAPE` ON) with the OLD rules' refusals on main (2.237's OFF dump).

    OMR_SURYA_KEEP_ALIVE=0 OMR_OWNER_SHAPE=1 python3 benchmarks/rule-page/owner_parity.py replay PLATE TAG OUT_DIR
    python3 benchmarks/rule-page/owner_parity.py combine OFF_DUMP_DIR OUT_DIR       # then: rule_parity.py OUT_DIR/combined PARITY.json

`replay` re-adjudicates the saved slice with the current tree and env (as `replay_slice.py`, no re-gather) and keeps ONLY the cells'
`stroke_owner` verdicts (`OUT_DIR/PLATE.owner.jsonl`). `combine` writes `OUT_DIR/combined/PLATE.verdicts.jsonl`: the OFF dump's box
decisions (the old rules, as main decides them) beside the ON owner's verdicts, so `rule_parity.py` asks the one question -- does the
reworked owner refuse what the old rule refused? -- with the old rules' fires unchanged by the flag (the flag stops them deciding).
"""
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

BOX = ("notehead_is_not_a_notehead", "rest_is_not_a_rest", "accidental_owner", "notehead_is_an_eighth_rest")


def replay(plate, tag, out_dir):
    from tools.omr.staged import lane_report as LR
    from tools.omr.staged.review import rerun as RR
    keep = set(json.load(open(ROOT / "benchmarks" / "lane-report" / "sample.json"))["plates"][plate]["pages"])
    rec = LR.load_slices(LR.slice_dir(plate, tag))
    rec["verdicts"] = []
    log, _ = RR.rebuild_gather(rec)
    del rec
    RR.run_stages(log)
    d = pathlib.Path(out_dir)
    d.mkdir(parents=True, exist_ok=True)
    n = 0
    with open(d / ("%s.owner.jsonl" % plate), "w") as fh:
        for v in log.to_json()["verdicts"]:
            if v["quantity"] in ("stroke_owner",) + BOX and LR.page_of(v.get("subject")) in keep:
                fh.write(json.dumps(v, default=str) + "\n")
                n += 1
    print(plate, tag, "verdicts kept", n)


def combine(off_dir, out_dir):
    d = pathlib.Path(out_dir)
    (d / "combined").mkdir(parents=True, exist_ok=True)
    for plate in ("litolff", "brahms"):
        on = d / ("%s.owner.jsonl" % plate)
        off = pathlib.Path(off_dir) / ("%s.verdicts.jsonl" % plate)
        if not (on.exists() and off.exists()):
            continue
        with open(d / "combined" / ("%s.verdicts.jsonl" % plate), "w") as fh:
            for line in open(off):
                if any(('"quantity": "%s"' % q) in line[:400] for q in BOX):
                    fh.write(line)
            for line in open(on):
                if '"quantity": "stroke_owner"' in line[:400]:
                    fh.write(line)
        print(plate, "combined")


if __name__ == "__main__":
    if sys.argv[1] == "replay":
        replay(*sys.argv[2:5])
    else:
        combine(*sys.argv[2:4])
