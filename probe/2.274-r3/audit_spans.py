from load import *   # noqa
import truth_p0 as T  # noqa


def spans(arm):
    xml = (WORK / ("brahms.%s.musicxml" % arm)).read_text()
    boxes = T.boxes_p0(WORK / ("brahms.%s.mini-record.json" % arm))
    out = []
    for a in A.arcs_of_xml(xml):
        if not a["start"].startswith("glyph/0/") or a["start"] not in boxes or a["stop"] not in boxes:
            continue
        sa, sz = a["start"].split("/")[2:4], a["stop"].split("/")[2:4]
        ba, bz = boxes[a["start"]], boxes[a["stop"]]
        out.append(dict(kind=a["kind"], staff="/".join(sa), same=sa == sz, cl=(ba[0] + ba[2]) / 2, cr=(bz[0] + bz[2]) / 2, yc=((ba[1] + ba[3]) / 2 + (bz[1] + bz[3]) / 2) / 2, start=a["start"], stop=a["stop"]))
    return out
