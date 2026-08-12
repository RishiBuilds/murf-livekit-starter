"""Unit tests for the escalation system database and helper operations.

Tests creation, sanitization, retrieval, status filtering, and status updates.
"""

import os
import tempfile
import pytest

from db import (
    create_escalation,
    get_escalation,
    init_db,
    list_escalations,
    update_escalation_status,
)


@pytest.fixture()
def db_path():
    """Create a temporary SQLite database for each test."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    yield path
    os.unlink(path)


def test_create_and_get_escalation(db_path):
    record = create_escalation(
        caller_name="Ramesh Sharma",
        reason="fraud",
        summary="Caller reported unauthorized withdrawal of ₹50,000.",
        what_agent_checked="Checked caller identity and advised stopping account.",
        urgency="critical",
        caller_language="hi-IN",
        preferred_followup="phone",
        db_path=db_path,
    )

    assert record["escalation_id"].startswith("ESC-")
    assert record["caller_name"] == "Ramesh Sharma"
    assert record["reason"] == "fraud"
    assert record["urgency"] == "critical"
    assert record["status"] == "open"

    fetched = get_escalation(record["escalation_id"], db_path=db_path)
    assert fetched is not None
    assert fetched["caller_name"] == "Ramesh Sharma"
    assert fetched["summary"] == "Caller reported unauthorized withdrawal of ₹50,000."


def test_create_escalation_sanitizes_sensitive_data(db_path):
    record = create_escalation(
        caller_name="Priya",
        reason="fraud",
        summary="Account 123456789012 had unauthorized transaction. Aadhaar 1234 5678 9012.",
        what_agent_checked="Checked PAN ABCDE1234F.",
        urgency="critical",
        db_path=db_path,
    )

    assert "123456789012" not in record["summary"]
    assert "1234 5678 9012" not in record["summary"]
    assert "[REDACTED]" in record["summary"]
    assert "ABCDE1234F" not in record["what_agent_checked"]
    assert "[REDACTED]" in record["what_agent_checked"]


def test_list_escalations_filtering_and_sorting(db_path):
    e1 = create_escalation(
        caller_name="Medium User",
        reason="human_decision_needed",
        summary="Loan restructure request.",
        urgency="medium",
        db_path=db_path,
    )
    e2 = create_escalation(
        caller_name="Critical Fraud User",
        reason="fraud",
        summary="Active scam in progress.",
        urgency="critical",
        db_path=db_path,
    )
    e3 = create_escalation(
        caller_name="High Priority User",
        reason="human_decision_needed",
        summary="Account dispute.",
        urgency="high",
        db_path=db_path,
    )

    open_tickets = list_escalations(status="open", db_path=db_path)
    assert len(open_tickets) == 3
    # Sorted by urgency: critical -> high -> medium
    assert open_tickets[0]["escalation_id"] == e2["escalation_id"]
    assert open_tickets[1]["escalation_id"] == e3["escalation_id"]
    assert open_tickets[2]["escalation_id"] == e1["escalation_id"]


def test_update_escalation_status(db_path):
    ticket = create_escalation(
        caller_name="Sunil",
        reason="human_decision_needed",
        summary="Branch complaint.",
        db_path=db_path,
    )

    esc_id = ticket["escalation_id"]
    assert list_escalations(status="open", db_path=db_path)[0]["escalation_id"] == esc_id

    # Update to in_progress
    updated = update_escalation_status(esc_id, "in_progress", db_path=db_path)
    assert updated["status"] == "in_progress"
    assert len(list_escalations(status="open", db_path=db_path)) == 0
    assert len(list_escalations(status="in_progress", db_path=db_path)) == 1

    # Update to resolved
    updated = update_escalation_status(esc_id, "resolved", db_path=db_path)
    assert updated["status"] == "resolved"
    assert len(list_escalations(status="in_progress", db_path=db_path)) == 0
    assert len(list_escalations(status="resolved", db_path=db_path)) == 1
