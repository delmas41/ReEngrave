"""ROADMAP 2.68 (dynamic owner): every bar whose ADJUDICATE `dynamic` verdict changed between the letter-neighbour branch
(B0, 0aa1181c + main) and this lane (A1), cut BLIND for Sean -- the bar outlined in blue on its own staff (staff named),
nothing of ours drawn. Bars Sean already judged (../2.68-dynamics-back) and the five the letter-neighbour lane rendered
(../2.68-dynamics-fix) are left out; they are re-scored in FINDINGS instead.
python3 render.py <A1 out/out dir> <B0 out/out dir>  -> dyn_NN.png, manifest.json, changed.json"""
import json, os, sys
import fitz
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
from tools.omr.staged import readout
HERE = os.path.dirname(os.path.abspath(__file__))
A1, B0 = sys.argv[1], sys.argv[2]
LIB = os.path.join(HERE, "../../../library/editions")
DOCS = [("litolff", "beethoven5-litolff/beethoven5-litolff-p3.record.json",
         "beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf", "Beethoven 5 (Litolff)"),
        ("brahms", "brahms1-breitkopf/brahms1-breitkopf-p1.record.json",
         "brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf", "Brahms 1 (Breitkopf)")]
font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 32)
judged = {t["cell"] for d in ("../2.68-dynamics-back", "../2.68-dynamics-fix")
          for t in json.load(open(os.path.join(HERE, d, "manifest.json")))["tiles"]}


def dyn(run):
    return {v["subject"]: v.get("value") for v in run.verdicts
            if v.get("quantity") == "dynamic" and v["subject"].startswith("cell/") and isinstance(v.get("value"), list)}


man, changed, n = [], [], 0
for tag, rec, pdf, title in DOCS:
    run = readout.load_run(os.path.join(A1, rec)); old = readout.load_run(os.path.join(B0, rec))
    da, db = dyn(run), dyn(old)
    doc = fitz.open(os.path.join(LIB, pdf))
    for k in sorted(set(da) | set(db), key=readout._subject_sort_key):
        if (da.get(k) or []) == (db.get(k) or []):
            continue
        changed.append({"doc": tag, "cell": k, "before": db.get(k) or [], "after": da.get(k) or [], "judged_before": k in judged})
        if k in judged:
            continue
        n += 1; _, p, sy, st, c = k.split("/")
        x0, y0, x1, y1 = run.obs_at(k, "cell_box")[0]["value"]
        lines = run.obs_at(f"staff/{p}/{sy}/{st}", "staff_lines")[0]["value"]
        sp = (lines[-1] - lines[0]) / 4.0
        inst = (run.standing(f"staff/{p}/{sy}/{st}", "instrument", "ADJUDICATE") or {}).get("value") or {}
        name = inst.get("name") if isinstance(inst, dict) else None
        cx0, cx1 = x0 - 6 * sp, x1 + 6 * sp; cy0, cy1 = lines[0] - 9 * sp, lines[-1] + 9 * sp
        Z = 2 if sp < 25 else 1
        clip = fitz.Rect(cx0 * 72 / 600, cy0 * 72 / 600, cx1 * 72 / 600, cy1 * 72 / 600)
        pix = doc[int(p)].get_pixmap(dpi=600 * Z, clip=clip)
        im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples); d = ImageDraw.Draw(im)
        d.rectangle([(x0 - cx0) * Z, (lines[0] - cy0 - sp) * Z, (x1 - cx0) * Z, (lines[-1] - cy0 + sp) * Z], outline=(30, 90, 230), width=5)
        out = Image.new("RGB", (im.width, im.height + 100), "white"); out.paste(im, (0, 100)); dd = ImageDraw.Draw(out)
        dd.text((10, 8), f"Dynamics tile {n} -- {title}, page {int(p) + 1}", fill="black", font=font)
        dd.text((10, 50), f"Blue box = one bar on the {name or 'unnamed'} staff", fill=(30, 90, 230), font=font)
        f = f"dyn_{n:02d}.png"; out.save(os.path.join(HERE, f))
        man.append({"n": n, "doc": tag, "cell": k, "staff_name": name, "before": db.get(k) or [], "after": da.get(k) or [], "file": f})
json.dump({"question": "What dynamic markings are printed for this staff in the blue bar?", "tiles": man},
          open(os.path.join(HERE, "manifest.json"), "w"), indent=1)
json.dump(changed, open(os.path.join(HERE, "changed.json"), "w"), indent=1)
print(len(changed), "cells changed;", n, "rendered;", sum(c["judged_before"] for c in changed), "already judged/rendered")
