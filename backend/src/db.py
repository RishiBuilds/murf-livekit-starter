import json
import logging
import os
import random
import re
import sqlite3
import string
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger("voice-agent.db")

_DEFAULT_DB_PATH = os.path.join(Path(__file__).resolve().parent, "voice_agent.db")

_SENSITIVE_KEY_NAMES: set[str] = {
    "account_number",
    "bank_account",
    "pin",
    "otp",
    "aadhaar",
    "aadhar",
    "pan",
    "cvv",
    "password",
    "credit_card",
    "debit_card",
    "ifsc",
}

_SENSITIVE_VALUE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}\b"),
    re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b"),
    re.compile(r"\b\d{9,18}\b"),
]


def normalize_user_id(name: str) -> str:
    name = unicodedata.normalize("NFKD", name)
    name = "".join(c for c in name if unicodedata.category(c) != "Mn")
    slug = re.sub(r"[^a-z0-9]+", "_", name.strip().lower()).strip("_")
    return f"user_{slug}" if slug else "user_unknown"


def sanitize_facts(facts: dict[str, Any]) -> dict[str, Any]:
    clean: dict[str, Any] = {}
    for key, value in facts.items():
        if key.lower().replace(" ", "_") in _SENSITIVE_KEY_NAMES:
            logger.warning("Dropped sensitive key %r from caller facts", key)
            continue

        if isinstance(value, str):
            scrubbed = value
            for pattern in _SENSITIVE_VALUE_PATTERNS:
                scrubbed = pattern.sub("[REDACTED]", scrubbed)
            clean[key] = scrubbed
        elif isinstance(value, dict):
            clean[key] = sanitize_facts(value)
        elif isinstance(value, list):
            clean[key] = [
                sanitize_facts(v) if isinstance(v, dict) else v for v in value
            ]
        else:
            clean[key] = value
    return clean


def _deep_merge_facts(
    existing: dict[str, Any], incoming: dict[str, Any]
) -> dict[str, Any]:
    merged = dict(existing)
    for key, new_val in incoming.items():
        old_val = merged.get(key)
        if isinstance(old_val, dict) and isinstance(new_val, dict):
            merged[key] = _deep_merge_facts(old_val, new_val)
        elif isinstance(old_val, list) and isinstance(new_val, list):
            seen = set()
            combined: list[Any] = []
            for item in old_val + new_val:
                hashable = json.dumps(item, sort_keys=True, default=str)
                if hashable not in seen:
                    seen.add(hashable)
                    combined.append(item)
            merged[key] = combined
        else:
            merged[key] = new_val
    return merged


def init_db(db_path: str = _DEFAULT_DB_PATH) -> str:
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute(
            """\
            CREATE TABLE IF NOT EXISTS users (
                user_id              TEXT PRIMARY KEY,
                name                 TEXT NOT NULL,
                language_preference  TEXT NOT NULL DEFAULT 'hi-IN',
                facts                TEXT NOT NULL DEFAULT '{}',
                last_interaction     TEXT NOT NULL,
                created_at           TEXT NOT NULL
            );
            """
        )
        conn.execute(
            """\
            CREATE INDEX IF NOT EXISTS idx_users_name
            ON users (name COLLATE NOCASE);
            """
        )
        conn.execute(
            """\
            CREATE TABLE IF NOT EXISTS escalations (
                escalation_id       TEXT PRIMARY KEY,
                caller_name         TEXT NOT NULL,
                caller_user_id      TEXT NOT NULL DEFAULT '',
                reason              TEXT NOT NULL CHECK(reason IN ('fraud', 'human_decision_needed')),
                summary             TEXT NOT NULL,
                what_agent_checked  TEXT NOT NULL DEFAULT '',
                urgency             TEXT NOT NULL DEFAULT 'medium' CHECK(urgency IN ('critical', 'high', 'medium')),
                caller_language     TEXT NOT NULL DEFAULT 'hi-IN',
                preferred_followup  TEXT NOT NULL DEFAULT 'phone' CHECK(preferred_followup IN ('phone', 'email', 'sms')),
                status              TEXT NOT NULL DEFAULT 'open' CHECK(status IN ('open', 'in_progress', 'resolved')),
                created_at          TEXT NOT NULL,
                updated_at          TEXT NOT NULL
            );
            """
        )
        conn.execute(
            """\
            CREATE INDEX IF NOT EXISTS idx_escalations_status
            ON escalations (status, urgency);
            """
        )
        conn.commit()
        logger.info("Database initialised at %s", db_path)
    finally:
        conn.close()
    return db_path


def get_user(user_id: str, db_path: str = _DEFAULT_DB_PATH) -> dict[str, Any] | None:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT * FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()
        if row is None:
            return None
        record = dict(row)
        record["facts"] = json.loads(record["facts"])
        return record
    finally:
        conn.close()


def find_user_by_name(
    name: str, db_path: str = _DEFAULT_DB_PATH
) -> dict[str, Any] | None:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT * FROM users WHERE name COLLATE NOCASE = ?",
            (name.strip(),),
        ).fetchone()

        if row is None:
            norm_id = normalize_user_id(name)
            row = conn.execute(
                "SELECT * FROM users WHERE user_id = ?", (norm_id,)
            ).fetchone()

        if row is None:
            return None
        record = dict(row)
        record["facts"] = json.loads(record["facts"])
        return record
    finally:
        conn.close()


