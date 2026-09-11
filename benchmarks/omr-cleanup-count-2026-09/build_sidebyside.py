"""The print beside the output, one printed SYSTEM at a time.

    python3 benchmarks/omr-cleanup-count-2026-09/build_sidebyside.py --tag p1-p4

Left: a crop of the scanned system. Right: our exported MusicXML for exactly
those bars, engraved by Verovio on ONE system so the two line up bar for bar.

⚠️ THE CROP COMES FROM THE PIPELINE'S OWN PAGE RASTER, not from a fresh
`fitz` render at a guessed DPI. `preprocessing.render_page` DESKEWS, so a
re-render at the same nominal DPI is a DIFFERENT image and the staff-line
y-values on the record would land a few pixels off the ink. Cropping the array
the pipeline read means the band is exactly the band the record is describing.
This repo's recurring instrument failure is a control in the wrong frame; a
mis-framed crop would not raise, it would just look like a slightly wrong
reading of the music -- which is what the human is being asked to judge.

⚠️ `breaks="none"` on the Verovio render is not cosmetic. The print shows one
system; forcing our side onto one system makes "the fourth bar" mean the same
thing on both halves of the page. Without it Verovio wraps where it likes and
the human has to re-find their place at every row.
"""
from __future__ import annotations

import argparse
import base64
import html
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))

PDF = (ROOT / "library/editions/beethoven/symphony-5-op67/"
       "beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf")

CROP_PAD_PX = 60
# ⚠️ NATIVE-ISH, DELIBERATELY. A 12-staff conductor system scaled to fit a
# browser column gives each staff ~60 px and the human cannot judge a notehead
# at that size -- which would make the artefact look complete and be useless.
# The crop is written near full resolution and displayed at `width:100%`, so
# the page reads as a strip and ZOOMING gives back the detail.
CROP_MAX_W = 2800


# ── the scan side ────────────────────────────────────────────────────────────

def system_bands(result):
    """{(page, system): (x0, y0, x1, y1)} in the pipeline's page-pixel frame."""
    bands = {}
    for o in result["record"]["observations"]:
        sub = o["subject"]
        parts = sub.split("/")
        if o["quantity"] == "staff_lines" and parts[0] == "staff":
            page, sysi = int(parts[1]), int(parts[2])
            ys = [float(y) for y in o["value"]]
            b = bands.setdefault((page, sysi), [None, min(ys), None, max(ys)])
            b[1], b[3] = min(b[1], min(ys)), max(b[3], max(ys))
        elif o["quantity"] == "cell_box" and parts[0] == "cell":
            page, sysi = int(parts[1]), int(parts[2])
            x0, _y0, x1, _y1 = [float(v) for v in o["value"]]
            b = bands.setdefault((page, sysi), [x0, None, x1, None])
            b[0] = x0 if b[0] is None else min(b[0], x0)
            b[2] = x1 if b[2] is None else max(b[2], x1)
    return {k: tuple(v) for k, v in bands.items()
            if all(x is not None for x in v)}


def crop_system(page_rgb, band, out_path):
    x0, y0, x1, y1 = band
    h, w = page_rgb.shape[:2]
    x0 = max(0, int(x0) - CROP_PAD_PX)
    y0 = max(0, int(y0) - CROP_PAD_PX)
    x1 = min(w, int(x1) + CROP_PAD_PX)
    y1 = min(h, int(y1) + CROP_PAD_PX)
    arr = page_rgb[y0:y1, x0:x1]
    im = Image.fromarray(arr.astype(np.uint8)).convert("L")
    if im.width > CROP_MAX_W:
        im = im.resize((CROP_MAX_W, max(1, round(im.height * CROP_MAX_W / im.width))),
                       Image.LANCZOS)
    im.save(out_path, optimize=True)
    return (x0, y0, x1, y1), im.size


# ── the output side ──────────────────────────────────────────────────────────

_ATTR_ORDER = ("divisions", "key", "time", "staves", "clef")


