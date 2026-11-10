import sys
sys.path.insert(0, ".")
from tools.omr.staged import stroke_owner as SO
from tools.omr.tests.test_claim_order_2_282 import _blob, _claims
own = SO.own_strokes([_blob()], _claims())
print(own[0])
