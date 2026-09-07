"""Which corroboration witness separates the 7 spurious mid-staff key flips.

Reads the stored transcriptions (no detector, no weights) and asks, of every
mid-staff key-signature CHANGE, three questions in turn:

  W1  does it contradict a cross-page vote that already spoke for this staff?
  W2  does another staff of the SAME SYSTEM change key at the same measure?
  W3  how strong is the reading that caused it?

⚠️ Fails loudly on an empty fixture set — see `_fixtures`.
"""
import json, os, sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "..", "omr-pipeline-audit-2026-09", "probe"))
from _fixtures import fixtures, chdir_root, SCAN, ENGRAVED  # noqa: E402  fail-loud
chdir_root()


def ks(k):
    if not k:
        return None
    assert "sharps" in k and "flats" in k, f"unexpected key summary: {k!r}"
    return (k["sharps"], k["flats"])


def changes_of_staff(st):
    """(measure_index, from, to, cell_ordinal) for every mid-staff change."""
    out, prev = [], None
    for i, m in enumerate(st.get("measures", [])):
        cur = ks(m.get("key_signature"))
        idx = m.get("measure_index")
        if idx is None:
            idx = i
        if cur is not None and prev is not None and cur != prev:
            out.append((idx, prev, cur, i))
        if cur is not None:
            prev = cur
    return out


total = 0
for fam, files in (("scan", fixtures(SCAN, expect_at_least=11)),
                   ("engraved", fixtures(ENGRAVED, expect_at_least=11))):
    rows = []
    w2_corroborated_pairs = 0
    for f in files:
        d = json.load(open(f))
        nm = os.path.basename(f).split(".")[0]
        for pi, pg in enumerate(d["pages"]):
            for si, sy in enumerate(pg["systems"]):
                staves = sy["staves"]
                # Every change position in this system, by measure index.
                positions = Counter()
                per_staff = {}
                for st in staves:
                    ch = changes_of_staff(st)
                    per_staff[st["staff_index"]] = ch
                    for idx, _a, _b, _i in ch:
                        positions[idx] += 1
                for st in staves:
                    for idx, a, b, cell_i in per_staff[st["staff_index"]]:
                        total += 1
                        voted = st.get("key_signature_source") == "header_vote"
                        w1 = voted and a == ks(st.get("key_signature"))
                        w2 = positions[idx] >= 2
                        if w2:
                            w2_corroborated_pairs += 1
                        kd = [x for x in st["measures"][cell_i].get("detections", [])
                              if (x.get("class") or "").lower().startswith("key")]
                        rows.append(dict(
                            file=nm, page=pi, system=si,
                            staff=st["staff_index"], instrument=st.get("instrument"),
                            measure_index=idx, cell=cell_i,
                            frm=a, to=b,
                            W1_contradicts_vote=w1,
                            W1_vote_reason=(st.get("key_signature_reason") or "")[:64],
                            W2_system_witnesses=positions[idx],
                            W3_conf=[round(x["confidence"], 2) for x in kd],
                            n_staves_in_system=len(staves),
                        ))
    print(f"=== {fam}: {len(rows)} mid-staff key changes")
    for r in rows:
        print(f"   {r['file']} p{r['page']}s{r['system']} staff{r['staff']:>3} "
              f"({r['instrument']}) m{r['measure_index']} cell{r['cell']} "
              f"{r['frm']}->{r['to']}  "
              f"W1={r['W1_contradicts_vote']} W2={r['W2_system_witnesses']}"
              f"/{r['n_staves_in_system']} W3={r['W3_conf']}")
        if r["W1_vote_reason"]:
            print(f"        vote said: {r['W1_vote_reason']!r}")
    print(f"   W1 covers {sum(r['W1_contradicts_vote'] for r in rows)}/{len(rows)}")
    print(f"   W2 (>=2 staves change at the same measure) would KEEP "
          f"{sum(r['W2_system_witnesses'] >= 2 for r in rows)}/{len(rows)}")
if total == 0:
    sys.stderr.write("FATAL: no mid-staff changes found at all -- probe is blind.\n")
    raise SystemExit(2)
