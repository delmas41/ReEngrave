"""Weight routing for the STAGED CLI (roadmap 3.2, first half).

The LEGACY path (`transcribe.py:_route_weights`) has routed by input domain
since 2026-09-03 -- a scanned PDF gets the hollow-graft checkpoint, a
digitally engraved one gets `ENGRAVED_WEIGHTS` -- and `docs/flags-2026-09.md`
already lists `OMR_WEIGHT_ROUTING` as a product flag "staged gets this at
roadmap 3.2". Nothing under `tools/omr/staged/` imported `input_domain` or
`_route_weights` before this module: the staged CLI took `--weights` as
typed, with no routing of any kind.

⚠️⚠️ **THIS DOES NOT MAKE `--weights` OMITTED MEAN "ROUTE", AND THAT IS A
DELIBERATE DEVIATION FROM HOW THE LEGACY CLI READS.** On `transcribe.py`,
omitting `--weights` always routes (there is no "no detector" mode). On the
staged CLI, omitting `--weights` has meant, since before this change and
independently of it, "run with NO detector at all -- every cell abstains
`READER_UNAVAILABLE` and the pipeline still completes" (`__main__.py`'s own
docstring; exercised by tests that want a cheap, weights-free run and by any
cloud session with no `omr-weights/`). Making omission silently trigger
routing would ask `_route_weights` to hand back a real file path even where
none exists on disk, which is not a graceful abstention -- `YoloDetector`
would fail to load it. So routing here is an EXPLICIT request
(`--weights auto` on the CLI): omitting `--weights` is UNCHANGED, an
explicit real path still pins exactly as before, and `--weights auto` is
the new third state. `--no-weight-routing` is the literal escape the prep
brief asked for, folded in as the deny-list-under-`--weights-auto` case
rather than as a second way to reach the unrouted default.

⚠️ THIS IS A GATHER-TIME DECISION, SO NO SHARED-RECORD ARM CAN PRICE IT.
Weight routing picks the detector BEFORE `gather()` runs; `readjudicate.py`
and `reexport_arm.py` rebuild ADJUDICATE/EXPORT over an already-gathered log
and are structurally blind to it, same as any other GATHER change. Its
first real measurement is whatever tonight's roadmap-1.1 whole-movement
gathers turn out to route to.
"""
from __future__ import annotations

from typing import Any, Optional, Sequence, Tuple


def resolve_staged_weights(
    pdf_path: Any,
    pages: Sequence[int],
    *,
    weights: Optional[str],
    route_weights: bool,
    no_weight_routing: bool = False,
    classify: Any = None,
) -> Tuple[Optional[str], Optional[dict], Any]:
    """Pick the weights file for a staged run, and the domain evidence if any
    was computed to do it.

    Returns `(weights_path, weight_routing_provenance, classification)`:

    - `weights` given (a real path, not the string `"auto"`) -> pins exactly
      as `--weights` always has: `(weights, None, None)`. No classification
      runs, matching the legacy rule that an explicit path "skips
      classification entirely".
    - `weights` is `None` and `route_weights` is False -> `(None, None,
      None)`, i.e. UNCHANGED: the caller's existing "no detector" behaviour.
    - `weights == "auto"` -> route. `no_weight_routing`, or
      `OMR_WEIGHT_ROUTING` in its off state (`_weight_routing_enabled`,
      imported rather than restated), short-circuits to the default weights
      with `mode: "disabled"` and never classifies. Otherwise the PDF is
      classified ONCE (`classify` is injectable for tests, matching
      `transcribe._route_weights`'s own seam) and `_route_weights` is asked
      to pick from that SAME classification -- never a second one -- via a
      classify function that ignores its arguments and returns what was
      already computed. The `DomainClassification` object is returned
      alongside the path so the caller can also hand it to `gather()`
      (`input_domain_classification=`), so the routed weights and the
      recorded `Q.INPUT_DOMAIN` row can never disagree about which
      classification produced them.
    """
    if weights and weights != "auto":
        return weights, None, None
    if weights is None and not route_weights:
        return None, None, None

    # Only "auto" or (route_weights and weights is None) reach here.
    from ..transcribe import (DEFAULT_WEIGHTS, _repo_root,
                              _weight_routing_enabled)

    if no_weight_routing or not _weight_routing_enabled():
        default = str(_repo_root() / DEFAULT_WEIGHTS)
        reason = ("--no-weight-routing -> default weights" if no_weight_routing
                  else "OMR_WEIGHT_ROUTING is off -> default weights")
        return default, {"mode": "disabled", "weights": default,
                         "reason": reason}, None

    from ..input_domain import DEFAULT_CLASSIFY_PAGES
    if classify is None:
        from ..input_domain import classify_pdf_domain as classify
    sample = list(pages)[:DEFAULT_CLASSIFY_PAGES]
    classification = classify(pdf_path, page_indices=sample)

    from ..transcribe import _route_weights
    weights_path, prov = _route_weights(
        pdf_path, pages, classify=lambda *_a, **_k: classification)
    return weights_path, prov, classification
