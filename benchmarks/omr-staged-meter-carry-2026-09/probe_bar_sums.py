"""Do a page's own BAR SUMS name its meter, without reading the meter?

⚠️ THE QUESTION IS THE CARRY'S SECOND WITNESS. A carried meter must arrive as
a CANDIDATE and be confirmed or refuted by the bars it claims to govern, so
that a movement boundary needs no movement detector: the Andante's bars simply
contradict the previous movement's meter. This asks whether they can.

⚠️ READ THE FLAG-OFF EXPORT ONLY. With the carry on, `reconcile_duration`
rewrites durations FROM the meter, so bar sums there are downstream of exactly
what is being tested.

⚠️ THREE FILTERS, EACH FOR A MEASURED REASON, NOT FOR TIDINESS:
  * a `<chord/>` note does not advance time -- summing chord members
    separately is what once made these bars look "systematically doubled";
  * a LONE measure/whole rest is a CONVENTION GLYPH standing for the bar
    whatever the meter, so it carries no evidence about bar LENGTH. 83 of 94
    bars at 4.0 in one earlier count were exactly this;
  * an EMPTY bar is a pad, not a reading.
"""
import sys, xml.etree.ElementTree as ET
from collections import Counter


def bar_sums(path):
    root = ET.parse(path).getroot()
    sums, skipped = [], Counter()
    for part in root.iter("part"):
        div = 1
        for m in part.iter("measure"):
            attrs = m.find("attributes")
            if attrs is not None and attrs.find("divisions") is not None:
                div = int(attrs.find("divisions").text)
            notes = list(m.iter("note"))
            if not notes:
                skipped["empty_bar_padded"] += 1
                continue
            rests = [n for n in notes if n.find("rest") is not None]
            if len(notes) == 1 and rests:
                r = rests[0]
                ty = r.find("type")
                if r.find("rest").get("measure") == "yes" or (
                        ty is not None and ty.text == "whole"):
                    skipped["lone_measure_or_whole_rest"] += 1
                    continue
            total = 0.0
            for n in notes:
                if n.find("chord") is not None:      # does not advance time
                    continue
                d = n.find("duration")
                if d is None:
                    continue
                total += int(d.text) / float(div)
            if total > 0:
                sums.append(round(total, 4))
    return sums, skipped


def report(label, path, truth_ql, truth_name):
    sums, skipped = bar_sums(path)
    c = Counter(sums)
    n = len(sums)
    print(f"\n=== {label}  (prints {truth_name} = {truth_ql} quarter-lengths a bar) ===")
    print(f"    assessable bars: {n}   skipped: {dict(skipped)}")
    if not n:
        return
    print("    the ten commonest bar sums:")
    for val, k in c.most_common(10):
        bar = "#" * max(1, round(40 * k / c.most_common(1)[0][1]))
        flag = "  <== the printed meter" if abs(val - truth_ql) < 1e-6 else ""
        print(f"      {val:6.3f} x{k:4d}  {bar}{flag}")
    hit = sum(k for v, k in c.items() if abs(v - truth_ql) < 1e-6)
    print(f"    bars landing EXACTLY on the printed meter: {hit}/{n} = {hit/n:.3f}")
    print(f"    modal bar sum: {c.most_common(1)[0][0]}")
    return c


if __name__ == "__main__":
    p1, p17 = sys.argv[1], sys.argv[2]
    a = report("page 1  — movement 1, meter IS read (control)", p1, 2.0, "2/4")
    b = report("page 17 — movement 2 Andante, meter reads NOTHING", p17, 1.5, "3/8")
    print("\n=== the discriminating question ===")
    for name, c in (("page 1", a), ("page 17", b)):
        if not c:
            continue
        n = sum(c.values())
        two = sum(k for v, k in c.items() if abs(v - 2.0) < 1e-6)
        three = sum(k for v, k in c.items() if abs(v - 1.5) < 1e-6)
        print(f"    {name:8s}  bars==2.0 (2/4): {two:4d} ({two/n:.3f})   "
              f"bars==1.5 (3/8): {three:4d} ({three/n:.3f})")
