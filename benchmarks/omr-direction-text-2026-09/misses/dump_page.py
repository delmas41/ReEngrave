"""Gather ONE page through GATHER and pickle (pws, page_dict) so the direction-word
finder can be iterated offline.  python3 dump_page.py <pdf> <page> <tag> <outdir>"""
import os, pickle, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
os.environ["OMR_SURYA_KEEP_ALIVE"] = "0"
os.environ.pop("OMR_DIRECTION_TEXT_SCAN_GATE", None)
WEIGHTS = "omr-weights/deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt"

def main():
    pdf, page, tag, outdir = sys.argv[1:5]
    outdir = Path(outdir); outdir.mkdir(parents=True, exist_ok=True)
    from tools.omr.staged import gather as G
    def patched(log, pws, cells, local, detections):
        pd = G._direction_page_dict(pws, cells, local, detections)
        with open(outdir / f"{tag}.pkl", "wb") as f:
            pickle.dump((pws, pd), f)
    G.gather_direction_words = patched
    from tools.omr.staged.__main__ import main as sm
    sm([pdf, "--pages", page, "--weights", WEIGHTS, "--through", "gather"])
main()
