#!/bin/sh
# Regenerate every crop FINDINGS.md §1 is read from.
#
# `benchmarks/**/crops/` is gitignored repo-wide, so these are NOT in the tree.
# They are build products of the commands below and of the library store; each
# takes a few seconds.  Run from this benchmark's directory.
#
#   sh probe/regenerate_crops.sh
#
# ⚠️ `benchmarks/omr-brahms-lineup-2026-09/FINDINGS.md` states that its crops
# are "committed as 0a3c50f6".  They are not — `git ls-files` on that directory
# returns six files and no image.  Same ignore rule, same trap.

set -e
LIB=/Users/seanjohnson/Desktop/ReEngrave/library
BACH="$LIB/editions/bach/brandenburg-concerto-3-in-g-major-bwv1048/bach--brandenburg-concerto-3-in-g-major-bwv1048--edition-peters-nr-4412--imslp468678.pdf"
BEET="$LIB/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf"
BRAH="$LIB/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"
DVOR="$LIB/editions/dvorak/symphony-9-op95/dvorak--symphony-9-op95--simrock-1894--imslp405834.pdf"
MAHL="$LIB/editions/mahler/symphony-5/mahler--symphony-5--unidentified-scan-2016--local.pdf"

mkdir -p out/crops

# §1, the four left edges, as legible vertical strips
python3 probe/crop_left_edge.py "$BACH" --page 8  --system 0 --chunks 4 \
        --scale 1.4 --out out/crops/bach-p8-s0.png
python3 probe/crop_left_edge.py "$BRAH" --page 3  --system 0 --chunks 5 \
        --left 6 --right 4 --scale 2.2 --out out/crops/brahms-p3-s0.png
python3 probe/crop_left_edge.py "$DVOR" --page 6  --system 0 --chunks 5 \
        --left 5 --right 3 --scale 1.6 --out out/crops/dvorak-p6-s0.png
python3 probe/crop_left_edge.py "$MAHL" --page 5  --system 0 --chunks 5 \
        --left 5 --right 3 --scale 1.6 --out out/crops/mahler-p5-s0.png

# The three close reads the argument turns on: Litolff's single bracket past
# four instrument names, and the two Breitkopf gaps (one bracketed, one not).
python3 - "$BEET" "$BRAH" "$DVOR" <<'PY'
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]
                      if False else "/Users/seanjohnson/Desktop/ReEngrave/"
                      ".claude/worktrees/agent-aa1bd3b1a2dc3ca54"))
import cv2, numpy as np
from tools.omr.preprocessing import render_page

beet, brah, dvor = sys.argv[1], sys.argv[2], sys.argv[3]
out = pathlib.Path("out/crops")

pi = render_page(beet, 38, dpi=600)
c = pi.binary[400:1010, 200:520]
cv2.imwrite(str(out / "wide-p38-top.png"),
            cv2.resize(c, (c.shape[1]*2, c.shape[0]*2),
                       interpolation=cv2.INTER_NEAREST))

pi = render_page(brah, 3, dpi=600)
for name, (y0, y1) in (("brahms-p3-gap8.png", (2380, 2740)),
                       ("brahms-p3-gap2.png", (1080, 1300))):
    c = pi.binary[y0:y1, 590:760]
    cv2.imwrite(str(out / name),
                cv2.resize(c, (c.shape[1]*3, c.shape[0]*3),
                           interpolation=cv2.INTER_NEAREST))

pi = render_page(dvor, 6, dpi=600)
a = pi.binary[1080:1340, 330:440]
b = pi.binary[2250:2480, 330:440]
big = np.hstack([
    cv2.resize(a, (330, 780), interpolation=cv2.INTER_NEAREST)[:660],
    np.full((660, 20), 128, np.uint8),
    cv2.resize(b, (330, 690), interpolation=cv2.INTER_NEAREST)[:660]])
cv2.imwrite(str(out / "dvorak-gaps-3-and-9.png"), big)
print("wrote the close reads")
PY

echo "crops regenerated in out/crops/"
