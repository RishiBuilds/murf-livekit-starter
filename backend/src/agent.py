import asyncio
import json
import logging
import threading

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
    create_escalation as db_create_escalation,
    find_user_by_name,
    get_user,
    init_db,
    normalize_user_id,
    save_user_memory,
)
from escalation_api import run_server
from prompt import SYSTEM_PROMPT
from scheme_checker import (
    format_eligibility_response_for_llm,
    query_scheme_eligibility_async,
)

logger = logging.getLogger("agent")

load_dotenv(".env.local")

_escalation_api_thread: threading.Thread | None = None
_escalation_api_lock = threading.Lock()


def ensure_escalation_api_started(port: int = 8000) -> None:
    """Ensure the Escalation REST API & Web Dashboard is running in a background thread."""
    global _escalation_api_thread
    with _escalation_api_lock:
        if _escalation_api_thread is not None and _escalation_api_thread.is_alive():
            return

        def _runner():
            try:
                run_server(port=port)
            except OSError as e:
                logger.info(
                    "Escalation API server port %d already in use or active: %s",
                    port,
                    e,
                )
            except Exception as exc:
                logger.error("Error in background Escalation API server: %s", exc)

        _escalation_api_thread = threading.Thread(
            target=_runner, daemon=True, name="EscalationAPIServer"
        )
        _escalation_api_thread.start()
        logger.info(
            "Background Escalation Support API & Web Dashboard automatically started at http://localhost:%d/",
            port,
        )


# Ensure escalation API server starts immediately when agent module is loaded
ensure_escalation_api_started()


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
            logger.exception(
                "Unexpected error in check_scheme_eligibility tool: %s", err
            )
            return (
                "FAILURE PATH (System Error):\n"
                "Data Version: Guidelines as of August 2026\n"
                "INSTRUCTION FOR ASSISTANT: Speak the following out loud to the caller:\n"
                '"I tried checking scheme eligibility, but encountered a system issue. '
                "According to August 2026 guidelines, please consult your nearest Common Service Centre "
                'or bank branch to check your exact eligibility."'
            )

    @llm.function_tool
    async def create_escalation(
        self,
        context: RunContext,
        caller_name: str,
        reason: str,
        summary: str,
        what_agent_checked: str,
        urgency: str,
        caller_language: str,
        preferred_followup: str,
        consent_given: bool,
    ):
        """Create a human-help escalation request when the caller's situation
        requires human intervention.

        WHEN TO CALL THIS TOOL:
        1. FRAUD REPORT: The caller reports suspected fraud, unauthorized
           transactions, or an active scam targeting them.
        2. HUMAN DECISION NEEDED: The caller needs something only a human
           can do — loan approval, account dispute, KYC override, complaint
           against a branch, or any decision requiring human authority.
        3. EXPLICIT USER COMMAND: The caller explicitly tells or asks you to
           escalate, transfer them to a human, talk to a human agent, or create
           an escalation ticket (e.g. "escalate this", "transfer me to a human",
           "talk to human agent").

        WHEN NOT TO CALL THIS TOOL:
        Do NOT call for routine questions about schemes, banking concepts,
        or fraud-awareness education. Only escalate when needed or when the
        caller explicitly asks for human transfer / escalation.

        MANDATORY CONSENT STEP:
        If YOU (the agent) initiated the escalation proposal, you MUST tell the caller
        what information you plan to share and ask for explicit permission.
        However, if the caller EXPLICITLY TOLD YOU to escalate or transfer them to a human,
        treat their command as explicit consent and call this tool immediately with consent_given=true.

        PRIVACY: NEVER include account numbers, Aadhaar, PAN, PINs, OTPs,
        or passwords in the summary field. The system will scrub patterns
        automatically, but you must avoid collecting them.

        Args:
            caller_name: The caller's name as they told you.
            reason: Why escalation is needed. Must be one of:
                'fraud' or 'human_decision_needed'.
            summary: A 2-3 sentence summary: who needs help, what happened,
                and how urgent it is. Do NOT include sensitive identifiers.
            what_agent_checked: What you (the agent) already verified or
                discussed with the caller before escalating.
            urgency: How urgent this is. Must be one of:
                'critical' (active fraud in progress),
                'high' (fraud report or important decision),
                'medium' (non-urgent human decision).
            caller_language: The caller's preferred language code
                (e.g. 'hi-IN', 'en-IN').
            preferred_followup: How the caller wants to be contacted.
                Must be one of: 'phone', 'email', 'sms'.
            consent_given: True only if the caller explicitly agreed to
                have their information shared with a human agent.
        """
        if not consent_given:
            logger.info(
                "Escalation consent not given by %s — skipping.", caller_name
            )
            return (
                "The caller declined to share their information for escalation. "
                "Nothing was sent. Respect their choice and continue helping "
                "them as best you can. If they are reporting active fraud, "
                "still advise them to call 1930 and visit cybercrime.gov.in."
            )

        logger.info(
            "Creating escalation for %s (reason=%s, urgency=%s)",
            caller_name,
            reason,
            urgency,
        )

        record = await asyncio.to_thread(
            db_create_escalation,
            caller_name=caller_name,
            reason=reason,
            summary=summary,
            what_agent_checked=what_agent_checked,
            urgency=urgency,
            caller_language=caller_language,
            preferred_followup=preferred_followup,
        )

        ref_id = record["escalation_id"]
        return (
            f"Escalation created successfully. Reference ID: {ref_id}. "
            f"INSTRUCTIONS FOR ASSISTANT — read the following to the caller:\n"
            f"1. Tell them their reference number is {ref_id} and ask them "
            f"to note it down.\n"
            f"2. Explain that a human agent will review their case and "
            f"follow up via {preferred_followup}.\n"
            f"3. Do NOT promise an immediate response — say 'as soon as possible' "
            f"or 'within a reasonable timeframe'.\n"
            f"4. If this is a fraud case, also remind them to call 1930 "
            f"and report at cybercrime.gov.in right away."
        )


