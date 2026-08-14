import logging
import os

from livekit.agents import tokenize, tts
from livekit.plugins import murf

logger = logging.getLogger("agent.voice_config")

# Default Murf Falcon voices for multi-agent system:
# - DhanSathi (Main Assistant / Triage): Anisha (Indian English / Hindi, female, friendly)
# - Bank Mitra (Banking Guide Specialist): Samar (Indian English / Hindi, male, instructional)
# - Suraksha Mitra (Fraud & Safety Specialist): Samar (Indian English / Hindi, male, authoritative)
# - Yojana Mitra (Government Scheme Specialist): Pooja (Indian English / Hindi, female, informative)
DEFAULT_MURF_VOICE_MAIN = os.getenv("MURF_VOICE_MAIN", "anisha")
DEFAULT_MURF_VOICE_BANKING = os.getenv("MURF_VOICE_BANKING", "samar")
DEFAULT_MURF_VOICE_FRAUD = os.getenv("MURF_VOICE_FRAUD", "samar")
DEFAULT_MURF_VOICE_SCHEME = os.getenv("MURF_VOICE_SCHEME", "pooja")


def create_murf_tts(
    voice: str = DEFAULT_MURF_VOICE_MAIN,
    style: str | None = "Conversation",
    api_key: str | None = None,
) -> tts.TTS | None:
    """Create a Murf TTS instance configured for real-time conversational streaming.

    Args:
        voice: The Murf voice ID (e.g. 'samar', 'anisha', 'pooja').
        style: The speech style (e.g. 'Conversation').
        api_key: Optional explicit API key. If not passed, read from MURF_API_KEY.

    Returns:
        A configured murf.TTS instance, or None if MURF_API_KEY is not configured.
    """
    key = api_key or os.getenv("MURF_API_KEY")
    if not key:
        logger.warning(
            "MURF_API_KEY not set; skipping Murf TTS instance creation for voice '%s'",
            voice,
        )
        return None

    return murf.TTS(
        api_key=key,
        voice=voice,
        style=style,
        tokenizer=tokenize.basic.SentenceTokenizer(min_sentence_len=2),
        text_pacing=True,
    )
