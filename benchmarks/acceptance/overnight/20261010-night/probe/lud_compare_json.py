#!/usr/bin/env python3
"""lud_compare_json: are two lud_extract outputs identical (ignoring prov.reader)?

The control between the load_record reader and the ijson reader. A control
must be able to fail: `--perturb` flips one value in a copy of the first file
and requires the comparison to report a difference.
"""
import json
import sys


def strip(o):
    o = dict(o)
    p = dict(o["prov"])
    p.pop("reader", None)
    o["prov"] = p
    return o


def diff(a, b, path="", out=None, limit=10):
    out = [] if out is None else out
    if len(out) >= limit:
        return out
    if type(a) != type(b):
        out.append(f"{path}: type {type(a).__name__} vs {type(b).__name__}")
    elif isinstance(a, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a:
                out.append(f"{path}/{k}: only in B")
            elif k not in b:
                out.append(f"{path}/{k}: only in A")
            else:
                diff(a[k], b[k], f"{path}/{k}", out, limit)
    elif isinstance(a, list):
        if len(a) != len(b):
            out.append(f"{path}: len {len(a)} vs {len(b)}")
        else:
            for i, (x, y) in enumerate(zip(a, b)):
                diff(x, y, f"{path}[{i}]", out, limit)
    elif a != b:
        out.append(f"{path}: {a!r} vs {b!r}")
    return out


def main():
    a = strip(json.load(open(sys.argv[1])))
    b = strip(json.load(open(sys.argv[2])))
    d = diff(a, b)
    sizes = {k: len(v) if hasattr(v, "__len__") else v for k, v in a.items() if k != "prov"}
    print("sections:", sizes)
    if d:
        print("DIFFERENT:")
        for x in d:
            print("  ", x)
        sys.exit(1)
    print("IDENTICAL")
    # the control can fail: perturb one value and require a difference
    first = next(iter(a["bar_totals"]))
    a["bar_totals"][first]["kept"] = a["bar_totals"][first].get("kept", 0) + 1
    if not diff(a, b):
        print("CONTROL BROKEN: a perturbed copy compared equal")
        sys.exit(2)
    print("control: a perturbed copy is reported different (comparison can fail)")


if __name__ == "__main__":
    main()
