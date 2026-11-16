"""2.311 scratch: Sean's Brahms p0 boxes by family and class, and how many lie in cells inspected for noteheads."""
import collections
from pathlib import Path

from tools.omr.hand_truth import store, score as S

page = store.load(Path("data/hand-truth/pages/imslp317803/0.json"))
items = S.truth_items(page)
scope = S.Scope(S.cells_inspected_for(page, "notehead"))
print("cells", len(page.cells), "inspected for notehead", len(scope.cells))
c = collections.Counter((it.family, it.cls, it.origin, scope.holds(it.rect)) for it in items if it.family in ("notehead", "rest"))
for k, v in sorted(c.items()):
    print(k, v)
print(collections.Counter(it.family for it in items))
