"""Throwaway: reader-name / detail-tag strings FILTERED on by consumers vs strings FILED by producers."""
import ast, collections, pathlib, sys, re
ROOT = pathlib.Path(sys.argv[1]) / "tools/omr/staged"
files = [p for p in sorted(ROOT.rglob("*.py")) if not p.name.startswith("test_")]
filed = collections.defaultdict(set)      # (key, value) -> sites
compared = collections.defaultdict(set)
KEYS = {"reader", "source", "identity", "owner", "unit", "kind", "basis", "via", "origin", "by", "tier", "filed_by", "method", "mode"}

def strs(n):
    if isinstance(n, ast.Constant) and isinstance(n.value, str):
        return [n.value]
    if isinstance(n, (ast.Tuple, ast.List, ast.Set)):
        return [e.value for e in n.elts if isinstance(e, ast.Constant) and isinstance(e.value, str)]
    return []

def keyname(n):
    # r.reader / d.get("source") / d["source"] / detail.get("identity")
    if isinstance(n, ast.Attribute) and n.attr in KEYS:
        return n.attr
    if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "get" and n.args and isinstance(n.args[0], ast.Constant) and n.args[0].value in KEYS:
        return n.args[0].value
    if isinstance(n, ast.Subscript):
        s = n.slice
        if isinstance(s, ast.Constant) and s.value in KEYS:
            return s.value
    if isinstance(n, ast.BoolOp):
        for v in n.values:
            k = keyname(v)
            if k:
                return k
    return None

for p in files:
    rel = str(p.relative_to(ROOT))
    tree = ast.parse(p.read_text())
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
        if isinstance(node, ast.keyword) and node.arg in KEYS:
            for s in strs(node.value):
                filed[(node.arg, s)].add(f"{rel}:{encl(node)}")
        if isinstance(node, ast.Dict):
            for k, v in zip(node.keys, node.values):
                if isinstance(k, ast.Constant) and k.value in KEYS:
                    for s in strs(v):
                        filed[(k.value, s)].add(f"{rel}:{encl(node)}")
        if isinstance(node, ast.Compare):
            sides = [node.left] + list(node.comparators)
            ks = [keyname(s) for s in sides]
            k = next((x for x in ks if x), None)
            if k:
                for s in sides:
                    for v in strs(s):
                        compared[(k, v)].add(f"{rel}:{encl(node)}")
            # startswith
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "startswith":
            k = keyname(node.func.value)
            if k:
                for a in node.args:
                    for v in strs(a):
                        compared[(k, v + "*")].add(f"{rel}:{encl(node)}")

# all string constants anywhere (to see if a compared value is ever written anywhere at all)
allstr = collections.defaultdict(set)
for p in files:
    rel = str(p.relative_to(ROOT))
    for node in ast.walk(ast.parse(p.read_text())):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and len(node.value) < 60:
            allstr[node.value].add(rel)

print("== compared values never FILED under the same key (candidate STARVED filters):")
for (k, v), sites in sorted(compared.items()):
    if v.endswith("*"):
        pre = v[:-1]
        if any(kk == k and vv.startswith(pre) for (kk, vv) in filed):
            continue
    elif (k, v) in filed:
        continue
    files_with = sorted(allstr.get(v.rstrip("*"), ()))
    print(f"  {k}={v!r:40} compared at {sorted(sites)[:4]}  | literal appears in {files_with[:6]}")
