from app.agents.decision_maker import (
    _fallback_decision,
    _generate_default_rationale,
    _validate_decision,
)


def test_fallback_decision_with_trigger():
    """When trigger is present, fallback should recommend publishing."""
    result = _fallback_decision(has_trigger=True)
    assert result["recommendation"] == "publish_to_github"
    assert result["confidence"] == "high"
    assert "trigger" in result["rationale"].lower()


def test_fallback_decision_without_trigger():
    """When no trigger, fallback should recommend local storage only."""
    result = _fallback_decision(has_trigger=False)
    assert result["recommendation"] == "store_locally_only"
    assert result["confidence"] == "high"
    assert "No publish trigger" in result["rationale"]


def test_validate_decision_normalizes_invalid_recommendation():
    """Invalid recommendation should be normalized based on trigger."""
    result = _validate_decision(
        {"recommendation": "invalid_action", "rationale": "test", "confidence": "high"},
        has_trigger=True,
    )
    assert result["recommendation"] == "publish_to_github"


def test_validate_decision_normalizes_invalid_confidence():
    """Invalid confidence should be normalized."""
    result = _validate_decision(
        {
            "recommendation": "publish_to_github",
            "rationale": "test",
            "confidence": "very_high",
        },
        has_trigger=True,
    )
    assert result["confidence"] in ("high", "medium", "low")


def test_validate_decision_generates_default_rationale():
    """Missing rationale should be generated."""
    result = _validate_decision(
        {"recommendation": "publish_to_github", "rationale": "", "confidence": "high"},
        has_trigger=True,
    )
    assert len(result["rationale"]) > 0


def test_generate_default_rationale_for_publish_with_trigger():
    """Rationale for publish with trigger should mention trigger."""
    rationale = _generate_default_rationale("publish_to_github", has_trigger=True)
    assert "trigger" in rationale.lower()


def test_generate_default_rationale_for_store_locally():
    """Rationale for local storage should be appropriate."""
    rationale = _generate_default_rationale("store_locally_only", has_trigger=False)
    assert "No publish trigger" in rationale or "locally" in rationale.lower()
