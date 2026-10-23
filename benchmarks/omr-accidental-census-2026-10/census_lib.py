"""2.197 shared helpers: a 'view' = the rows of one tree's run on some pages (replay.json from c1_replay/c1b_export, or a full record), the live
verdict per (subject, quantity), the MusicXML notes keyed by their glyph (traced export), and box geometry. Stdlib only."""
import json, collections, re
import xml.etree.ElementTree as ET

def iou(a, b):
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0])); iy = max(0, min(a[3], b[3]) - max(a[1], b[1])); i = ix * iy
    u = (a[2]-a[0])*(a[3]-a[1]) + (b[2]-b[0])*(b[3]-b[1]) - i
    return i / u if u > 0 else 0.0

def fam(cls):
    c = (cls or "").lower()
    if c.startswith("accidental"): return "accidental"
    if c.startswith("key") and not c.startswith("keyboard"): return "key"
    return None

def kind(cls):
    c = (cls or "").lower()
    for t, k in (("doubleflat", "dflat"), ("doublesharp", "dsharp"), ("flat", "flat"), ("natural", "natural"), ("sharp", "sharp")):
        if t in c: return k

ALT = {"b": "flat", "#": "sharp", "n": "natural", "natural": "natural", "##": "dsharp", "bb": "dflat"}

class View:
    def __init__(self, path, xml_path=None, tag=""):
        d = json.load(open(path))
        rec = d.get("record", d)
        self.tag = tag
        self.tree_sha = d.get("tree_sha")
        self.obs = rec["observations"]; self.verdicts = rec["verdicts"]
        self.boxes = collections.defaultdict(list)       # page -> glyph_box dicts
        self.by_key = {}
        self.accpos = {}                                # glyph key -> accidental_staff_position row
        self.markers = collections.defaultdict(list)    # staff key -> keysig_marker rows
        self.cellbox = {}
        self.space = {}                                 # (page,system,staff,cell) -> canonical staff space
        for o in self.obs:
            q = o["quantity"]
            if q == "glyph_box":
                b = (o.get("detail") or {}).get("bbox_page_px")
                if not b: continue
                s = o["subject"].split("/")
                g = dict(key=o["subject"], cls=o["value"][0], reader=o["reader"], conf=o.get("score"), box=b, page=int(s[1]), system=int(s[2]),
                         staff=int(s[3]), cell=int(s[4]), category=(o.get("detail") or {}).get("category"))
                self.boxes[g["page"]].append(g); self.by_key.setdefault(o["subject"], g)
            elif q == "accidental_staff_position":
                self.accpos[o["subject"]] = o
            elif q == "keysig_marker":
                self.markers[o["subject"]].append(o)
            elif q == "cell_box":
                s = o["subject"].split("/"); self.cellbox[tuple(int(x) for x in s[1:])] = o["value"]
            elif q == "cell_staff_space":
                s = o["subject"].split("/"); 
                try: self.space[tuple(int(x) for x in s[1:])] = float(o["value"])
                except Exception: pass
        chains = collections.defaultdict(list)
        for v in self.verdicts: chains[(v["subject"], v["quantity"])].append(v)
        self.live = {}
        for k, ch in chains.items():
            sup = {x.get("supersedes") for x in ch if x.get("supersedes")}
            self.live[k] = ([x for x in ch if x["id"] not in sup] or ch)[-1]
        self.xml_notes = {}
        self.xml_keys = []
        if xml_path:
            self._parse_xml(open(xml_path).read())

    def verdict(self, subject, q):
        return self.live.get((subject, q))

    def _parse_xml(self, xml):
        root = ET.fromstring(xml)
        for part in root.iter("part"):
            pid = part.get("id")
            for m in part.findall("measure"):
                for el in m.findall("attributes"):
                    for k in el.findall("key"):
                        self.xml_keys.append((pid, m.get("number"), int(k.findtext("fifths"))))
                for el in m.findall("note"):
                    rg = el.get("rg")
                    if not rg or el.find("rest") is not None: continue
                    p = el.find("pitch")
                    self.xml_notes[rg] = dict(part=pid, measure=m.get("number"), accidental=el.findtext("accidental"),
                                              step=p.findtext("step"), alter=p.findtext("alter") or "0", octave=p.findtext("octave"),
                                              blue=el.get("color") is not None, chord=el.find("chord") is not None)
