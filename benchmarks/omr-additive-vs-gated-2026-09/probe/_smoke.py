"""Runs every probe in this directory and reports which succeed. Regression
check on the tooling, not on the pipeline."""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
os.environ.setdefault("OMR_FIXTURE_ROOT", "/Users/seanjohnson/Desktop/ReEngrave")

NAMES = [
    "probe_gate_reach", "probe_register_warning", "probe_clef_proposals",
    "probe_propose_clef_branches", "probe_fill_population",
    "probe_clef_provenance_gate", "probe_dynamic_runs", "probe_low_labels",
    "probe_absent_veto_scale", "analyse_contests",
]

bad = 0
for name in NAMES:
    r = subprocess.run([sys.executable, os.path.join(HERE, name + ".py")],
                       capture_output=True, cwd=HERE)
    ok = r.returncode == 0 and r.stdout.strip()
    print(("OK   " if ok else "FAIL ") + name)
    if not ok:
        bad += 1
        print(r.stderr.decode()[-500:])
sys.exit(1 if bad else 0)