def save_user_memory(
    user_id: str,
    name: str,
    facts: dict[str, Any] | None = None,
    language_preference: str = "hi-IN",
    db_path: str = _DEFAULT_DB_PATH,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    clean_facts = sanitize_facts(facts or {})

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        existing_row = conn.execute(
            "SELECT * FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()

        if existing_row is not None:
            old_facts = json.loads(existing_row["facts"])
            merged = _deep_merge_facts(old_facts, clean_facts)
            conn.execute(
                """\
                UPDATE users
                   SET name = ?,
                       language_preference = ?,
                       facts = ?,
                       last_interaction = ?
                 WHERE user_id = ?
                """,
                (
                    name,
                    language_preference,
                    json.dumps(merged, ensure_ascii=False),
                    now,
                    user_id,
                ),
            )
        else:
            merged = clean_facts
            conn.execute(
                """\
                INSERT INTO users
                    (user_id, name, language_preference, facts,
                     last_interaction, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    name,
                    language_preference,
                    json.dumps(merged, ensure_ascii=False),
                    now,
                    now,
                ),
            )
        conn.commit()
        logger.info("Saved memory for %s (%s)", name, user_id)
    finally:
        conn.close()

    return {
        "user_id": user_id,
        "name": name,
        "language_preference": language_preference,
        "facts": merged,
        "last_interaction": now,
    }

def _generate_escalation_id() -> str:
    """Generate a human-readable escalation reference ID like ESC-20260812-A3F7."""
    date_part = datetime.now(timezone.utc).strftime("%Y%m%d")
    rand_part = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"ESC-{date_part}-{rand_part}"


def _sanitize_text(text: str) -> str:
    """Scrub sensitive patterns (Aadhaar, PAN, account numbers) from free text."""
    scrubbed = text
    for pattern in _SENSITIVE_VALUE_PATTERNS:
        scrubbed = pattern.sub("[REDACTED]", scrubbed)
    return scrubbed


def create_escalation(
    caller_name: str,
    reason: str,
    summary: str,
    what_agent_checked: str = "",
    urgency: str = "medium",
    caller_language: str = "hi-IN",
    preferred_followup: str = "phone",
    caller_user_id: str = "",
    db_path: str = _DEFAULT_DB_PATH,
) -> dict[str, Any]:
    """Create a new escalation ticket and return its record."""
    escalation_id = _generate_escalation_id()
    now = datetime.now(timezone.utc).isoformat()

    clean_summary = _sanitize_text(summary)
    clean_checked = _sanitize_text(what_agent_checked)

    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """\
            INSERT INTO escalations
                (escalation_id, caller_name, caller_user_id, reason,
                 summary, what_agent_checked, urgency, caller_language,
                 preferred_followup, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'open', ?, ?)
            """,
            (
                escalation_id,
                caller_name.strip(),
                caller_user_id.strip(),
                reason,
                clean_summary,
                clean_checked,
                urgency,
                caller_language,
                preferred_followup,
                now,
                now,
            ),
        )
        conn.commit()
        logger.info(
            "Created escalation %s for %s (reason=%s, urgency=%s)",
            escalation_id,
            caller_name,
            reason,
            urgency,
        )
    finally:
        conn.close()

    return {
        "escalation_id": escalation_id,
        "caller_name": caller_name.strip(),
        "caller_user_id": caller_user_id.strip(),
        "reason": reason,
        "summary": clean_summary,
        "what_agent_checked": clean_checked,
        "urgency": urgency,
        "caller_language": caller_language,
        "preferred_followup": preferred_followup,
        "status": "open",
        "created_at": now,
        "updated_at": now,
    }


def get_escalation(
    escalation_id: str, db_path: str = _DEFAULT_DB_PATH
) -> dict[str, Any] | None:
    """Fetch a single escalation by its reference ID."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT * FROM escalations WHERE escalation_id = ?",
            (escalation_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def list_escalations(
    status: str | None = "open",
    db_path: str = _DEFAULT_DB_PATH,
) -> list[dict[str, Any]]:
    """List escalations filtered by status, ordered by urgency then creation time.

    Pass status=None to return all escalations.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        urgency_order = (
            "CASE urgency "
            "WHEN 'critical' THEN 1 "
            "WHEN 'high' THEN 2 "
            "WHEN 'medium' THEN 3 "
            "END"
        )
        if status is not None:
            rows = conn.execute(
                f"SELECT * FROM escalations WHERE status = ? ORDER BY {urgency_order}, created_at DESC",
                (status,),
            ).fetchall()
        else:
            rows = conn.execute(
                f"SELECT * FROM escalations ORDER BY {urgency_order}, created_at DESC"
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def update_escalation_status(
    escalation_id: str,
    new_status: str,
    db_path: str = _DEFAULT_DB_PATH,
) -> dict[str, Any] | None:
    """Update the status of an escalation (open -> in_progress -> resolved)."""
    if new_status not in ("open", "in_progress", "resolved"):
        raise ValueError(f"Invalid status: {new_status!r}")

    now = datetime.now(timezone.utc).isoformat()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute(
            "UPDATE escalations SET status = ?, updated_at = ? WHERE escalation_id = ?",
            (new_status, now, escalation_id),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM escalations WHERE escalation_id = ?",
            (escalation_id,),
        ).fetchone()
        if row:
            logger.info("Escalation %s -> %s", escalation_id, new_status)
            return dict(row)
        return None
    finally:
        conn.close()