def slice_measures(xml_text, wanted):
    """A complete score-partwise holding only `wanted` = {part_id: (lo, hi)}.

    ⚠️ The exporter writes `<attributes>` only where something CHANGED, and
    "changed" is measured from the start of the PART, not of the system. So a
    system that is not a part's first will often open with no clef, key or
    divisions at all -- and a slice that simply cut there would render in
    treble, in C, at the wrong note lengths, and every one of those would look
    like a reading error to the human. The last-seen attributes are carried
    forward and injected. That is a property of the SLICE and not of the file,
    and this docstring is where it is recorded.
    """
    root = ET.fromstring(xml_text)
    out = ET.Element("score-partwise", {"version": "3.1"})
    for tag in ("work", "identification", "defaults"):
        el = root.find(tag)
        if el is not None:
            out.append(el)
    plist_src = root.find("part-list")
    plist = ET.SubElement(out, "part-list")
    keep_order = []
    for sp in plist_src.findall("score-part"):
        if sp.get("id") in wanted:
            plist.append(sp)
            keep_order.append(sp.get("id"))

    for pid in keep_order:
        lo, hi = wanted[pid]
        src = next(p for p in root.findall("part") if p.get("id") == pid)
        dst = ET.SubElement(out, "part", {"id": pid})
        carried = {}
        first = True
        kept = []
        for m in src.findall("measure"):
            n = int(m.get("number"))
            att = m.find("attributes")
            if n < lo:
                if att is not None:
                    for child in att:
                        if child.tag in _ATTR_ORDER:
                            carried[child.tag] = child
                continue
            if n > hi:
                break
            m = ET.fromstring(ET.tostring(m))       # copy, never mutate the source
            if first:
                att = m.find("attributes")
                have = {c.tag for c in att} if att is not None else set()
                need = [t for t in _ATTR_ORDER if t in carried and t not in have]
                if need:
                    if att is None:
                        att = ET.Element("attributes")
                        m.insert(0, att)
                    for i, t in enumerate(need):
                        att.insert(i, carried[t])
                first = False
            kept.append(m)
        # ⚠️⚠️ RENUMBERED 1..n WITHIN THE SLICE, AND THE REASON IS A REAL
        # DEFECT IN THE FILE RATHER THAN A RENDERING PREFERENCE. A part whose
        # staff is SUPPRESSED on a system gets no measures for those bars, so
        # from Litolff p.4 onward P9-P11 are eighteen bars behind P1-P8 and
        # `<measure number="82">` names a different instant in different
        # parts. Verovio says so out loud -- `Mismatching measure number 87`
        # -- and would drop measures rather than render them.
        #
        # The slice therefore aligns by ORDINAL, which is what the PRINT does:
        # the fourth bar of this system is the fourth bar of this system on
        # every staff. That is right for looking at, and it is NOT a repair --
        # the file still carries the defect and FINDINGS.md §3 records it. A
        # staff that genuinely read a different NUMBER of bars still comes out
        # visibly short here, which is the one thing this alignment must not
        # hide.
        for i, m in enumerate(kept, 1):
            m.set("number", str(i))
            dst.append(m)
    return ET.tostring(out, encoding="unicode")


def render_svg(tk, xml_text, page_width):
    tk.setOptions({
        "pageWidth": page_width, "pageHeight": 60000,
        "scale": 33, "adjustPageHeight": True, "breaks": "none",
        "footer": "none", "header": "none",
        "pageMarginLeft": 20, "pageMarginRight": 20,
        "pageMarginTop": 20, "pageMarginBottom": 20,
        "spacingStaff": 6, "spacingSystem": 4,
    })
    if not tk.loadData(xml_text):
        return None
    return tk.renderToSVG(1)


# ── the page ─────────────────────────────────────────────────────────────────

