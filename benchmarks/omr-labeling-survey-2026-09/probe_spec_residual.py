"""For each specialist family: how much of its OWN symbol is unboxed in its own
corpus? A miss inside a swept cell is a hard negative aimed straight at the one
class the specialist exists for."""
import json, sys, os, glob, collections
sys.path.insert(0, os.getcwd())
import cv2
from tools.omr.yolo_detector import YoloDetector, imgsz_for_cell

W = "/Users/seanjohnson/Desktop/ReEngrave/omr-weights/deepscoresv2-yolov8l-hollow-ft-2026-09-03.pt"
names = json.load(open("tools/omr/training/deepscoresv2_208_classes.json"))
FAM = {
 "hollow": {"noteheadHalfOnLine","noteheadHalfInSpace","noteheadWholeOnLine","noteheadWholeInSpace"},
 "ties": {"tie"}, "slurs": {"slur"},
 "rests": {"restWhole","restHalf","restQuarter","rest8th","rest16th","restHBar"},
 "accidentals": {"accidentalFlat","accidentalNatural","accidentalSharp"},
}
det = YoloDetector(W, device="mps")
class C:
    def __init__(s, ys, im): s.staff_line_ys_canonical = ys; s.image = im
mans = {}
for m in glob.glob("benchmarks/**/*cells.json", recursive=True):
    try:
        for e in json.load(open(m)):
            mans.setdefault(e["cell_id"], e)
    except Exception:
        pass
print(f"{'family':13s}{'cells':>7s}{'human':>8s}{'teacher':>9s}{'unboxed':>9s}{'% unboxed':>11s}")
for fam, cls in FAM.items():
    root = f"data/specialist-{fam}"
    if not os.path.isdir(root): continue
    human = teacher = cells = 0
    for lab in glob.glob(f"{root}/v*/labels/*.txt"):
        cid = os.path.basename(lab)[:-4]
        img = cv2.imread(lab.replace("/labels/", "/images/")[:-4] + ".png")
        if img is None: continue
        cells += 1
        human += sum(1 for l in open(lab) if l.strip())
        ys = (mans.get(cid) or {}).get("staff_line_ys_canonical") or []
        c = C(ys, img)
        teacher += sum(1 for d in det.detect(c, conf_threshold=0.25, imgsz=imgsz_for_cell(c))
                       if d.smufl_name in cls)
    unb = max(0, teacher - human)
    print(f"{fam:13s}{cells:7d}{human:8d}{teacher:9d}{unb:9d}{(unb/teacher*100 if teacher else 0):10.0f}%")
