"""SPEC-021 Atlas uplink gates."""

from dslv_zpdi.layer3_telemetry.atlas_uplink import (
    CaptureGate,
    UplinkPolicy,
    may_uplink,
    qualifies_for_atlas,
)


def _alpha(**kwargs) -> CaptureGate:
    base = dict(
        tier="alpha",
        format="hdf5",
        gpsdo_disciplined=True,
        packet_state="PRIMARY_ACCEPTED",
        hmac_ok=True,
        gps_lock=True,
        pps_jitter_ns=1.8,
    )
    base.update(kwargs)
    return CaptureGate(**base)


def test_alpha_hdf5_gpsdo_qualifies():
    ok, reasons = qualifies_for_atlas(_alpha())
    assert ok is True
    assert reasons == []


def test_tier2_never_qualifies():
    ok, reasons = qualifies_for_atlas(_alpha(tier="tier2"))
    assert ok is False
    assert "Not Alpha / Tier-1" in reasons


def test_secondary_never_qualifies():
    ok, _ = qualifies_for_atlas(_alpha(packet_state="SECONDARY_QUARANTINED"))
    assert ok is False


def test_no_gpsdo_never_qualifies():
    ok, reasons = qualifies_for_atlas(_alpha(gpsdo_disciplined=False))
    assert ok is False
    assert "GPSDO not disciplining" in reasons


def test_pps_jitter_gate():
    ok, reasons = qualifies_for_atlas(_alpha(pps_jitter_ns=5001.0))
    assert ok is False
    assert any("PPS" in r for r in reasons)


def test_opt_in_default_off():
    ok, reasons = may_uplink(True, UplinkPolicy())
    assert ok is False
    assert "Operator opt-in is OFF" in reasons


def test_metered_blocks_even_when_opted_in():
    ok, reasons = may_uplink(
        True, UplinkPolicy(opt_in=True, node_idle=True, metered=True)
    )
    assert ok is False
    assert "Link is metered" in reasons


def test_busy_node_blocks():
    ok, reasons = may_uplink(
        True, UplinkPolicy(opt_in=True, node_idle=False, metered=False)
    )
    assert ok is False
    assert "Node is busy" in reasons


def test_passive_window_allows_alpha():
    ok, reasons = may_uplink(
        True, UplinkPolicy(opt_in=True, node_idle=True, metered=False)
    )
    assert ok is True
    assert reasons == []
