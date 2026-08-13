"""Small, deterministic safety checks for financial voice conversations."""

from dataclasses import dataclass


@dataclass(frozen=True)
class SafetyRisk:
    """A non-sensitive classification result safe to use in the agent response."""

    is_active_fraud: bool = False
    is_sensitive_data_request: bool = False
    should_show_1930: bool = False
    warning: str = ""


def classify_safety_risk(text: str) -> SafetyRisk:
    """Identify common Indian financial-fraud signals without storing the text.

    The match is deliberately conservative: a general question about UPI or
    OTP is allowed through, while a request to disclose a credential or grant
    remote access is treated as an urgent warning.
    """

    normalized = " ".join(text.lower().split())
    credential_terms = ("otp", "pin", "cvv", "password", "aadhaar", "aadhar")
    request_terms = (
        "share",
        "give",
        "tell",
        "send",
        "asked",
        "asking",
        "maang",
        "bata",
        "bhej",
    )
    remote_access_terms = (
        "anydesk",
        "teamviewer",
        "remote access",
        "screen share",
        "screen-share",
        "install app",
        "refund app",
    )
    theft_terms = (
        "money deducted",
        "unauthorized transaction",
        "money stolen",
        "scammed",
        "fraud happened",
        "paise kat",
        "paise chale gaye",
    )

    credential_request = any(term in normalized for term in credential_terms) and any(
        term in normalized for term in request_terms
    )
    remote_access = any(term in normalized for term in remote_access_terms)
    theft_report = any(term in normalized for term in theft_terms)

    if credential_request:
        return SafetyRisk(
            is_active_fraud=True,
            is_sensitive_data_request=True,
            should_show_1930=True,
            warning=(
                "Stop—never share an OTP, PIN, password, CVV, or Aadhaar number. "
                "If money is at risk, call 1930 now."
            ),
        )
    if remote_access or theft_report:
        return SafetyRisk(
            is_active_fraud=True,
            should_show_1930=True,
            warning=(
                "This may be a scam. Stop talking to the caller and do not install or "
                "open anything they send. If money is at risk, call 1930 now."
            ),
        )
    return SafetyRisk()
