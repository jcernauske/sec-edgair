"""Tests for the human approval gate behavior."""

from src.base.entity_resolution.staging import apply_gate


def _make_high_confidence_proposals():
    return [
        {"mapping_id": "ER-001", "confidence": 1.0, "status": "pending"},
        {"mapping_id": "ER-002", "confidence": 0.9, "status": "pending"},
    ]


def _make_mixed_confidence_proposals():
    return [
        {"mapping_id": "ER-001", "confidence": 1.0, "status": "pending"},
        {"mapping_id": "ER-002", "confidence": 0.5, "status": "pending"},
    ]


def test_gate_require_approval_true_stops_all():
    """When REQUIRE_HUMAN_APPROVAL=True, all proposals need review."""
    result = apply_gate(
        _make_high_confidence_proposals(),
        require_human_approval=True,
        confidence_floor=0.7,
    )
    assert len(result["needs_review"]) == 2
    assert len(result["auto_promote"]) == 0
    assert result["gate_action"] == "stop"


def test_gate_require_approval_false_auto_promotes_high_confidence():
    """When False, high confidence proposals auto-promote."""
    result = apply_gate(
        _make_high_confidence_proposals(),
        require_human_approval=False,
        confidence_floor=0.7,
    )
    assert len(result["auto_promote"]) == 2
    assert len(result["needs_review"]) == 0
    assert result["gate_action"] == "auto_promote"


def test_gate_low_confidence_always_stops():
    """Confidence < 0.7 always needs review, even with toggle off."""
    result = apply_gate(
        _make_mixed_confidence_proposals(),
        require_human_approval=False,
        confidence_floor=0.7,
    )
    assert len(result["auto_promote"]) == 1
    assert len(result["needs_review"]) == 1
    assert result["needs_review"][0]["mapping_id"] == "ER-002"
    assert result["gate_action"] == "stop"


def test_gate_low_confidence_stops_even_with_approval_off():
    """Hard floor: <0.7 stops regardless of toggle."""
    proposals = [{"mapping_id": "ER-001", "confidence": 0.3, "status": "pending"}]
    result = apply_gate(
        proposals,
        require_human_approval=False,
        confidence_floor=0.7,
    )
    assert len(result["needs_review"]) == 1
    assert result["gate_action"] == "stop"


def test_gate_exactly_at_floor_auto_promotes():
    """Confidence exactly at floor (0.7) should auto-promote when toggle is off."""
    proposals = [{"mapping_id": "ER-001", "confidence": 0.7, "status": "pending"}]
    result = apply_gate(
        proposals,
        require_human_approval=False,
        confidence_floor=0.7,
    )
    assert len(result["auto_promote"]) == 1
    assert result["gate_action"] == "auto_promote"


def test_gate_empty_proposals():
    """Empty proposals should auto-promote (nothing to stop for)."""
    result = apply_gate(
        [],
        require_human_approval=True,
        confidence_floor=0.7,
    )
    assert result["gate_action"] == "auto_promote"
    assert len(result["auto_promote"]) == 0
    assert len(result["needs_review"]) == 0
