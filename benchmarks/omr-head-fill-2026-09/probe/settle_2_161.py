"""ROADMAP 2.161 -- Sean settled Set G tile 3 (Brahms glyph/5/0/2/3/2), 2026-10-17: "That is a quarter note". Records it
as "4" superseding his "1" on that tile, and rewrites FINDINGS 17.7's tile-3 paragraph.
usage: settle_2_161.py"""
import json

p = "out/print/2.161-review/answers.json"
a = json.load(open(p))
for t in a["tiles"]:
    if t["n"] == 3:
        t["sean"] = "4"
        t["verdict"] = "control right"
        t["supersedes"] = {"sean": "1", "note": 'Sean 2026-10-17, settling his 2.154 "4" vs Set G "1" on this head: '
                                               '"That is a quarter note"'}
a["corrections"] = [{"tile": 3, "from": "1", "to": "4", "sean": "That is a quarter note", "date": "2026-10-17"}]
json.dump(a, open(p, "w"), indent=1)

p = "benchmarks/omr-head-fill-2026-09/FINDINGS.md"
s = open(p).read()
i = s.index("**Control tile 3 (Brahms `glyph/5/0/2/3/2`)")
s = s[:i] + """**Control tile 3 (Brahms `glyph/5/0/2/3/2`): right.** Sean first wrote 1 (a whole) on this tile, against his own "4" on
the same head at 2.154-review tile 4; asked, he settled it (2026-10-17): "That is a quarter note". Recorded as "4" (the "1"
kept in answers.json as superseded); the index holds one answer for the head, 4. We write a quarter (decided,
`stem_tip_reads_no_beam`, both replay arms; the flag does not touch it): detector `noteheadBlackInSpace` (0.80), 2.148 slit
0.00, 2.23 centre window 1.00 -- right. Crop: `out/print/2.161-diagnosis/11-brahms-5-0-2-3-2-tile4-of-2.154-vs-tile3-of-2.161.png`.
Both controls right; no error found.
"""
open(p, "w").write(s)
print("ok")
