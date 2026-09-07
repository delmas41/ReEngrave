"""Export-only A/B for `OMR_KEYSIG_CORROBORATION`, over the stored transcriptions.

No detector, no weights, no scan_eval. Every arm loads the SAME stored
transcription JSON fresh (the exporter mutates the page dict — it pairs slurs
and wedges in place — so a shared dict would leak between arms) and writes
MusicXML.

Four arms, and the first two are the point:

    before   control
    before2  THE SAME CONTROL AGAIN — run first, so that a difference found
             later is attributable to the change rather than to the harness.
             A cached or nondeterministic harness reports a clean identical
             A/B, which is exactly the shape a flag-guarded change hopes for.
    flagoff  the wiring as `transcribe` has it, with the env var unset
    flagon   the same wiring with OMR_KEYSIG_CORROBORATION=1

⚠️ Fails loudly (exit 2) on an empty fixture set — see `_fixtures`.
"""
import hashlib
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", "..", "omr-pipeline-audit-2026-09", "probe"))
from _fixtures import fixtures, SCAN, ENGRAVED  # noqa: E402  fail-loud

# ⚠️ `chdir_root()` is DELIBERATELY not called. It cds to the MAIN checkout,
# whose `tools/omr` does not contain the module under test — the arms would
# then all import the same unchanged code and the A/B would report a clean
# identical result for the reason the harness exists to rule out. Fixtures come
# back from `fixtures()` as absolute paths, so nothing here needs the cwd; the
# CODE must come from THIS worktree and the FIXTURES from wherever they live.
_WORKTREE = os.path.dirname(os.path.dirname(os.path.dirname(_HERE)))
sys.path.insert(0, _WORKTREE)

from tools.omr.export import to_musicxml  # noqa: E402
from tools.omr.key_signature_corroboration import (  # noqa: E402
    drop_uncorroborated_key_changes,
    enabled,
)


def arm(path: str, *, gated: bool) -> tuple[str, dict]:
    """One arm's MusicXML for one fixture, plus what the guard did.

    `gated` reproduces `transcribe`'s wiring literally: the pass runs only if
    `enabled()` says so, which is what reads the env var.
    """
    result = json.load(open(path))
    totals = {"reverted": 0, "respelled": 0, "kept": 0, "changes": []}
    if gated and enabled():
        for page in result.get("pages", []):
            got = drop_uncorroborated_key_changes(page)
            totals["reverted"] += got["reverted"]
            totals["respelled"] += got["respelled"]
            totals["kept"] += got["kept"]
            totals["changes"] += got["changes"]
    return to_musicxml(result), totals


def digest(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


#: The committed artefact — the four arms' digests per fixture, so the
#: byte-identity claim is a file a reviewer can read rather than a console
#: line they have to trust. `before == before2` is in here too: a control that
#: agreed with itself is what makes the flag-off column mean anything.
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "out",
                   "ab-arm-digests.json")


def main() -> int:
    artefact: dict = {
        "what": "OMR_KEYSIG_CORROBORATION: sha256 of the exported MusicXML "
                "for four arms per stored transcription.",
        "arms": {
            "before": "control",
            "before2": "the same control AGAIN, run first, so a later "
                       "difference is attributable rather than assumed",
            "flagoff": "transcribe's wiring reproduced literally, env unset",
            "flagon": "the same wiring with OMR_KEYSIG_CORROBORATION=1",
        },
        "files": [],
    }
    families = [("scan", fixtures(SCAN, expect_at_least=11)),
                ("engraved", fixtures(ENGRAVED, expect_at_least=11))]
    rc = 0
    for fam, files in families:
        print(f"\n=== {fam}: {len(files)} stored transcriptions")
        n_ident_control = n_ident_off = n_diff_on = 0
        all_changes = []
        for path in files:
            name = os.path.basename(path).split(".")[0]

            os.environ.pop("OMR_KEYSIG_CORROBORATION", None)
            before, _ = arm(path, gated=False)
            before2, _ = arm(path, gated=False)          # control, run FIRST
            flagoff, off_totals = arm(path, gated=True)  # env var unset
            os.environ["OMR_KEYSIG_CORROBORATION"] = "1"
            flagon, on_totals = arm(path, gated=True)
            os.environ.pop("OMR_KEYSIG_CORROBORATION", None)

            ctl_ok = before == before2
            off_ok = before == flagoff
            n_ident_control += ctl_ok
            n_ident_off += off_ok
            changed = before != flagon
            n_diff_on += changed
            all_changes += on_totals["changes"]

            artefact["files"].append({
                "fixture": name, "family": fam,
                "before": digest(before), "before2": digest(before2),
                "flagoff": digest(flagoff), "flagon": digest(flagon),
                "control_identical": ctl_ok,
                "flagoff_identical_to_control": off_ok,
                "flagon_differs": changed,
                "reverted_flagon": on_totals["reverted"],
                "respelled_flagon": on_totals["respelled"],
                "kept_flagon": on_totals["kept"],
                "changes": on_totals["changes"],
            })
            if not ctl_ok:
                print(f"  !! CONTROL DIFFERS on {name} — harness is not "
                      f"deterministic; nothing below is attributable")
                rc = 1
            if not off_ok:
                print(f"  !! FLAG-OFF DIFFERS on {name} "
                      f"({digest(before)} vs {digest(flagoff)})")
                rc = 1
            if off_totals["reverted"]:
                print(f"  !! FLAG-OFF REVERTED {off_totals['reverted']} on {name}")
                rc = 1
            if changed:
                print(f"  flag-ON changes {name}: "
                      f"reverted={on_totals['reverted']} "
                      f"respelled={on_totals['respelled']} "
                      f"kept={on_totals['kept']}")
                for c in on_totals["changes"]:
                    print(f"      staff {c['staff_index']:>3} m{c['measure_index']} "
                          f"{c['from']}->{c['to']} over {c['measures_reverted']} "
                          f"measures | witnesses {c['witnesses']}/"
                          f"{c['staves_in_system']} | vote contradicted="
                          f"{c['contradicted_vote']}"
                          + (f" ({c['vote_reason']!r})" if c["vote_reason"] else ""))
            elif on_totals["reverted"]:
                print(f"  flag-ON reverted {on_totals['reverted']} on {name} "
                      f"but the EXPORT is byte-identical")
        print(f"  control identical: {n_ident_control}/{len(files)}")
        print(f"  FLAG-OFF byte-identical to control: {n_ident_off}/{len(files)}")
        print(f"  flag-ON export differs: {n_diff_on}/{len(files)}, "
              f"{len(all_changes)} changes reverted")
    artefact["pooled"] = {
        "fixtures": len(artefact["files"]),
        "control_identical": sum(f["control_identical"] for f in artefact["files"]),
        "flagoff_identical_to_control": sum(
            f["flagoff_identical_to_control"] for f in artefact["files"]),
        "flagon_differs": sum(f["flagon_differs"] for f in artefact["files"]),
        "changes_reverted": sum(f["reverted_flagon"] for f in artefact["files"]),
        "corroborated_changes_kept": sum(
            f["kept_flagon"] for f in artefact["files"]),
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as fh:
        json.dump(artefact, fh, indent=2, sort_keys=True)
        fh.write("\n")
    print(f"\nartefact -> {os.path.normpath(OUT)}")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
