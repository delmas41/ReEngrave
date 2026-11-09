"""one-off (2.277): make the stroke owner accept ANY claim layer's rows, whatever the unit; extend the derived check. Edits in place."""
import pathlib
R = pathlib.Path(__file__).resolve().parents[2] / "tools" / "omr" / "staged"

p = R / "adjudicators" / "stroke_owner.py"
s = p.read_text()
old = "def _arc_claims(ev: Evidence, cell) -> List[SO.Claim]:"
new = '''#: owners the stroke owner already reads by their own path (the register's tier-0 areas, the arcs' and hairpins' traced ink, the page heads and their ledgers)
_OWN_PATH_OWNERS = frozenset(SO.AREA_OWNERS) | {"arc", "hairpin", "head", "ledger"}


def _rects(r) -> List[Tuple[float, float, float, float]]:
    """The page-px rectangles a claim row names, WHATEVER its unit: its value when it is a rectangle (`area`), else `detail.area`, else `detail.stroke_boxes`."""
    d = r.detail or {}
    v = r.value
    if isinstance(v, (list, tuple)) and len(v) == 4 and all(isinstance(t, (int, float)) for t in v):
        return [tuple(float(t) for t in v)]
    if isinstance(d.get("area"), (list, tuple)) and len(d["area"]) == 4:
        return [tuple(float(t) for t in d["area"])]
    return [tuple(float(t) for t in b) for b in (d.get("stroke_boxes") or ()) if isinstance(b, (list, tuple)) and len(b) == 4]


def _layer_claims(ev: Evidence, cell, page: Dict[int, Tuple[float, ...]]) -> List[SO.Claim]:
    """ROADMAP 2.277 (flag `OMR_CLAIM_FINAL`): ANY claim layer's `Q.CLAIMED_AREA` rows -- whatever the owner and whatever the unit (`area`, `page_ink`, a
    layer a later lane files, e.g. 2.276's `tremolo`) -- own the strokes of THIS cell that lie wholly inside their rectangle (+1 px: a stem crossing a slash keeps its
    ink), at tier 0, exactly as a word's page-wide claim does. No hand list of owners: an owner this module has no path for is a layer by being in the register.
    Nothing here is filed with the flag OFF."""
    from .. import claim_final as CF
    out: List[SO.Claim] = []
    if not CF.enabled():
        return out
    for r in ev.rows(Q.CLAIMED_AREA, scope=Scope.SELF_AND_ANCESTORS, subject=cell):
        d = r.detail or {}
        owner = str(d.get("owner") or "")
        if not owner or owner in _OWN_PATH_OWNERS or d.get("standing", "READ") != "READ" or d.get("unit") == "ink":
            continue
        inside = set()
        for x0, y0, x1, y1 in _rects(r):
            inside |= {o for o, pb in page.items() if x0 - 1 <= pb[0] and pb[2] <= x1 + 1 and y0 - 1 <= pb[1] and pb[3] <= y1 + 1}
        if inside:
            out.append(SO.Claim(r.id, owner, owner, tuple(sorted(inside)), (), r.id, area=True))
    return out


def _arc_claims(ev: Evidence, cell) -> List[SO.Claim]:'''
assert old in s
s = s.replace(old, new, 1)
old = "    claims += _found_whole_rests(ev, cell, page, claims)\n"
new = "    layer_claims = _layer_claims(ev, cell, page)       # 2.277 (flag OMR_CLAIM_FINAL): any other claim layer, whatever its unit\n    claims += layer_claims\n    claims += _found_whole_rests(ev, cell, page, claims)\n"
assert old in s
s = s.replace(old, new, 1)
old = "    owned = SO.own_strokes(inks, claims, tiers=SO.TIERS,"
new = "    tiers = ((tuple(SO.TIERS[0]) + tuple(sorted({c.family for c in layer_claims})),) + tuple(SO.TIERS[1:])) if layer_claims else SO.TIERS\n    owned = SO.own_strokes(inks, claims, tiers=tiers,"
assert old in s
s = s.replace(old, new, 1)
p.write_text(s)

p = R / "claim_final.py"
s = p.read_text()
old = '''    out: List[Dict[str, str]] = []
    for fam in filed:'''
new = '''    out: List[Dict[str, str]] = []
    # a claim LAYER in `claim_order.LAYERS` (before the heads) whose rows no consumer reads: the stroke owner has no generic path and the family is neither a tier-0
    # owner nor a box family it already reads. (2.276's `tremolo` is such a layer on a tree without `_layer_claims`.)
    co = root / "claim_order.py"
    if co.exists():
        lay = re.search(r"LAYERS[^=]*=\\s*\\((.*?)\\n\\)\\n", co.read_text(), re.S)
        names = []
        for ln in (lay.group(1) if lay else "").split("\\n"):
            mm = re.match(r'\\s*\\("(\\w+)",\\s*\\(([^)]*)\\)', ln)
            if mm:
                if mm.group(1) == "head":
                    break
                names += [x.strip().strip("\\"'") for x in mm.group(2).split(",") if x.strip().strip("\\"'")]
        tiers_all = re.search(r"TIERS[^=]*=\\s*\\((.*?)\\n\\)\\n", so, re.S)
        read_by_owner = {x for x in re.findall(r'"(\\w+)"', re.sub(r"#[^\\n]*", "", tiers_all.group(1) if tiers_all else ""))}
        has_generic = "_layer_claims(" in (root / "adjudicators" / "stroke_owner.py").read_text()
        for fam in names:
            if fam not in read_by_owner and not has_generic:
                out.append({"claim": fam, "reader": "stroke_owner", "why": "a claim layer in claim_order.LAYERS whose rows no consumer reads"})
    for fam in filed:'''
assert old in s
s = s.replace(old, new, 1)
p.write_text(s)
print("ok")
