"""2.311 scratch: Sean's Brahms p0 cells by what was inspected, and the boxes inside fully swept ("all-ink") cells."""
import collections
from pathlib import Path

from tools.omr.hand_truth import store, score as S

page = store.load(Path("data/hand-truth/pages/imslp317803/0.json"))
print(collections.Counter((getattr(c, "kind", None), tuple(sorted(c.inspected))) for c in page.cells).most_common(12))
print("cell fields", [k for k in vars(page.cells[0])])
allink = [c for c in page.cells if "all-ink" in c.inspected]
print("all-ink cells", len(allink))
items = S.truth_items(page)
sc = S.Scope(allink)
inside = [it for it in items if sc.holds(it.rect)]
print("boxes in all-ink cells", len(inside))
print(collections.Counter(it.family for it in inside).most_common())
print(collections.Counter(it.cls for it in inside if it.family in ("notehead", "rest", "accidental", "flag", "beam", "clef", "key_accidental", "time_signature_digit", "augmentation_dot", "tremolo")).most_common())
b = page.boxes[0]
print("box fields", [k for k in vars(b)])
