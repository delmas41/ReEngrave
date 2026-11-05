"""2.229: export a saved record's OWN verdicts (no re-adjudication) restricted to the loaded pages, through lane_report's traced export + parser.
usage: export_saved.py RECORD WORKDIR PLATE LOADEDPAGES TAG [COUNTPAGES]

ROADMAP 2.265: with COUNTPAGES (the sample pages; LOADEDPAGES also holds each plate's context page) the context pages are loaded for the
header they carry and never counted (`counted_view`): their ARC and DOT family rows are dropped before the export, the written file's
symbols / red bars / blue marks / notes-not-written are taken over the counted pages, and `PLATE.TAG.specks.json` lists every dot-class box
whose ink is under the stroke floor. Without COUNTPAGES every loaded page is counted, exactly as before 2.265."""
import json
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[4]))  # repo root, so `tools` imports
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import counted_view as CV                                      # noqa: E402


def main(argv):
    from tools.omr.staged import lane_report as L, export as E
    from tools.omr.staged.record_io import load_record
    rec, work, plate, pages, tag = argv[0], pathlib.Path(argv[1]), argv[2], {int(x) for x in argv[3].split(",")}, argv[4]
    count_pages = {int(x) for x in argv[5].split(",")} if len(argv) > 5 else set(pages)
    t0 = time.time()
    res = load_record(rec)
    r = res["record"] if "record" in res else res
    if "record" not in res:
        res = {"record": res, "summary": {}}
    keep = lambda it: (lambda pg: pg is None or pg in pages)(L.page_of(it.get("subject")))
    for k in ("observations", "abstentions", "verdicts"):
        r[k] = [x for x in r[k] if keep(x)]
    boxes = L.glyph_boxes(r["observations"])
    specks = CV.dot_specks(E.Record(res), count_pages)
    left_out = CV.drop_context_marks(r, pages - count_pages)
    with L.traced_export():
        xml, report = E.to_musicxml(res)
    sym = L.parse_symbols(xml, boxes)
    hosts, loose, red_n, blue_n, nnw = CV.counted_symbols(sym["hosts"], sym["loose"], report, count_pages)
    red = report.get("bars_written_red") or {}
    out = dict(plate=plate, arm=tag, mode="saved", hosts=hosts, loose=loose, count_pages=sorted(count_pages), loaded_pages=sorted(pages),
               red_bars=red_n, bars_held_out=L._count(report.get("bars_held_out_sum")), notes_not_written=nnw,
               blue_marks=blue_n, seconds=round(time.time() - t0, 1),
               before_2_265=dict(red_bars=L._count(red.get("bars") if isinstance(red, dict) else red), blue_marks=xml.count('color="%s"' % E.GUESS_COLOR),
                                 notes_not_written=report.get("notes_not_written_total")),
               context_rows_left_out=left_out)
    work.mkdir(parents=True, exist_ok=True)
    (work / ("%s.%s.musicxml" % (plate, tag))).write_text(xml)
    (work / ("%s.%s.symbols.json" % (plate, tag))).write_text(json.dumps(out, default=str))
    (work / ("%s.%s.report.json" % (plate, tag))).write_text(json.dumps(report, default=str))
    (work / ("%s.%s.specks.json" % (plate, tag))).write_text(json.dumps(dict(floor_sp2=CV.SPECK_FLOOR_SP2, count_pages=sorted(count_pages), specks=specks), default=str))
    print("done", plate, tag, len(hosts), "hosts", out["seconds"], "s;", len(specks), "dot specks; context rows left out", sum(left_out.values()))


if __name__ == "__main__":
    main(sys.argv[1:])