server = AgentServer()


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()
    init_db()
    ensure_escalation_api_started()


server.setup_fnc = prewarm


@server.rtc_session(agent_name="my-agent")
async def my_agent(ctx: JobContext):
    ensure_escalation_api_started()
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    # 1. Connect to LiveKit room FIRST
    await ctx.connect()

    # 2. Initialize and start AgentSession on connected room
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

    # 3. Wait for remote caller participant to join (timeout after 15s)
    logger.info(
        "Agent connected to room '%s'. Waiting for caller to join...", ctx.room.name
    )
    try:
        participant = await asyncio.wait_for(ctx.wait_for_participant(), timeout=15.0)
    except Exception as err:
        logger.warning("Wait for participant timed out or interrupted: %s", err)
        participant = next(iter(ctx.room.remote_participants.values()), None)

    if not participant:
        logger.warning("No remote participant found in room %s", ctx.room.name)
        return

    logger.info(
        "Caller participant present: identity='%s', name='%s', kind=%s",
        participant.identity,
        participant.name,
        participant.kind,
    )

    greeting_done = False
    _bg_tasks = set()

    async def trigger_outbound_greeting(p: rtc.RemoteParticipant):
        nonlocal greeting_done
        if greeting_done:
            return
        greeting_done = True

        phone = p.attributes.get("sip.phoneNumber") or p.identity
        name = p.name or p.identity
        is_sip = p.kind == rtc.ParticipantKind.PARTICIPANT_KIND_SIP
        caller_type = "SIP Call" if is_sip else "Web User"
        caller_summary = f"{caller_type} (Name: '{name}', Phone/Identity: '{phone}')"

        instruction = (
            f"This is a call with {caller_summary}.\n\n"
            "YOU MUST OPEN THE CALL WITH A WARM, FRIENDLY GREETING:\n"
            "Greet the caller, state that you are DhanSathi from the Financial Literacy Initiative, "
            "and ask how you can help them with government schemes, banking, or financial safety today.\n"
            "For example: 'Namaste! Main DhanSathi, Financial Literacy Initiative se. Aaj main aapki kya madad kar sakta hoon?' "
            "(Or in English: 'Namaste! This is DhanSathi from the Financial Literacy Initiative. How can I help you today?')"
        )
        await session.generate_reply(instructions=instruction)

    # For SIP calls, trigger greeting when audio track is subscribed or after brief pause
    if participant.kind == rtc.ParticipantKind.PARTICIPANT_KIND_SIP:
        logger.info(
            "SIP caller detected. Listening for audio track subscription / pickup..."
        )

        has_audio = any(
            pub.subscribed for pub in participant.track_publications.values()
        )
        if has_audio:
            await trigger_outbound_greeting(participant)
        else:

            @ctx.room.on("track_subscribed")
            def on_track_subscribed(track, publication, p):
                if p.sid == participant.sid and track.kind == rtc.TrackKind.KIND_AUDIO:
                    logger.info("Audio track subscribed for SIP participant!")
                    task = asyncio.create_task(trigger_outbound_greeting(p))
                    _bg_tasks.add(task)
                    task.add_done_callback(_bg_tasks.discard)

            # Short fallback timer (1.5 seconds) to ensure greeting fires
            await asyncio.sleep(1.5)
            if not greeting_done:
                await trigger_outbound_greeting(participant)
    else:
        await trigger_outbound_greeting(participant)


if __name__ == "__main__":
    cli.run_app(server)
