import json
import logging
import os
import re
import sqlite3
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
