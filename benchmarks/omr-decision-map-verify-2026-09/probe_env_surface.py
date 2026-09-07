"""Wider OMR_* env surface than verify.py's V4 sees.

V4 requires the literal `os.environ.get("OMR_...")` in tools/omr/*.py (not
rglob) plus any "OMR_..." string in backend/modules/*.py. This scan takes any
OMR_ string literal anywhere under tools/ and backend/, excluding tests.
"""
import pathlib
import re

ROOT = pathlib.Path(".")

v4 = set()
for py in sorted((ROOT / "tools" / "omr").glob("*.py")):
    for m in re.finditer(r'os\.environ\.get\(\s*"(OMR_[A-Z0-9_]+)"', py.read_text()):
        v4.add(m.group(1))
for py in sorted((ROOT / "backend" / "modules").glob("*.py")):
    for m in re.finditer(r'"(OMR_[A-Z0-9_]+)"', py.read_text()):
        v4.add(m.group(1))

wide = set()
srcs = [p for p in (ROOT / "tools").rglob("*.py") if "tests" not in p.parts]
srcs += [p for p in (ROOT / "backend").rglob("*.py") if "tests" not in p.parts]
for py in srcs:
    for m in re.finditer(r'["\'](OMR_[A-Z0-9_]+)["\']', py.read_text(errors="ignore")):
        wide.add(m.group(1))

doc = set(re.findall(r"OMR_[A-Z0-9_]+", (ROOT / "CLAUDE.md").read_text()))

print("V4 sees            :", len(v4))
print("wider scan sees    :", len(wide))
print("missed by V4       :", sorted(wide - v4))
print()
print("undocumented (wide):", len(wide - doc))
for n in sorted(wide - doc):
    print("   -", n)
