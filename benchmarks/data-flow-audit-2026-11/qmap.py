"""Throwaway: per quantity, producer and consumer SITES (file:function) over all of tools/omr/staged (non-test)."""
import ast, collections, json, pathlib, sys
ROOT = pathlib.Path(sys.argv[1]) / "tools/omr/staged"
sys.path.insert(0, sys.argv[1])
from tools.omr.staged.record import Q
from tools.omr.staged import reach
by_attr = {k: v for k, v in vars(Q).items() if isinstance(v, str) and not k.startswith("_")}
vals = set(by_attr.values())
read_at, write_at = reach._accessors()

def qname(n):
    if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) and n.value.id == "Q" and n.attr in by_attr:
        return by_attr[n.attr]
    if isinstance(n, ast.Constant) and n.value in vals:
        return n.value
    return None

prod = collections.defaultdict(set); cons = collections.defaultdict(set); other = collections.defaultdict(set)
defined = {}  # funcname -> files
refs = collections.Counter()
files = [p for p in sorted(ROOT.rglob("*.py")) if not p.name.startswith("test_")]
for p in files:
    rel = str(p.relative_to(ROOT))
    tree = ast.parse(p.read_text())
    # parent map for enclosing function
    parents = {}
    for node in ast.walk(tree):
        for c in ast.iter_child_nodes(node):
            parents[c] = node
    def encl(n):
        while n in parents:
            n = parents[n]
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                return n.name
        return "<module>"
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            defined.setdefault(node.name, set()).add(rel)
        if isinstance(node, ast.Name):
            refs[node.id] += 1
        if isinstance(node, ast.Attribute):
            refs[node.attr] += 1
    handled = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            a = node.func.attr
            tbl = write_at if a in write_at else read_at if a in read_at else None
            if tbl is None:
                continue
            idx = tbl[a]
            arg = node.args[idx] if len(node.args) > idx else next((k.value for k in node.keywords if k.arg == "quantity"), None)
            if arg is None:
                continue
            qs = []
            if isinstance(arg, (ast.Tuple, ast.List, ast.Set)):
                qs = [qname(e) for e in arg.elts]
            else:
                qs = [qname(arg)]
            for q in qs:
                if q is None:
                    continue
                site = f"{rel}:{encl(node)}"
                (prod if a == "observe" else cons if a != "abstain" else prod)[q].add(site)
            for sub in ast.walk(arg):
                handled.add(id(sub))
    for node in ast.walk(tree):
        if id(node) in handled:
            continue
        q = qname(node) if isinstance(node, ast.Attribute) else None
        if q:
            other[q].add(f"{rel}:{encl(node)}")

# verdict producers
from tools.omr.staged import adjudicate, evaluate, infer
import importlib
for m in ("adjudicators", "consequences", "inferences"):
    importlib.import_module("tools.omr.staged." + m)
for q, spec in adjudicate.REGISTRY.items():
    prod[q].add(f"VERDICT:{getattr(spec, 'fn', spec).__name__ if hasattr(getattr(spec,'fn',spec),'__name__') else q}")
    for w in spec.wants:
        cons[w].add(f"WANTS:{q}")
for r in evaluate.RULES:
    prod[r.effect].add(f"EVALUATE:{getattr(r,'name',r)}")
    cons[r.cause].add(f"EVALUATE:{getattr(r,'name',r)}")
out = {}
for q in sorted(vals):
    out[q] = {"prod": sorted(prod[q]), "cons": sorted(cons[q]), "other": sorted(other[q])}
json.dump({"q": out, "refs": refs, "defined": {k: sorted(v) for k, v in defined.items()}}, open(sys.argv[2], "w"), indent=1)
real_cons = lambda q: [c for c in out[q]["cons"] if not c.startswith("WANTS:")]
print("== consumer (real read call) but NO producer site:")
for q, d in out.items():
    if not d["prod"] and real_cons(q):
        print("  ", q, "| cons:", real_cons(q)[:6])
print("== declared in wants only, no producer, no real read:")
for q, d in out.items():
    if not d["prod"] and d["cons"] and not real_cons(q):
        print("  ", q, d["cons"][:4])
print("== producer but NO consumer (no read call, no wants; 'other' refs listed):")
for q, d in out.items():
    if d["prod"] and not d["cons"]:
        print("  ", q, "| prod:", d["prod"][:3], "| other:", d["other"][:4])
print("== no producer, no consumer at all:")
for q, d in out.items():
    if not d["prod"] and not d["cons"]:
        print("  ", q, "| other:", d["other"][:4])
