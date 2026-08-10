import asyncio
import json
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
from scheme_checker import (
    format_eligibility_response_for_llm,
    query_scheme_eligibility_async,
)

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
        facts: str = "{}",
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
            facts: A JSON string or dictionary of facts learned during the call. Example: \
'{"schemes_checked": ["PM-KISAN"], "state": "Maharashtra", "occupation": "farmer"}'.
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

        if isinstance(facts, str):
            try:
                parsed_facts = json.loads(facts)
            except Exception:
                parsed_facts = {"summary": facts}
        else:
            parsed_facts = facts

        record = await asyncio.to_thread(
            save_user_memory,
            user_id=resolved_id,
            name=name.strip(),
            facts=parsed_facts,
            language_preference=language_preference,
        )

        return (
            f"Saved successfully. User ID: {record['user_id']}. "
            f"Facts stored: {record['facts']}."
        )

    @llm.function_tool
    async def check_scheme_eligibility(
        self,
        context: RunContext,
        scheme_name: str = "",
        occupation: str = "",
        age: int = 0,
        annual_income: float = 0.0,
        land_size_hectares: float = 0.0,
        is_taxpayer: bool = False,
        gender: str = "",
        state: str = "",
    ):
        """Check a caller's eligibility for Indian government financial schemes based on collected profile details.

        WHEN TO CALL THIS TOOL:
        Call this tool IMMEDIATELY when the caller asks whether they (or someone else) are eligible
        for a specific financial scheme (such as PM-KISAN, MUDRA, Atal Pension Yojana, Jan Dhan Yojana,
        PM Awas Yojana, or Sukanya Samriddhi Yojana), OR when they ask what financial schemes they qualify
        for based on facts they have shared (like occupation, age, annual income, land size, or taxpayer status).

        WHEN NOT TO CALL THIS TOOL:
        Do NOT call this tool during general greetings, routine conversational small talk, or for basic
        banking concepts (like explaining what UPI is or how to open a regular account) unless eligibility
        for a specific scheme is being evaluated.

        Args:
            scheme_name: Specific scheme name if mentioned (e.g. 'PM-KISAN', 'MUDRA', 'APY', 'PMJDY', 'PMAY', 'SSY'). Leave blank to check all standard schemes.
            occupation: The caller's occupation (e.g. 'farmer', 'shopkeeper', 'artisan', 'daily wager', 'unemployed').
            age: Caller's age in years (e.g. 35). Set to 0 if unknown.
            annual_income: Caller's annual household income in INR (e.g. 150000.0). Set to 0.0 if unknown.
            land_size_hectares: Cultivable land holding in hectares (e.g. 1.5). Set to 0.0 if no land or unknown.
            is_taxpayer: True if the caller pays income tax; False otherwise.
            gender: Caller's gender ('male', 'female', or 'other').
            state: Caller's Indian state or UT (e.g. 'Maharashtra', 'Uttar Pradesh').
        """
        logger.info(
            "Checking scheme eligibility for scheme='%s', occupation='%s', age=%d, income=%f",
            scheme_name,
            occupation,
            age,
            annual_income,
        )

        try:
            result = await query_scheme_eligibility_async(
                scheme_name=scheme_name,
                occupation=occupation,
                age=age,
                annual_income=annual_income,
                land_size_hectares=land_size_hectares,
                is_taxpayer=is_taxpayer,
                gender=gender,
                state=state,
                timeout_seconds=3.0,
            )
            return format_eligibility_response_for_llm(result)
        except Exception as err:
            logger.exception("Unexpected error in check_scheme_eligibility tool: %s", err)
            return (
                "FAILURE PATH (System Error):\n"
                "Data Version: Guidelines as of August 2026\n"
                "INSTRUCTION FOR ASSISTANT: Speak the following out loud to the caller:\n"
                "\"I tried checking scheme eligibility, but encountered a system issue. "
                "According to August 2026 guidelines, please consult your nearest Common Service Centre "
                "or bank branch to check your exact eligibility.\""
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
