"""2.306 r13 study: shared helpers over the pickle `load.py` writes. OLD = cell join (OFF arm verdicts); NEW = Q.PAGE_STEM as gathered."""
import pickle, collections

S = "/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-project-mgmt-pipeline-review-e6581e/77ea0805-f478-4ed7-b4b6-89b2b63b5322/scratchpad"
LIB = "/Users/seanjohnson/Desktop/ReEngrave/library/"
PDF = dict(lit=LIB + "editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
           bra=LIB + "editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf")
NAME = dict(lit="litolff", bra="brahms")


def load(plate):
    return pickle.load(open("%s/r13/%s.pkl" % (S, plate), "rb"))


def pg(s):
    return int(s.split("/")[1])


def cell_of(g):
    p = g.split("/")
    return "cell/" + "/".join(p[1:5])


def staff_of(g):
    p = g.split("/")
    return "staff/" + "/".join(p[1:4])


def cell_up(D):
    """{cell: (ox, oy, up)} canonical -> page: page = o + canonical / up. From any head box of the cell (its canonical and page boxes)."""
    out = {}
    for g, h in D["heads"].items():
        c = cell_of(g)
        if c in out or c not in D["cellbox"]:
            continue
        b, can = h["box"], h["can"]
        if can[2] > 0 and b[2] > b[0]:
            up = can[2] / (b[2] - b[0])
            out[c] = (b[0] - can[0] / up, b[1] - can[1] / up, up)
    return out


def stem_page_box(D, ups, sid):
    st = D["stems"].get(sid)
    if st is None or st["cell"] not in ups:
        return None
    ox, oy, up = ups[st["cell"]]
    x, y, w, h = st["can"]
    return [ox + x / up, oy + y / up, ox + (x + w) / up, oy + (y + h) / up]


def is_real(D, g, arm="on"):
    """A head of its own staff that ADJUDICATE did not refuse as a non-note (the lane's `nostem9.real`)."""
    V = D["V_" + arm].get(g) or {}
    n = V.get("notehead_is_not_a_notehead")
    if n and n["o"] == "decided" and n["v"] is True:
        return False
    o = V.get("glyph_owner")
    if o and o["o"] == "decided" and isinstance(o["v"], str) and o["v"] != staff_of(g):
        return False
    return "head_stem" in V


def old_answer(D, g):
    V = D["V_off"].get(g) or {}
    hs, sd = V.get("head_stem") or {}, V.get("stem_direction") or {}
    return dict(stem=hs.get("v") if hs.get("o") == "decided" else None, join=hs.get("o"), why=hs.get("r"), detail=hs.get("d") or {},
                direction=sd.get("v") if sd.get("o") == "decided" else None, dir_why=sd.get("r"))


def new_answer(D, g):
    p = D["pstem"].get(g)
    if p is None:
        return dict(read=None, how="no page reading", direction=None, stroke=None, row={})
    return dict(read=bool(p["read"]), how=p.get("how"), direction=p.get("direction"), stroke=p.get("page_stroke"), row=p)


def staff_sp(D, g):
    ln = D["staff_lines"].get(staff_of(g))
    if ln and len(ln) >= 5:
        return (ln[-1] - ln[0]) / 4.0
    return 16.0
