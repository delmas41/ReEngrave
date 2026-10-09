"""Direction words and word+dynamic markings in two re-gathers, per movement.

`readout diff` compares glyph families; direction words are not glyphs, so this
counts them straight off both records (GATHER `direction_word` rows, ADJUDICATE
`direction` verdicts, EVALUATE `marking` verdicts -- the last only where the
record ran that far). python3 text_counts.py <shared-records dir> <base tag> <arm tag>
"""
import collections
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[3]))
from tools.omr.staged.record_io import load_record   # noqa: E402

root, base, arm = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
for doc in ("beethoven5-litolff", "brahms1-breitkopf"):
    print(f"== {doc}")
    for tag in (base, arm):
        path = root / f"{doc}-mvt1-whole-{tag}.record.json"
        if not path.exists():
            print(f"  {tag}: no record")
            continue
        rec = load_record(path)["record"]
        words = [o for o in rec["observations"] if o["quantity"] == "direction_word"]
        refused = collections.Counter(a.get("reason") for a in rec.get("abstentions", [])
                                      if a["quantity"] == "direction_word")
        texts = collections.Counter(str(o["value"]).lower().rstrip(".") for o in words)
        dirs = [v for v in rec["verdicts"] if v["quantity"] == "direction" and v.get("value")]
        marks = [m for v in rec["verdicts"] if v["quantity"] == "marking"
                 for m in (v.get("detail") or {}).get("markings", [])]
        reasons = collections.Counter(m.get("reason") for m in marks)
        print(f"  {tag}: words read {len(words)} (bars with words {len(dirs)}); "
              f"word refusals {dict(refused.most_common(4))}")
        print(f"      commonest: {texts.most_common(12)}")
        print(f"      markings: {len(marks)} {dict(reasons)}"
              + (f"  e.g. {[m['text'] for m in marks[:8]]}" if marks else ""))