CSS = """
:root{color-scheme:light}
body{margin:0;font:14px/1.45 -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
     background:#f6f5f2;color:#1a1a1a}
header{position:sticky;top:0;background:#fffdf8;border-bottom:2px solid #d8d2c4;
       padding:14px 22px;z-index:9}
h1{margin:0 0 4px;font-size:17px}
.sub{color:#5d5648;font-size:13px}
main{padding:18px 22px 120px;max-width:1900px}
section{background:#fff;border:1px solid #ddd7c9;border-radius:6px;margin:0 0 26px;
        overflow:hidden;box-shadow:0 1px 2px rgba(0,0,0,.05)}
.head{display:flex;gap:18px;align-items:baseline;flex-wrap:wrap;
      padding:10px 14px;background:#f3efe4;border-bottom:1px solid #ddd7c9}
.head b{font-size:15px}
.rank{background:#3b3226;color:#fff;border-radius:11px;padding:1px 9px;font-size:12px}
.why{color:#6a6254;font-size:12.5px}
.pane{padding:10px 14px}
.lbl{font-size:11px;letter-spacing:.09em;text-transform:uppercase;color:#8a8272;
     margin:2px 0 6px}
.scan img{width:100%;border:1px solid #e4ded0;background:#fff}
.ours{overflow-x:auto;background:#fff}
.ours svg{max-width:100%;height:auto}
table.facts{border-collapse:collapse;font-size:12.5px;margin:6px 0 2px}
table.facts td,table.facts th{border:1px solid #e6e0d2;padding:3px 8px;text-align:left}
table.facts th{background:#faf7ef;font-weight:600}
.msg{background:#fff8e6;border-left:3px solid #d9a441;padding:7px 11px;
      font-size:12.5px;margin:8px 0}
.msg.bad{background:#fdecec;border-left-color:#c0504d}
code{background:#f1ede2;padding:1px 4px;border-radius:3px;font-size:12px}
"""


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="p1-p4")
    ap.add_argument("--out-dir", default=str(HERE / "out"))
    ap.add_argument("--dpi", type=int, default=600)
    args = ap.parse_args(argv)

    out = Path(args.out_dir)
    crops = out / "crops"
    crops.mkdir(parents=True, exist_ok=True)

    result = json.loads((out / f"record-{args.tag}.json").read_text())
    xml_text = (out / f"beethoven5-mvt1-{args.tag}.musicxml").read_text()
    smap = json.loads((out / f"system-map-{args.tag}.json").read_text())
    props = json.loads((out / f"proposals-{args.tag}.json").read_text())
    by_sys = {(p["page"], p["system"]): p for p in props["systems"]}

    bands = system_bands(result)

    import verovio
    from tools.omr import preprocessing
    tk = verovio.toolkit()

    rows = []
    rendered = {}
    for entry in smap["systems"]:
        page, sysi = entry["page"], entry["system"]
        key = (page, sysi)
        band = bands.get(key)
        crop_rel = None
        crop_px = None
        if band is not None:
            if page not in rendered:          # two systems share one page render
                rendered.clear()              # one page in memory at a time
                rendered[page] = preprocessing.render_page(PDF, page, dpi=args.dpi)
            pi = rendered[page]
            name = f"p{page}-s{sysi}.png"
            crop_px, size = crop_system(pi.rgb, band, crops / name)
            # ⚠️ EMBEDDED, not linked. The repo's root .gitignore excludes
            # `benchmarks/**/crops/` -- rasters are build products here -- so a
            # linked crop would leave the committed HTML showing seven broken
            # images to anyone who had not re-run the gather, which is the one
            # reader this artefact is FOR. One self-contained file instead.
            crop_rel = ("data:image/png;base64,"
                        + base64.b64encode((crops / name).read_bytes()).decode())
        wanted = {r["part_id"]: (r["first_measure"], r["last_measure"])
                  for r in entry["staves"]}
        svg = None
        err = None
        try:
            svg = render_svg(tk, slice_measures(xml_text, wanted), 3000)
        except Exception as exc:                       # noqa: BLE001
            err = f"{type(exc).__name__}: {exc}"
        # ⚠️ THE CONTROL ON THE ENGRAVED HALF. Verovio silently DROPS what it
        # cannot place -- it printed "Mismatching measure number 87" and kept
        # going before the slice was renumbered -- so a row could look
        # complete while showing fewer notes than the file holds, and the
        # human would count real music as missing. The glyph count in the SVG
        # is compared with the count in the FILE for exactly these bars, and a
        # disagreement is shown as a banner on that row rather than logged.
        drawn_notes = svg.count('class="note"') if svg else 0
        drawn_rests = (svg.count('class="rest"') + svg.count('class="mRest"')
                       + svg.count('class="multiRest"')) if svg else 0
        rows.append({"drawn_notes": drawn_notes, "drawn_rests": drawn_rests,
                     "page": page, "system": sysi, "staves": entry["staves"],
                     "crop": crop_rel, "crop_px": crop_px, "svg": svg,
                     "svg_error": err, "prop": by_sys.get(key, {})})

    rows.sort(key=lambda r: (-(r["prop"].get("attention_score") or 0),
                             r["page"], r["system"]))

    parts_html = ['<meta charset="utf-8">',
                  f"<style>{CSS}</style>",
                  "<header><h1>Beethoven 5, movement 1 — Litolff 1870 (IMSLP 984073) "
                  "— the print beside our output</h1>",
                  f"<div class='sub'>{len(rows)} printed systems, ordered by "
                  "the MACHINE'S PROPOSED attention, highest first — "
                  "<b>a proposal, not a count</b>. "
                  f"Record: <code>record-{args.tag}.json</code>, "
                  f"commit <code>{(result.get('provenance') or {}).get('commit')}</code>, "
                  f"dirty=<code>{(result.get('provenance') or {}).get('dirty')}</code>."
                  "</div></header><main>"]

    for i, r in enumerate(rows, 1):
        p = r["prop"]
        parts_html.append("<section>")
        parts_html.append(
            f"<div class='head'><span class='rank'>#{i}</span>"
            f"<b>page {r['page']}, system {r['system']}</b>"
            f"<span class='why'>{len(r['staves'])} staves exported &middot; "
            f"{html.escape(str(p.get('why', '')))}</span></div>")
        parts_html.append("<div class='pane'>")
        parts_html.append("<div class='lbl'>the print</div><div class='scan'>")
        if r["crop"]:
            parts_html.append(
                f"<a href='{r['crop']}' target='_blank' title='open full size'>"
                f"<img src='{r['crop']}'></a>")
        else:
            parts_html.append("<div class='msg bad'>no crop: the record carries "
                              "no page-pixel band for this system.</div>")
        parts_html.append("</div>")
        parts_html.append("<div class='lbl'>our output, the same bars</div>"
                          "<div class='ours'>")
        if r["svg"]:
            parts_html.append(r["svg"])
        else:
            parts_html.append(f"<div class='msg bad'>Verovio did not render this "
                              f"slice: {html.escape(str(r['svg_error']))}</div>")
        parts_html.append("</div>")
        want_n, want_r = p.get("notes_written"), p.get("rests_written")
        if r["svg"] and (r["drawn_notes"] != want_n or r["drawn_rests"] != want_r):
            parts_html.append(
                f"<div class='msg bad'>⚠️ the engraved half does NOT show "
                f"everything the file holds: drawn {r['drawn_notes']} notes / "
                f"{r['drawn_rests']} rests against {want_n} / {want_r} in the "
                f"file for these bars. Count from the FILE, not from this "
                f"picture, until that is explained.</div>")
        elif r["svg"]:
            parts_html.append(
                f"<div class='msg'>control: the engraved half draws exactly "
                f"what the file holds for these bars — {want_n} notes, "
                f"{want_r} rests.</div>")

        parts_html.append("<div class='lbl'>what the machine PROPOSES here "
                          "(never a count)</div><table class='facts'>"
                          "<tr><th>fact</th><th>value</th></tr>")
        for k in ("staves_printed", "bars_printed_range",
                  "bars_printed_minus_bars_read",
                  "bars_printed_per_staff", "bars_exported",
                  "proposed_missing_staff_systems",
                  "parts_disagree_about_the_bar_by",
                  "proposed_missing_bars_nothing_read",
                  "proposed_missing_notes_held_back",
                  "proposed_spurious_arpeggiato_detections",
                  "notes_written", "rests_written", "arcs_written",
                  "attention_score"):
            if k in p:
                parts_html.append(f"<tr><td>{k}</td><td>{html.escape(str(p[k]))}</td></tr>")
        parts_html.append("</table>")
        names = ", ".join(f"{s['part_name']} (m{s['first_measure']}-{s['last_measure']})"
                          for s in r["staves"])
        parts_html.append(f"<div class='why'>staves, top to bottom: "
                          f"{html.escape(names)}</div>")
        parts_html.append("</div></section>")

    parts_html.append("</main>")
    (out / f"side-by-side-{args.tag}.html").write_text("\n".join(parts_html))
    print(f"wrote {out / f'side-by-side-{args.tag}.html'}  systems={len(rows)}  "
          f"crops={sum(1 for r in rows if r['crop'])}  "
          f"rendered={sum(1 for r in rows if r['svg'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
