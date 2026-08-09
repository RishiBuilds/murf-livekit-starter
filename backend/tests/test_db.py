"""Unit tests for the SQLite caller-memory database layer.

These tests are fast, offline, and use temporary in-memory or temp-file
databases — no LLM or network calls required.
"""

import os
import tempfile

import pytest

from db import (
    _deep_merge_facts,
    find_user_by_name,
    get_user,
    init_db,
    normalize_user_id,
    sanitize_facts,
    save_user_memory,
)


@pytest.fixture()
def db_path():
    """Create a temporary SQLite database for each test."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    yield path
    os.unlink(path)


# ── normalize_user_id ──────────────────────────────────────────────


class TestNormalizeUserId:
    def test_simple_name(self):
        assert normalize_user_id("Ramesh") == "user_ramesh"

    def test_multi_word(self):
        assert normalize_user_id("Ramesh Kumar") == "user_ramesh_kumar"

    def test_strips_whitespace(self):
        assert normalize_user_id("  Priya  ") == "user_priya"

    def test_special_characters(self):
        assert normalize_user_id("Héllo Wörld!") == "user_hello_world"

    def test_empty_string(self):
        assert normalize_user_id("") == "user_unknown"

    def test_only_special_chars(self):
        assert normalize_user_id("!!!") == "user_unknown"


# ── sanitize_facts ────────────────────────────────────────────────


class TestSanitizeFacts:
    def test_drops_sensitive_keys(self):
        facts = {
            "account_number": "1234567890",
            "schemes_checked": ["PM-KISAN"],
        }
        result = sanitize_facts(facts)
        assert "account_number" not in result
        assert result["schemes_checked"] == ["PM-KISAN"]

    def test_drops_aadhaar_key(self):
        facts = {"aadhaar": "1234-5678-9012", "state": "UP"}
        result = sanitize_facts(facts)
        assert "aadhaar" not in result
        assert result["state"] == "UP"

    def test_drops_pan_key(self):
        facts = {"pan": "ABCDE1234F"}
        result = sanitize_facts(facts)
        assert "pan" not in result

    def test_drops_pin_otp_password_cvv(self):
        for key in ("pin", "otp", "password", "cvv"):
            result = sanitize_facts({key: "1234"})
            assert key not in result

    def test_redacts_aadhaar_in_value(self):
        facts = {"notes": "Aadhaar is 1234 5678 9012"}
        result = sanitize_facts(facts)
        assert "1234 5678 9012" not in result["notes"]
        assert "[REDACTED]" in result["notes"]

    def test_redacts_pan_in_value(self):
        facts = {"notes": "PAN card ABCDE1234F shown"}
        result = sanitize_facts(facts)
        assert "ABCDE1234F" not in result["notes"]
        assert "[REDACTED]" in result["notes"]

    def test_redacts_account_number_in_value(self):
        facts = {"notes": "Account 123456789012345 at SBI"}
        result = sanitize_facts(facts)
        assert "123456789012345" not in result["notes"]
        assert "[REDACTED]" in result["notes"]

    def test_passes_safe_facts(self):
        facts = {
            "schemes_checked": ["PM-KISAN", "MUDRA"],
            "state": "Maharashtra",
            "occupation": "farmer",
        }
        result = sanitize_facts(facts)
        assert result == facts

    def test_nested_dict_sanitisation(self):
        facts = {
            "eligibility": {
                "pin": "1234",
                "state": "Bihar",
            }
        }
        result = sanitize_facts(facts)
        assert "pin" not in result["eligibility"]
        assert result["eligibility"]["state"] == "Bihar"


# ── _deep_merge_facts ─────────────────────────────────────────────


class TestDeepMergeFacts:
    def test_new_key_added(self):
        old = {"state": "UP"}
        new = {"occupation": "farmer"}
        result = _deep_merge_facts(old, new)
        assert result == {"state": "UP", "occupation": "farmer"}

    def test_scalar_overwritten(self):
        old = {"state": "UP"}
        new = {"state": "Bihar"}
        result = _deep_merge_facts(old, new)
        assert result["state"] == "Bihar"

    def test_lists_merged_unique(self):
        old = {"schemes_checked": ["PM-KISAN"]}
        new = {"schemes_checked": ["PM-KISAN", "MUDRA"]}
        result = _deep_merge_facts(old, new)
        assert result["schemes_checked"] == ["PM-KISAN", "MUDRA"]

    def test_nested_dicts_merged(self):
        old = {"eligibility": {"state": "UP"}}
        new = {"eligibility": {"occupation": "farmer"}}
        result = _deep_merge_facts(old, new)
        assert result["eligibility"] == {
            "state": "UP",
            "occupation": "farmer",
        }


# ── Database CRUD ─────────────────────────────────────────────────


class TestDatabaseCRUD:
    def test_init_creates_table(self, db_path):
        """init_db should create the users table without error."""
        import sqlite3

        conn = sqlite3.connect(db_path)
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        conn.close()
        table_names = [t[0] for t in tables]
        assert "users" in table_names

    def test_save_and_get_user(self, db_path):
        record = save_user_memory(
            user_id="user_ramesh",
            name="Ramesh",
            facts={"schemes_checked": ["PM-KISAN"]},
            language_preference="hi-IN",
            db_path=db_path,
        )
        assert record["user_id"] == "user_ramesh"
        assert record["name"] == "Ramesh"
        assert record["facts"]["schemes_checked"] == ["PM-KISAN"]

        fetched = get_user("user_ramesh", db_path=db_path)
        assert fetched is not None
        assert fetched["name"] == "Ramesh"
        assert fetched["facts"]["schemes_checked"] == ["PM-KISAN"]

    def test_get_user_not_found(self, db_path):
        assert get_user("nonexistent", db_path=db_path) is None

    def test_find_user_by_name_case_insensitive(self, db_path):
        save_user_memory(
            user_id="user_priya",
            name="Priya",
            facts={},
            db_path=db_path,
        )
        found = find_user_by_name("priya", db_path=db_path)
        assert found is not None
        assert found["name"] == "Priya"

    def test_find_user_by_name_via_normalised_id(self, db_path):
        save_user_memory(
            user_id="user_ravi_sharma",
            name="Ravi Sharma",
            facts={},
            db_path=db_path,
        )
        found = find_user_by_name("Ravi Sharma", db_path=db_path)
        assert found is not None
        assert found["user_id"] == "user_ravi_sharma"

    def test_find_user_not_found(self, db_path):
        assert find_user_by_name("Ghost", db_path=db_path) is None

    def test_update_merges_facts(self, db_path):
        save_user_memory(
            user_id="user_ramesh",
            name="Ramesh",
            facts={"schemes_checked": ["PM-KISAN"], "state": "UP"},
            db_path=db_path,
        )
        save_user_memory(
            user_id="user_ramesh",
            name="Ramesh",
            facts={
                "schemes_checked": ["PM-KISAN", "MUDRA"],
                "occupation": "farmer",
            },
            db_path=db_path,
        )
        fetched = get_user("user_ramesh", db_path=db_path)
        assert fetched is not None
        # Lists should be merged (unique values)
        assert set(fetched["facts"]["schemes_checked"]) == {
            "PM-KISAN",
            "MUDRA",
        }
        # Old key preserved
        assert fetched["facts"]["state"] == "UP"
        # New key added
        assert fetched["facts"]["occupation"] == "farmer"

    def test_save_sanitises_sensitive_data(self, db_path):
        record = save_user_memory(
            user_id="user_test",
            name="Test",
            facts={
                "account_number": "9876543210",
                "state": "Bihar",
            },
            db_path=db_path,
        )
        assert "account_number" not in record["facts"]
        assert record["facts"]["state"] == "Bihar"

    def test_idempotent_init(self, db_path):
        """Calling init_db twice should not error or corrupt data."""
        save_user_memory(
            user_id="user_x",
            name="X",
            facts={"a": 1},
            db_path=db_path,
        )
        init_db(db_path)  # second init
        fetched = get_user("user_x", db_path=db_path)
        assert fetched is not None
        assert fetched["facts"]["a"] == 1
