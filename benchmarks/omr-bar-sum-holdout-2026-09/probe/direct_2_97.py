"""Call reconcile_duration directly on cells of a pickled Log.
   python3 direct_2_97.py LOG.pickle p/s/st/c [...]"""
import pickle
import sys

sys.path.insert(0, ".")
from tools.omr.staged import consequences as C  # noqa: E402
from tools.omr.staged import record as R  # noqa: E402
from tools.omr.staged.record import Kind, Q  # noqa: E402

log = pickle.load(open(sys.argv[1], "rb"))
for k in sys.argv[2:]:
    cell = R.cell(*[int(x) for x in k.split("/")])
    meter = log.verdict(Q.METER, cell.at(Kind.SYSTEM))
    n0 = len(log._vrd)
    out = C.reconcile_duration(log, cell, meter)
    print(k, "returned", [(v.subject.to_key(), v.value) for v in out])
    for v in C._standing(log, cell, Q.DURATION):
        print("   ", v.subject.to_key(), v.outcome.value, v.reason, v.decider,
              (v.value or {}).get("beats"),
              [(c.value.get("beats"), c.value.get("written"), c.value.get("dots"),
                c.value.get("beam_levels")) for c in v.candidates
               if isinstance(c.value, dict)])
