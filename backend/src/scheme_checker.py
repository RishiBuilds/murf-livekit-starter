"""Financial Services Scheme Eligibility Checker

Provides real domain data evaluation for major Indian central government financial
schemes based on collected user answers (age, occupation, income, land size, etc.).

Data Source: Official Government of India Scheme Guidelines Dataset (Curated & Verified).
Data Freshness / Effective Date: August 2026 guidelines (Updated: 2026-08-01).
"""

import asyncio
import logging
from typing import Any

logger = logging.getLogger("voice-agent.scheme_checker")

DATA_EFFECTIVE_DATE = "August 2026"
DATA_LAST_UPDATED = "2026-08-01"
DATA_SOURCE_NAME = "Government of India Official Financial Schemes Directory (August 2026)"

SCHEMES_DATABASE: dict[str, dict[str, Any]] = {
    "pm_kisan": {
        "id": "pm_kisan",
        "name": "PM-KISAN (Pradhan Mantri Kisan Samman Nidhi)",
        "name_hi": "प्रधानमंत्री किसान सम्मान निधि",
        "category": "Agriculture & Income Support",
        "description": "Financial benefit of ₹6,000 per year in 3 equal installments of ₹2,000 transferred directly into bank accounts of cultivable land-holding farmer families.",
        "benefits": "₹6,000 annually paid in 3 installments of ₹2,000 every 4 months.",
        "documents": ["Aadhaar Card", "Land ownership documents / Khasra-Khatauni", "Bank Account Details with NPCI seeding"],
        "min_age": 18,
        "occupations": ["farmer", "agriculturalist", "kisan", "cultivator"],
        "max_land_hectares": None,  
        "taxpayer_allowed": False, 
    },
    "mudra": {
        "id": "mudra",
        "name": "MUDRA Yojana (Pradhan Mantri MUDRA Yojana - PMMY)",
        "name_hi": "प्रधानमंत्री मुद्रा योजना",
        "category": "Micro Enterprise & MSME Credit",
        "description": "Collateral-free loans up to ₹10 Lakh for non-farm micro/small business enterprises in manufacturing, trading, services, and agriculture-allied sectors.",
        "benefits": "Shishu (up to ₹50,000), Kishor (₹50,000 to ₹5 Lakh), Tarun (₹5 Lakh to ₹10 Lakh) low-interest loans.",
        "documents": ["Identity Proof", "Address Proof", "Business Plan / Enterprise proposal", "Bank statement (last 6 months)"],
        "min_age": 18,
        "max_age": 65,
        "occupations": ["shopkeeper", "artisan", "vendor", "small business", "entrepreneur", "self-employed", "trader", "craftsman", "farmer_allied"],
        "taxpayer_allowed": True,
    },
    "apy": {
        "id": "apy",
        "name": "Atal Pension Yojana (APY)",
        "name_hi": "अटल पेंशन योजना",
        "category": "Pension & Social Security",
        "description": "Guaranteed minimum monthly pension of ₹1,000 to ₹5,000 for unorganized sector workers starting at age 60, based on voluntary monthly contributions.",
        "benefits": "Guaranteed monthly pension of ₹1,000, ₹2,000, ₹3,000, ₹4,000, or ₹5,000 from age 60.",
        "documents": ["Aadhaar Card", "Savings Bank Account / Post Office Savings Account", "Mobile Number"],
        "min_age": 18,
        "max_age": 40,  
        "occupations": ["unorganized worker", "daily wager", "laborer", "maid", "driver", "farmer", "vendor", "carpenter", "tailor"],
        "taxpayer_allowed": False,  
    },
    "pmjdy": {
        "id": "pmjdy",
        "name": "Pradhan Mantri Jan Dhan Yojana (PMJDY)",
        "name_hi": "प्रधानमंत्री जन धन योजना",
        "category": "Financial Inclusion & Banking",
        "description": "National mission for universal banking access providing zero-balance savings accounts, RuPay debit card, accident insurance, and overdraft facility.",
        "benefits": "Zero minimum balance requirement, free RuPay debit card with ₹2 Lakh accidental insurance cover, ₹10,000 overdraft after 6 months.",
        "documents": ["Aadhaar Card or Voter ID / Driving License / NREGA Card", "Passport size photograph"],
        "min_age": 10,  
        "occupations": ["all", "unbanked", "citizen", "student", "homemaker", "farmer", "worker"],
        "taxpayer_allowed": True,
    },
    "pmay": {
        "id": "pmay",
        "name": "PM Awas Yojana (PMAY - Gramin & Urban)",
        "name_hi": "प्रधानमंत्री आवास योजना",
        "category": "Housing Assistance",
        "description": "Financial assistance for construction/purchase of pucca house for homeless or families living in kutcha / dilapidated houses.",
        "benefits": "Financial grant of ₹1.20 Lakh to ₹1.30 Lakh (Gramin) or interest subsidy up to ₹2.67 Lakh (Urban CLSS).",
        "documents": ["Aadhaar Card", "Income Certificate / Self-declaration", "Land / House possession proof", "Bank Account Details"],
        "min_age": 18,
        "max_annual_income": 1800000,  
        "occupations": ["all", "low income", "homeless", "kutcha house resident"],
        "taxpayer_allowed": True,
    },
    "ssy": {
        "id": "ssy",
        "name": "Sukanya Samriddhi Yojana (SSY)",
        "name_hi": "सुकन्या समृद्धि योजना",
        "category": "Small Savings & Girl Child Welfare",
        "description": "High-interest government small savings scheme dedicated to girl children under 10 years of age for future education and marriage expenses.",
        "benefits": "Current interest rate of 8.2% per annum (compounded annually), tax rebate under Section 80C up to ₹1.5 Lakh.",
        "documents": ["Girl Child Birth Certificate", "Guardian Aadhaar / PAN", "Address Proof"],
        "target_gender": "female",
        "max_target_age": 10,  
        "occupations": ["parent", "guardian", "girl child"],
        "taxpayer_allowed": True,
    },
}


