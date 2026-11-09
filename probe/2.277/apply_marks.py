"""one-off: set the copy rule's overlap cut (2.277). Edits claim_final.py, adjudicators/stroke_owner.py and the test file in place."""
import pathlib
R = pathlib.Path(__file__).resolve().parents[2] / "tools" / "omr"
p = R / "staged" / "claim_final.py"
s = p.read_text()
i = s.index("def marks(owned_by_head")
j = s.index("# ── what a decider is told")
new = '''#: two boxes are COPIES BY POSITION (one head's ink drawn twice) only where their boxes overlap at least this much (intersection over union). A MEASUREMENT on the
#: Litolff sample, looked at on crops both sides of the line (2.277 FINDINGS): under 0.5 the pairs are different heads (a second's two sides of a stem, a chord's
#: neighbours, a tall chord blob); 0.5-0.7 is ambiguous; 0.7 and over are single heads. It only NARROWS: it can never fuse two heads of a second or a unison
#: (page-facts: a second puts heads on both sides of the stem; a head with a stem each way is TWO notes, 2.175 -- and this module only COUNTS ink, it refuses nothing).
COPY_IOU_MIN = 0.7


def _iou(a: Sequence[float], b: Sequence[float]) -> float:
    ix = min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0])
    iy = min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1])
    if ix <= 0 or iy <= 0:
        return 0.0
    i = ix * iy
    return i / float(a[2] * a[3] + b[2] * b[3] - i)


def marks(owned_by_head: Iterable[Sequence[str]], boxes: Dict[str, Sequence[float]], min_iou: float = COPY_IOU_MIN) -> Dict[str, str]:
    """`{box key: mark id}` for every head box that is a copy by position of another. `owned_by_head`: for each stroke a HEAD owns, the claim keys that own it (a
    MERGED stroke lists several boxes); `boxes`: key -> (x, y, w, h) in one frame. Two boxes of one merged stroke are one mark only if their boxes overlap at least
    `min_iou`; union-find over those pairs; the mark id is the smallest key of the group (deterministic). A box alone on its ink is not listed: it is its own mark."""
    parent: Dict[str, str] = {}

    def find(a: str) -> str:
        while parent.setdefault(a, a) != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    for keys in owned_by_head:
        ks = [str(k) for k in keys if str(k) in boxes]
        for x in range(len(ks)):
            for y in range(x + 1, len(ks)):
                if _iou(boxes[ks[x]], boxes[ks[y]]) >= min_iou:
                    ra, rb = find(ks[x]), find(ks[y])
                    if ra != rb:
                        parent[max(ra, rb)] = min(ra, rb)
    groups = {}
    for k in list(parent):
        groups.setdefault(find(k), []).append(k)
    return {k: root for root, ks in groups.items() if len(ks) > 1 for k in ks}


'''
p.write_text(s[:i] + new + s[j:])

p = R / "staged" / "adjudicators" / "stroke_owner.py"
s = p.read_text()
old = '    mk = CF.marks([[k for k in w.owners if k in keys] for w in owned.values() if w.family == "head" and w.state in ("decided", "merged")])'
new = '''    frames: Dict[str, Any] = {}
    for b in ev.rows(Q.GLYPH_BOX, scope=Scope.SELF_AND_DESCENDANTS, subject=cell):
        v = b.value
        if isinstance(v, (list, tuple)) and len(v) == 5 and b.subject.to_key() in keys:
            frames[b.subject.to_key()] = tuple(float(t) for t in v[1:5])
    mk = CF.marks([[k for k in w.owners if k in keys] for w in owned.values() if w.family == "head" and w.state in ("decided", "merged")], frames)'''
assert old in s
p.write_text(s.replace(old, new))

p = R / "tests" / "test_claim_final_2_277.py"
s = p.read_text()
i = s.index("    def test_marks_are_one_head_by_ink")
j = s.index("    def test_refusal_kinds")
new = '''    BOXES = {"g/1": (0, 0, 10, 10), "g/2": (0.5, 0.5, 10, 10), "g/3": (1, 0, 10, 10), "g/9": (50, 0, 10, 10), "g/7": (10, 5, 10, 10)}

    def test_marks_are_one_head_by_ink(self):
        m = CF.marks([["g/2", "g/1"], ["g/1", "g/3"], ["g/9"]], self.BOXES)
        self.assertEqual(set(m), {"g/1", "g/2", "g/3"})
        self.assertEqual(len(set(m.values())), 1)
        self.assertEqual(CF.distinct_heads(["g/1", "g/2", "g/3", "g/9"], m), 2)

    def test_CONTROL_two_unrelated_heads_are_two_marks(self):
        self.assertEqual(CF.marks([["g/1"], ["g/2"]], self.BOXES), {})
        self.assertEqual(CF.distinct_heads(["g/1", "g/2"], {}), 2)

    def test_CONTROL_the_heads_of_a_second_on_a_merged_blob_are_never_one_mark(self):
        # two boxes that share a stroke but sit side by side (a second's two sides of the stem; IoU well under the cut) stay two marks
        self.assertEqual(CF.marks([["g/1", "g/7"]], self.BOXES), {})

    def test_double_marks_found(self):
        m = CF.marks([["g/1", "g/2"]], self.BOXES)
        self.assertEqual(len(CF.double_marks(m, ["g/1", "g/2"])), 1)
        self.assertEqual(CF.double_marks(m, ["g/1"]), [])

'''
p.write_text(s[:i] + new + s[j:])
print("ok")
