"""2.152 -- the three context facts computed OFF the slim record (extract.py). GATHER-side only; nothing decides.

P1 page glyph census   w/h of a box in staff spaces vs this PAGE's own confident instances of its class (leave-one-out
                       median / MAD). 'confident' = kept by its gate (notehead_is_not_a_notehead False / rest_is_not_a_rest
                       False) AND detector score >= CONF AND (heads) a DECIDED duration. Built from the SAME raster's
                       readings: not an independent witness (CLAUDE.md §4).
S1 system band         v: centre more than VBAND sp outside its own staff's five lines; h: a head/rest box in cell 0 whose
                       centre is left of the right edge of a clef/key/meter box of the same staff; n: another staff of the
                       system is nearer than the owning one.
S2 cross-staff         a: a head/rest (not a whole rest) with NO event of any other staff of its system within TOL sp in x;
                       b: >= HALF of the other staves have a clef/key/meter box within TOL sp in x while this is a head/rest.
"""
import pickle
import statistics
from collections import defaultdict

CONF = 0.50
VBAND = 2.0
TOL = 1.5
MIN_N = 12
HEADCAT = ("notehead",)


def parse(g):
    p = g.split("/")
    return tuple(int(x) for x in p[1:])      # page, system, staff, cell, idx


def head_family(cls):
    if cls.startswith("noteheadBlack"):
        return "head:black"
    if cls.startswith("noteheadHalf"):
        return "head:half"
    if cls.startswith("noteheadWhole"):
        return "head:whole"
    return cls


