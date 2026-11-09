"""Load a saved staged record slim (drop `considered`/`correlated`), index it with export.Record. READ-ONLY."""
import sys, json, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.omr.staged.record_io import expand_result
from tools.omr.staged import export as EXPORT

BRAHMS = "/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records/brahms1-breitkopf-mvt1-whole-m4b-sample.record.json"
LITOLFF = "/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records/beethoven5-litolff-mvt1-whole-m4b-sample.record.json"


def load(path):
    def _hook(o):
        if "quantity" in o and "outcome" in o:
            o.pop("considered", None); o.pop("correlated", None)
        return o
    t = time.time()
    d = expand_result(json.loads(Path(path).read_text(), object_hook=_hook))
    print("loaded", path.split("/")[-1], round(time.time() - t, 1), "s", flush=True)
    return d, EXPORT.Record(d)
