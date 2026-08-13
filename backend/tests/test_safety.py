"""Tests for deterministic caller-safety checks.

These checks intentionally stay small and explainable: they are a safety net
around the LLM, not a replacement for a fraud investigation.
"""

from safety import classify_safety_risk


def test_detects_credential_sharing_request():
    risk = classify_safety_risk("The caller is asking for my OTP and UPI PIN")

    assert risk.is_sensitive_data_request is True
    assert risk.is_active_fraud is True
    assert "OTP" in risk.warning


def test_detects_remote_access_scam():
    risk = classify_safety_risk("They told me to install AnyDesk to get a refund")

    assert risk.is_active_fraud is True
    assert risk.should_show_1930 is True


def test_ignores_general_financial_literacy_question():
    risk = classify_safety_risk("What is the difference between UPI and NEFT?")

    assert risk.is_active_fraud is False
    assert risk.is_sensitive_data_request is False
    assert risk.warning == ""