class Doc:
    def __init__(self, path):
        D = pickle.load(open(path, "rb"))
        self.D = D
        self.box, self.vrd, self.staff = D["box"], D["vrd"], D["staff"]
        self.glyph = {}          # subject -> dict
        self.by_sys = defaultdict(list)
        self.by_page_cls = defaultdict(list)
        self.by_bar = defaultdict(list)
        for g, (cls, cat, conf, bb) in self.box.items():
            p, s, st, cell, idx = parse(g)
            sk = "staff/%d/%d/%d" % (p, s, st)
            stf = self.staff.get(sk)
            if not stf:
                continue
            sp = stf["staff_spacing"]
            kept = None
            if cat == "notehead":
                v = self.vrd.get((g, "notehead_is_not_a_notehead"))
                kept = (v is not None and v[1] is False)
                if v is None:
                    kept = "nogate"          # a record that predates the gate (p0-p3 ink, 2026-09-22): see below
            elif cat == "rest":
                v = self.vrd.get((g, "rest_is_not_a_rest"))
                kept = (v is not None and v[1] is False)
                if v is None:
                    kept = "nogate"
            dur = self.vrd.get((g, "duration"))
            if kept == "nogate":
                kept = dur is not None       # such a head was written as a note iff it carries a duration verdict
            x0, y0, x1, y1 = bb
            lines = stf["staff_lines"]
            cy = (y0 + y1) / 2
            if cy < lines[0]:
                vd = (lines[0] - cy) / sp
            elif cy > lines[-1]:
                vd = (cy - lines[-1]) / sp
            else:
                vd = 0.0
            self.glyph[g] = dict(g=g, cls=cls, cat=cat, conf=conf, bb=bb, p=p, s=s, st=st, cell=cell, sp=sp,
                                 w=(x1 - x0) / sp, h=(y1 - y0) / sp, cx=(x0 + x1) / 2, cy=cy, vd=vd, kept=kept,
                                 dur=dur, fam=head_family(cls) if cat == "notehead" else cls)
            self.by_sys[(p, s)].append(g)
            self.by_bar[(p, s, st, cell)].append(g)
        # P1 census: confident instances per (page, family), and per document
        self.census = defaultdict(list)
        self.census_doc = defaultdict(list)
        for g, r in self.glyph.items():
            if self.confident(r):
                self.census[(r["p"], r["fam"])].append((g, r["w"], r["h"]))
                self.census_doc[r["fam"]].append((g, r["w"], r["h"]))
        # S1 header marks per staff; S2 columns per system
        self.hdr = defaultdict(list)       # (p,s,st) -> x1 of clef/key/meter boxes in cell 0
        self.hdr_x = defaultdict(list)     # (p,s) -> (staff, cx) for clef/key/meter boxes anywhere in cell 0
        self.events = defaultdict(list)    # (p,s) -> (staff, cx) of kept heads/rests (not whole rests)
        for g, r in self.glyph.items():
            c = r["cls"]
            if r["cat"] in ("clef", "time_sig_digit") or (r["cat"] == "accidental" and c.startswith("key")):
                if r["cell"] == 0:
                    self.hdr[(r["p"], r["s"], r["st"])].append(r["bb"][2])
                    self.hdr_x[(r["p"], r["s"])].append((r["st"], r["cx"]))
            if r["kept"] and c != "restWhole":
                self.events[(r["p"], r["s"])].append((r["st"], r["cx"]))
        self.nstaves = {}
        for (p, s), gl in self.by_sys.items():
            self.nstaves[(p, s)] = len({self.glyph[g]["st"] for g in gl})

    def confident(self, r):
        if not r["kept"] or r["conf"] is None or r["conf"] < CONF:
            return False
        if r["cat"] == "notehead":
            return bool(r["dur"]) and r["dur"][0] == "decided"
        return True

    # ---- P1
    def _stats(self, key, pool, i):
        c = self._sc.setdefault((key, i), None)
        if c is None:
            xs = [t[i] for t in pool]
            med = statistics.median(xs)
            c = (med, statistics.median([abs(x - med) for x in xs]) * 1.4826)
            self._sc[(key, i)] = c
        return c

    def p1z(self, g, scope="page"):
        """(z_w, z_h, n) of the box against its class's confident instances on this page (or document), or None if the
        census is thinner than MIN_N. Medians/MAD are over the whole pool (the subject itself is 1 of >= 12; the effect of
        leaving it out is below 0.01 sp at the sizes met here, checked on the Sean tiles in FINDINGS)."""
        r = self.glyph[g]
        key = (r["p"], r["fam"]) if scope == "page" else r["fam"]
        pool = self.census[key] if scope == "page" else self.census_doc[key]
        if not hasattr(self, "_sc"):
            self._sc = {}
        if len(pool) - (1 if self.confident(r) else 0) < MIN_N:
            return None
        out = []
        for i, nm in ((1, "w"), (2, "h")):
            med, mad = self._stats((scope,) + (key if isinstance(key, tuple) else (key,)), pool, i)
            out.append(abs(r[nm] - med) / max(mad, 0.05))
        return out[0], out[1], len(pool), r["w"], r["h"]

    def p1(self, g, k=4.0, scope="page"):
        z = self.p1z(g, scope)
        if z is None:
            return None
        return dict(flag=(z[0] > k or z[1] > k), n=z[2], w=(z[3], z[0]), h=(z[4], z[1]))

    # ---- S1
    def s1(self, g):
        r = self.glyph[g]
        res = {}
        res["v"] = r["vd"] > VBAND
        hx = self.hdr.get((r["p"], r["s"], r["st"]))
        res["h"] = bool(r["cell"] == 0 and r["cat"] in ("notehead", "rest") and hx and r["cx"] <= max(hx))
        # nearer staff
        own = self.staff["staff/%d/%d/%d" % (r["p"], r["s"], r["st"])]["staff_lines"]
        near = False
        for st in range(0, 64):
            sk = "staff/%d/%d/%d" % (r["p"], r["s"], st)
            if st == r["st"] or sk not in self.staff:
                continue
            ln = self.staff[sk]["staff_lines"]
            d = 0.0 if ln[0] <= r["cy"] <= ln[-1] else min(abs(r["cy"] - ln[0]), abs(r["cy"] - ln[-1]))
            if d / r["sp"] < r["vd"] and r["vd"] > 0.5:
                near = True
        res["n"] = near
        return res

    # ---- S2
    def s2(self, g, tol=TOL):
        r = self.glyph[g]
        if r["cat"] not in ("notehead", "rest"):
            return None
        n = self.nstaves.get((r["p"], r["s"]), 1)
        if n < 3:
            return None
        t = tol * r["sp"]
        others = {st for st, cx in self.events[(r["p"], r["s"])] if st != r["st"] and abs(cx - r["cx"]) <= t}
        hdr = {st for st, cx in self.hdr_x[(r["p"], r["s"])] if st != r["st"] and abs(cx - r["cx"]) <= t}
        return dict(a=(len(others) == 0) and r["cls"] != "restWhole", b=len(hdr) >= max(2, 0.5 * (n - 1)),
                    n_events=len(others), n_hdr=len(hdr))
