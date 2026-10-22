"""A meter this module's own predicate calls garbage must not be KEPT.

⚠️ `_is_propagatable_meter` names `1/4` in its docstring as exactly the kind of
thing that survives upstream filtering, and it was consulted only to decide who
may VOTE — never to decide whether a staff may keep a reading. Measured over 21
stored scan transcriptions: 4 of 227 staves and 45 of 2,538 measures carried
one, all `1/4`, across three works and three publishers.
`benchmarks/omr-rests-2026-09/FINDINGS.md` §14.
"""

from __future__ import annotations

from tools.omr.rhythm import backfill_page_time_signatures


def _page(staff_meters):
    """One system, one measure per staff, each staff opening in a given meter."""
    return {"systems": [{"system_index": 0, "staves": [
        {"staff_index": i,
         "time_signature": dict(ts) if ts else None,
         "measures": [{"measure_index": 0,
                       "time_signature": dict(ts) if ts else None,
                       "detections": []}]}
        for i, ts in enumerate(staff_meters)]}]}


def _ts(num, den):
    return {"numerator": num, "denominator": den, "raw": f"{num}/{den}"}


def test_a_one_four_staff_takes_the_pages_decided_meter_instead():
    # nine staves read 2/4, one reads the garbage 1/4
    page = _page([_ts(2, 4)] * 9 + [_ts(1, 4)])
    backfill_page_time_signatures(page)
    staves = page["systems"][0]["staves"]
    assert page["implausible_meters_dropped"] == 2, "the staff AND its measure"
    assert staves[-1]["time_signature"]["raw"] == "2/4", (
        "a meter the predicate rejects must not survive a page that decided 2/4")
    assert staves[-1]["measures"][0]["time_signature"]["raw"] == "2/4"


def test_a_plausible_minority_meter_is_NOT_touched():
    """⚠️ The guard removes GARBAGE, not dissent. A staff reading a plausible
    meter the page vote disagrees with is a separate, unshipped question — see
    FINDINGS §14; three Beethoven staves read 4/4 on a 2/4 page and CORROBORATE
    EACH OTHER, so no weak guard reaches them."""
    page = _page([_ts(2, 4)] * 9 + [_ts(4, 4)])
    backfill_page_time_signatures(page)
    staves = page["systems"][0]["staves"]
    assert not page.get("implausible_meters_dropped")
    assert staves[-1]["time_signature"]["raw"] == "4/4"


def test_clearing_beats_keeping_even_when_the_page_decides_nothing():
    """`None` means "unknown" and the exporter omits `<time>`; a kept `1/4`
    writes `<time>1/4</time>` and sizes that part's measure rests at one
    quarter — a confident wrong answer."""
    page = _page([_ts(1, 4)])
    backfill_page_time_signatures(page)
    staff = page["systems"][0]["staves"][0]
    assert staff["time_signature"] is None
    assert staff["measures"][0]["time_signature"] is None


def test_a_propagated_meter_is_not_re_tested():
    """⚠️ Only READINGS are considered. Re-testing this module's own output
    would be circular."""
    ts = dict(_ts(1, 4), source="detected_propagated")
    page = _page([ts])
    backfill_page_time_signatures(page)
    assert not page.get("implausible_meters_dropped")