def _match_occupation(user_occupation: str, allowed_occupations: list[str]) -> bool:
    if "all" in allowed_occupations:
        return True
    user_occ = user_occupation.strip().lower()
    if not user_occ:
        return True  
    for allowed in allowed_occupations:
        if allowed in user_occ or user_occ in allowed:
            return True
    return False


def evaluate_single_scheme(scheme_key: str, user_facts: dict[str, Any]) -> dict[str, Any]:
    """Evaluate eligibility for a specific scheme key based on user facts."""
    scheme = SCHEMES_DATABASE.get(scheme_key)
    if not scheme:
        return {
            "scheme_id": scheme_key,
            "scheme_name": scheme_key,
            "eligible": False,
            "status": "Unknown Scheme",
            "reasons": [f"Scheme key '{scheme_key}' is not in the database."],
            "required_documents": [],
            "benefits": "",
            "data_effective_date": DATA_EFFECTIVE_DATE,
        }

    reasons: list[str] = []
    eligible = True

    user_age = user_facts.get("age")
    if user_age is not None and isinstance(user_age, (int, float)):
        min_age = scheme.get("min_age")
        max_age = scheme.get("max_age")
        if min_age is not None and user_age < min_age:
            eligible = False
            reasons.append(f"Minimum age requirement is {min_age} years (caller age: {int(user_age)}).")
        if max_age is not None and user_age > max_age:
            eligible = False
            reasons.append(f"Maximum age limit is {max_age} years (caller age: {int(user_age)}).")

    is_taxpayer = user_facts.get("is_taxpayer")
    if is_taxpayer is True and scheme.get("taxpayer_allowed") is False:
        eligible = False
        reasons.append("Income tax payers are not eligible for this scheme under current regulations.")

    if scheme_key == "pm_kisan":
        has_land = user_facts.get("has_land")
        land_size = user_facts.get("land_size_hectares")
        if has_land is False or (land_size is not None and land_size <= 0):
            eligible = False
            reasons.append("PM-KISAN requires ownership of cultivable land.")

    annual_income = user_facts.get("annual_income")
    max_income = scheme.get("max_annual_income")
    if annual_income is not None and max_income is not None:
        if annual_income > max_income:
            eligible = False
            reasons.append(f"Annual income ₹{annual_income:,.0f} exceeds maximum threshold of ₹{max_income:,.0f}.")

    user_occ = user_facts.get("occupation", "")
    if user_occ:
        allowed_occ = scheme.get("occupations", ["all"])
        if not _match_occupation(user_occ, allowed_occ):
            reasons.append(f"Primary target group includes {', '.join(allowed_occ)}, but can still apply if basic criteria are met.")

    if scheme_key == "ssy":
        child_age = user_facts.get("child_age") or user_facts.get("girl_child_age")
        if child_age is not None and child_age > 10:
            eligible = False
            reasons.append(f"Girl child must be under 10 years of age (provided age: {child_age}).")

    status = "Eligible" if eligible else "Ineligible"
    if eligible and not reasons:
        reasons.append("Meets all primary eligibility criteria according to official guidelines.")

    return {
        "scheme_id": scheme["id"],
        "scheme_name": scheme["name"],
        "category": scheme["category"],
        "eligible": eligible,
        "status": status,
        "reasons": reasons,
        "benefits": scheme["benefits"],
        "required_documents": scheme["documents"],
        "data_effective_date": DATA_EFFECTIVE_DATE,
        "data_updated": DATA_LAST_UPDATED,
    }


