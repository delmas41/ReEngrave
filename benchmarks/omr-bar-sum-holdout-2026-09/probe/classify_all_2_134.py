"""ROADMAP 2.134: run classify_held_2_96.py (unchanged) on a split dump:
held (the 2.96 question), the SAME held bars with a deliberately wrong meter
(+0.3 quarter; the control that must collapse the evidenced share), and partial.

    python3 .../classify_all_2_134.py <dir> <label> '<truth json>' <doubled> <held_sum>
"""
import json
import subprocess
import sys
from pathlib import Path

d, label, truth, doubled, held_sum = sys.argv[1:6]
d = Path(d)
K = str(Path(__file__).resolve().parent / "classify_held_2_96.py")
tj = json.loads(truth)
wrong = {k: float(v) + 0.3 for k, v in tj.items()}
n_part = len(json.load(open(d / f"{label}-partial.json"))["bars"])
jobs = [("held", "part", tj, int(doubled), int(held_sum)),
        ("held", "negctl", wrong, int(doubled), int(held_sum)),
        ("partial", "part", tj, 0, n_part)]
for kind, tag, tr, dbl, exp in jobs:
    out = d / f"{label}-{kind}-{tag}.json"
    r = subprocess.run([sys.executable, K, str(d / f"{label}-{kind}.json"),
                        "--truth", json.dumps(tr), "--doubled", str(dbl),
                        "--expect-total", str(exp), "--out", str(out)],
                       capture_output=True, text=True)
    (d / f"{label}-{kind}-{tag}.txt").write_text(r.stdout + r.stderr)
    print(kind, tag, "rc", r.returncode, r.stdout.splitlines()[0] if r.stdout else r.stderr[-300:])
