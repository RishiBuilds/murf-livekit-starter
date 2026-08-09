import asyncio
import logging

from dotenv import load_dotenv
from livekit import rtc
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    RunContext,
    cli,
    llm,
    room_io,
    tokenize,
)
from livekit.plugins import deepgram, google, murf, noise_cancellation, silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

from db import (
    find_user_by_name,
    get_user,
    init_db,
    normalize_user_id,
    save_user_memory,
)
from prompt import SYSTEM_PROMPT

logger = logging.getLogger("agent")

load_dotenv(".env.local")


class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(instructions=SYSTEM_PROMPT)

    @llm.function_tool
    async def lookup_caller(
        self,
        context: RunContext,
        user_id_or_name: str,
    ):
        """Look up a caller's stored profile by their name or user ID.

        Call this when a caller introduces themselves or tells you their
        name so you can greet returning callers personally and continue
        from where the last conversation ended.

        Args:
            user_id_or_name: The caller's name or their user ID.
        """
        logger.info("Looking up caller: %s", user_id_or_name)

        record = await asyncio.to_thread(get_user, normalize_user_id(user_id_or_name))
        if record is None:
            record = await asyncio.to_thread(find_user_by_name, user_id_or_name)

        if record is None:
            return f"No record found for '{user_id_or_name}'. This is a new caller."

        facts_summary = ", ".join(f"{k}: {v}" for k, v in record["facts"].items())
        return (
            f"Returning caller found. Name: {record['name']}. "
            f"Last interaction: {record['last_interaction']}. "
            f"Known facts: {facts_summary or 'none'}. "
            f"Language preference: {record['language_preference']}."
        )

    @llm.function_tool
    async def save_caller_info(
        self,
        context: RunContext,
        name: str,
        consent_given: bool,
        facts: dict,
        language_preference: str = "hi-IN",
        user_id: str = "",
    ):
        """Save what you learned about the caller in this conversation.

        IMPORTANT: You MUST ask the caller for explicit consent BEFORE
        calling this tool.  If they said no, set consent_given to false —
        the tool will refuse to save anything.

        Only store non-sensitive facts: schemes discussed, eligibility
        details (state, occupation, land size), topics covered, and
        language preference.  NEVER pass account numbers, Aadhaar, PAN,
        PINs, OTPs, or passwords.

        Args:
            name: The caller's name as they told you.
            consent_given: True only if the caller explicitly agreed to \
have their information remembered.
            facts: A dictionary of facts learned during the call. Example: \
{"schemes_checked": ["PM-KISAN"], "state": "Maharashtra", \
"occupation": "farmer", "topics_discussed": ["eligibility", "documents"]}.
            language_preference: The caller's preferred language code \
(e.g. "hi-IN", "en-IN"). Defaults to "hi-IN".
            user_id: Optional explicit user ID. If empty, one will be \
generated from the caller's name.
        """
        if not consent_given:
            logger.info("Consent not given by %s — skipping save.", name)
            return (
                "The caller declined to have their information saved. "
                "Nothing was stored. Respect their choice and continue "
                "the conversation normally."
            )

        resolved_id = user_id.strip() or normalize_user_id(name)
        logger.info(
            "Saving caller info for %s (%s) with consent",
            name,
            resolved_id,
        )

        record = await asyncio.to_thread(
            save_user_memory,
            user_id=resolved_id,
            name=name.strip(),
            facts=facts,
            language_preference=language_preference,
        )

        return (
            f"Saved successfully. User ID: {record['user_id']}. "
            f"Facts stored: {record['facts']}."
        )


server = AgentServer()


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()
    init_db()


server.setup_fnc = prewarm


@server.rtc_session(agent_name="my-agent")
async def my_agent(ctx: JobContext):
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    session = AgentSession(
        stt=deepgram.STT(model="nova-3", language="multi"),
        llm=google.LLM(
            model="gemini-3.5-flash-lite",
        ),
        tts=murf.TTS(
            voice="anisha",
            style="Conversation",
            tokenizer=tokenize.basic.SentenceTokenizer(min_sentence_len=2),
            text_pacing=True,
        ),
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        preemptive_generation=True,
    )

    await session.start(
        agent=Assistant(),
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                noise_cancellation=lambda params: (
                    noise_cancellation.BVCTelephony()
                    if params.participant.kind
                    == rtc.ParticipantKind.PARTICIPANT_KIND_SIP
                    else noise_cancellation.BVC()
                ),
            ),
        ),
    )

    await ctx.connect()


if __name__ == "__main__":
    cli.run_app(server)