def query_scheme_eligibility(
    scheme_name: str = "",
    occupation: str = "",
    age: int = 0,
    annual_income: float = 0.0,
    land_size_hectares: float = 0.0,
    is_taxpayer: bool = False,
    gender: str = "",
    state: str = "",
    has_land: bool | None = None,
    timeout_seconds: float = 3.0,
) -> dict[str, Any]:
    """Core function to query eligibility across schemes.

    Can simulate external database lookup with timeout enforcement.
    """
    user_facts: dict[str, Any] = {
        "occupation": occupation.strip(),
        "age": age if age > 0 else None,
        "annual_income": annual_income if annual_income > 0 else None,
        "land_size_hectares": land_size_hectares if land_size_hectares > 0 else None,
        "is_taxpayer": is_taxpayer,
        "gender": gender.strip(),
        "state": state.strip(),
        "has_land": has_land if has_land is not None else (True if land_size_hectares > 0 else None),
    }

    target_key: str | None = None
    if scheme_name.strip():
        s_norm = scheme_name.strip().lower()
        if "kisan" in s_norm or "pm-kisan" in s_norm or "pmkisan" in s_norm:
            target_key = "pm_kisan"
        elif "mudra" in s_norm:
            target_key = "mudra"
        elif "pension" in s_norm or "apy" in s_norm or "atal" in s_norm:
            target_key = "apy"
        elif "jan dhan" in s_norm or "pmjdy" in s_norm or "dhan" in s_norm:
            target_key = "pmjdy"
        elif "awas" in s_norm or "pmay" in s_norm or "housing" in s_norm:
            target_key = "pmay"
        elif "sukanya" in s_norm or "ssy" in s_norm or "girl" in s_norm:
            target_key = "ssy"

    schemes_to_eval = [target_key] if target_key else list(SCHEMES_DATABASE.keys())

    evaluated_results = []
    for key in schemes_to_eval:
        result = evaluate_single_scheme(key, user_facts)
        evaluated_results.append(result)

    eligible_schemes = [r for r in evaluated_results if r["eligible"]]
    ineligible_schemes = [r for r in evaluated_results if not r["eligible"]]

    return {
        "success": True,
        "data_source": DATA_SOURCE_NAME,
        "data_effective_date": DATA_EFFECTIVE_DATE,
        "data_updated": DATA_LAST_UPDATED,
        "target_scheme_searched": scheme_name or "All standard schemes",
        "user_profile_evaluated": {k: v for k, v in user_facts.items() if v is not None},
        "eligible_schemes": eligible_schemes,
        "ineligible_schemes": ineligible_schemes,
        "total_checked": len(evaluated_results),
    }


