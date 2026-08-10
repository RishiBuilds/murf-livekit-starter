"""Unit tests for the Scheme Eligibility Checker module.

Tests domain logic, data currency timestamps, failure path out-loud responses,
and LLM formatting without requiring live LLM or external network connections.
"""

import pytest

from scheme_checker import (
    DATA_EFFECTIVE_DATE,
    evaluate_single_scheme,
    format_eligibility_response_for_llm,
    query_scheme_eligibility,
    query_scheme_eligibility_async,
)


class TestSchemeEligibilityRules:
    def test_pm_kisan_eligible_farmer(self):
        facts = {"occupation": "farmer", "has_land": True, "land_size_hectares": 1.5, "is_taxpayer": False}
        res = evaluate_single_scheme("pm_kisan", facts)
        assert res["eligible"] is True
        assert res["status"] == "Eligible"
        assert res["data_effective_date"] == DATA_EFFECTIVE_DATE

    def test_pm_kisan_ineligible_no_land(self):
        facts = {"occupation": "farmer", "has_land": False, "land_size_hectares": 0.0, "is_taxpayer": False}
        res = evaluate_single_scheme("pm_kisan", facts)
        assert res["eligible"] is False
        assert any("land" in r.lower() for r in res["reasons"])

    def test_pm_kisan_ineligible_taxpayer(self):
        facts = {"occupation": "farmer", "has_land": True, "land_size_hectares": 2.0, "is_taxpayer": True}
        res = evaluate_single_scheme("pm_kisan", facts)
        assert res["eligible"] is False
        assert any("tax" in r.lower() for r in res["reasons"])

    def test_apy_eligible_young_worker(self):
        facts = {"occupation": "daily wager", "age": 25, "is_taxpayer": False}
        res = evaluate_single_scheme("apy", facts)
        assert res["eligible"] is True

    def test_apy_ineligible_age_over_40(self):
        facts = {"occupation": "driver", "age": 45, "is_taxpayer": False}
        res = evaluate_single_scheme("apy", facts)
        assert res["eligible"] is False
        assert any("maximum age" in r.lower() for r in res["reasons"])

    def test_mudra_eligible_shopkeeper(self):
        facts = {"occupation": "shopkeeper", "age": 30}
        res = evaluate_single_scheme("mudra", facts)
        assert res["eligible"] is True
        assert "Shishu" in res["benefits"]

    def test_ssy_eligible_girl_child(self):
        facts = {"occupation": "parent", "girl_child_age": 5}
        res = evaluate_single_scheme("ssy", facts)
        assert res["eligible"] is True

    def test_ssy_ineligible_child_over_10(self):
        facts = {"occupation": "parent", "girl_child_age": 12}
        res = evaluate_single_scheme("ssy", facts)
        assert res["eligible"] is False
        assert any("10 years" in r for r in res["reasons"])


class TestDataTimestampAndFailurePaths:
    def test_query_includes_data_effective_date(self):
        res = query_scheme_eligibility(occupation="farmer", land_size_hectares=1.0)
        assert res["success"] is True
        assert res["data_effective_date"] == "August 2026"
        assert res["data_source"] is not None

    def test_formatted_llm_response_contains_date(self):
        res = query_scheme_eligibility(scheme_name="PM-KISAN", occupation="farmer", land_size_hectares=1.0)
        formatted = format_eligibility_response_for_llm(res)
        assert "August 2026" in formatted
        assert "PM-KISAN" in formatted
        assert "QUALIFIED SCHEMES" in formatted

    @pytest.mark.asyncio
    async def test_async_query_success(self):
        res = await query_scheme_eligibility_async(scheme_name="MUDRA", occupation="artisan")
        assert res["success"] is True
        assert len(res["eligible_schemes"]) > 0

    @pytest.mark.asyncio
    async def test_timeout_failure_path_out_loud(self, monkeypatch):
        """Verify that when a lookup times out, a clear message to speak out loud is returned."""
        async def mock_wait_for(coro, timeout):
            coro.close()
            raise TimeoutError("Simulated timeout")

        monkeypatch.setattr("asyncio.wait_for", mock_wait_for)
        res = await query_scheme_eligibility_async(scheme_name="PM-KISAN", timeout_seconds=1.0)
        assert res["success"] is False
        assert res["error_type"] == "timeout"
        assert "user_message_out_loud" in res
        assert "timed out" in res["user_message_out_loud"]

        formatted = format_eligibility_response_for_llm(res)
        assert "FAILURE PATH" in formatted
        assert "INSTRUCTION FOR ASSISTANT" in formatted
        assert "out loud" in formatted.lower()
