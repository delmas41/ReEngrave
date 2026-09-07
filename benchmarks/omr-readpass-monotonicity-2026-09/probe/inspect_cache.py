"""What is in a compose.py read-pass cache: per page, staves and margin labels."""
import pickle, sys, collections
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from tools.omr.slots import MIN_LABEL_CONFIDENCE  # noqa

root = Path(sys.argv[1])
rows = []
tot_matched = tot_conf = tot_all = 0
for blob in sorted(root.glob("p*.pkl")):
    pi = int(blob.stem[1:])
    pws, labels = pickle.loads(blob.read_bytes())
    m = [l for l in labels if l.matched]
    c = [l for l in m if l.confidence in MIN_LABEL_CONFIDENCE]
    tot_all += len(labels); tot_matched += len(m); tot_conf += len(c)
    rows.append((pi, len(pws.staves), len(labels), len(m), len(c)))
print(f"pages={len(rows)} labels_all={tot_all} matched={tot_matched} conf={tot_conf}")
for r in rows[:5]: print(r)