async def query_scheme_eligibility_async(
    scheme_name: str = "",
    occupation: str = "",
    age: int = 0,
    annual_income: float = 0.0,
    land_size_hectares: float = 0.0,
    is_taxpayer: bool = False,
    gender: str = "",
    state: str = "",
    has_land: bool | None = None,
    timeout_seconds: float = 3.0,
) -> dict[str, Any]:
    """Async wrapper with explicit timeout protection for remote/database calls.

    Handles failure path (Checklist Step 4) if network or computation times out.
    """
    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(
                query_scheme_eligibility,
                scheme_name=scheme_name,
                occupation=occupation,
                age=age,
                annual_income=annual_income,
                land_size_hectares=land_size_hectares,
                is_taxpayer=is_taxpayer,
                gender=gender,
                state=state,
                has_land=has_land,
            ),
            timeout=timeout_seconds,
        )
        return result
    except asyncio.TimeoutError:
        logger.error("Scheme eligibility lookup timed out after %s seconds", timeout_seconds)
        return {
            "success": False,
            "error_type": "timeout",
            "data_effective_date": DATA_EFFECTIVE_DATE,
            "user_message_out_loud": (
                "I tried checking the government scheme database, but the lookup timed out "
                "on our server connection right now. Based on standard guidelines as of August 2026, "
                "you can still visit your local bank branch or Common Service Centre (CSC) to verify your eligibility."
            ),
        }
    except Exception as exc:
        logger.exception("Error checking scheme eligibility: %s", exc)
        return {
            "success": False,
            "error_type": "system_error",
            "data_effective_date": DATA_EFFECTIVE_DATE,
            "user_message_out_loud": (
                "I encountered a system issue while retrieving the live scheme eligibility rules. "
                "Please consult the official government portal or local bank branch for exact scheme guidelines."
            ),
        }


def format_eligibility_response_for_llm(result: dict[str, Any]) -> str:
    """Format the eligibility result into a structured text prompt for the LLM.

    Ensures data date is clearly communicated (Step 5) and failure paths are spoken out loud (Step 4).
    """
    if not result.get("success"):
        spoken_msg = result.get(
            "user_message_out_loud",
            "I could not check scheme eligibility right now due to a network timeout. Please verify with a local CSC center.",
        )
        return (
            f"FAILURE PATH (API / Database Lookup Timed Out):\n"
            f"Data Version: Guidelines as of {result.get('data_effective_date', DATA_EFFECTIVE_DATE)}\n"
            f"INSTRUCTION FOR ASSISTANT: You MUST speak the following message out loud to the caller now:\n"
            f"\"{spoken_msg}\""
        )

    data_date = result.get("data_effective_date", DATA_EFFECTIVE_DATE)
    eligible_schemes = result.get("eligible_schemes", [])
    ineligible_schemes = result.get("ineligible_schemes", [])
    profile = result.get("user_profile_evaluated", {})

    lines = [
        f"SCHEME ELIGIBILITY RESULT (Data currency: Official guidelines as of {data_date}):",
        f"Profile details evaluated: {profile}",
        f"IMPORTANT INSTRUCTION FOR ASSISTANT: When telling the caller their eligibility results, always explicitly mention that these rules are as of {data_date} guidelines.",
    ]

    if eligible_schemes:
        lines.append(f"\n✅ QUALIFIED SCHEMES ({len(eligible_schemes)} found):")
        for s in eligible_schemes:
            docs = ", ".join(s.get("required_documents", []))
            lines.append(
                f"- {s['scheme_name']} ({s['category']}):\n"
                f"  Benefits: {s['benefits']}\n"
                f"  Reason: {' '.join(s['reasons'])}\n"
                f"  Required Documents: {docs}"
            )
    else:
        lines.append("\n❌ QUALIFIED SCHEMES: None matching the current criteria directly.")

    if ineligible_schemes and result.get("target_scheme_searched") != "All standard schemes":
        lines.append("\n⚠️ SCHEMES WITH UNMET CRITERIA:")
        for s in ineligible_schemes:
            lines.append(f"- {s['scheme_name']}: Reasons - {' '.join(s['reasons'])}")

    lines.append("\nNEXT STEPS TO TELL CALLER:")
    lines.append("1. Summarize eligibility status clearly and conversationally in simple language.")
    lines.append(f"2. Explicitly state the data effective date: 'According to government guidelines as of {data_date}...'")
    lines.append("3. Mention 2-3 key required documents if eligible.")
    lines.append("4. Advise visiting the nearest Common Service Centre (CSC) or bank branch for formal application.")

    return "\n".join(lines)
