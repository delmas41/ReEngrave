"""Every function (ADJUDICATE / EVALUATE / INFER / EXPORT) that reads Q.STEM_DIRECTION or Q.HEAD_STEM, and whether its body mentions an owner test
(GLYPH_OWNER / is_relocated_copy / owned_by_another_staff / owned_by_another_staff()). Static grep, one line each."""
import ast, glob, os, sys
root = sys.argv[1]
files = sorted(glob.glob(os.path.join(root, "tools/omr/staged/adjudicators/*.py"))) + [os.path.join(root, "tools/omr/staged", f) for f in
                                                                                     ("consequences.py", "evaluate.py", "infer.py", "inferences.py", "export.py", "groups.py", "export_unison.py")]
for f in files:
    if not os.path.exists(f):
        continue
    src = open(f).read()
    tree = ast.parse(src)
    lines = src.split("\n")
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        body = "\n".join(lines[node.lineno - 1:node.end_lineno])
        reads = [q for q in ("Q.STEM_DIRECTION", "Q.HEAD_STEM)", "Q.HEAD_STEM,", "Q.HEAD_STEM ") if q in body]
        if not reads:
            continue
        # only the innermost: skip a function that merely contains another that reads
        inner = [n for n in ast.walk(node) if isinstance(n, ast.FunctionDef) and n is not node]
        own = body
        for n in inner:
            own = own.replace("\n".join(lines[n.lineno - 1:n.end_lineno]), "")
        if not any(q in own for q in ("Q.STEM_DIRECTION", "Q.HEAD_STEM")):
            continue
        heads = "NOTEHEAD_CLASS" in own or "head_ids" in own or "glyphs" in own or "members" in own
        skip = any(k in own for k in ("GLYPH_OWNER", "is_relocated_copy", "owned_by_another_staff"))
        print("%-38s %-34s iterates heads: %-3s  skips other-staff heads: %s" % (os.path.relpath(f, root).replace("tools/omr/staged/", ""), node.name,
                                                                                  "yes" if heads else "no", "YES" if skip else "no"))
