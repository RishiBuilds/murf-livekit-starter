import asyncio
import json
import logging
import threading
from datetime import datetime, timezone

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
    tts,
)
from livekit.plugins import deepgram, google, murf, noise_cancellation, silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

from banking_specialist import BankingSpecialistAgent
from db import (
    create_escalation as db_create_escalation,
)
from db import (
    find_user_by_name,
    get_user,
    init_db,
    normalize_user_id,
    save_call_log,
    save_user_memory,
)
from escalation_api import run_server
from fraud_specialist import FraudSpecialistAgent
from prompt import SYSTEM_PROMPT
from safety import classify_safety_risk
from scheme_checker import (
    format_eligibility_response_for_llm,
    query_scheme_eligibility_async,
)
from scheme_specialist import SchemeSpecialistAgent
from voice_config import (
    DEFAULT_MURF_VOICE_BANKING,
    DEFAULT_MURF_VOICE_FRAUD,
    DEFAULT_MURF_VOICE_MAIN,
    DEFAULT_MURF_VOICE_SCHEME,
    create_murf_tts,
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
    SUCCESS_TOOLS: frozenset[str] = frozenset(
        {
            "check_scheme_eligibility",
            "fraud_safety_check",
            "transfer_to_scheme_specialist",
            "transfer_to_fraud_specialist",
            "transfer_to_banking_specialist",
        }
    )

    def __init__(
        self,
        handoff_context: str = "",
        tts: tts.TTS | str | None = None,
    ) -> None:
        instructions = SYSTEM_PROMPT
        if handoff_context:
            instructions += (
                "\n\nCONTEXT FROM SPECIALIST AGENT (previous conversation summary):\n"
                f"{handoff_context}\n"
                "Use this context to continue helping the caller seamlessly. "
                "Do NOT ask them to repeat anything already covered."
            )
        tts_instance = (
            tts if tts is not None else create_murf_tts(DEFAULT_MURF_VOICE_MAIN)
        )
        if tts_instance is not None:
            super().__init__(instructions=instructions, tts=tts_instance)
        else:
            super().__init__(instructions=instructions)
        self._tools_used: set[str] = set()
        self._handoff_context = handoff_context

    async def on_enter(self) -> None:
        """Resume a hand-back without making the caller repeat their request."""
        if not self._handoff_context:
            return
        self.session.generate_reply(
            instructions=(
                "You have just received a specialist hand-back. Continue from the handoff "
                "context immediately. If the caller's current topic needs a different "
                "specialist, announce that connection and call the matching transfer tool in "
                "this turn. Do not ask them to repeat anything."
            )
        )

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
        self._tools_used.add("lookup_caller")
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
    async def fraud_safety_check(
        self,
        context: RunContext,
        caller_message: str,
    ):
        """Check a caller's description for immediate fraud danger.

        Use this before answering whenever the caller says somebody asked for an
        OTP, PIN, CVV, password, Aadhaar number, a screen-share app, remote
        access, or reports money being taken. This tool never stores the caller
        message. Do not use it for a general question such as "what is UPI?".

        Args:
            caller_message: A short paraphrase of the caller's fraud concern.
                Never include actual account numbers, OTPs, PINs, or passwords.
        """
        self._tools_used.add("fraud_safety_check")
        risk = classify_safety_risk(caller_message)
        if not risk.is_active_fraud:
            return (
                "No immediate fraud signal detected. Continue with normal financial "
                "literacy guidance and never request sensitive information."
            )

        return (
            "URGENT SAFETY INTERRUPT: Say this first, in the caller's language: "
            f'"{risk.warning}" '
            "Do not ask for, repeat, or save any sensitive details. Encourage the "
            "caller to stop the suspicious interaction. If money has moved or is at "
            "risk, tell them to call 1930 and report at cybercrime.gov.in immediately."
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
        self._tools_used.add("save_caller_info")
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
        has_cultivable_land: bool | None = None,
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
            has_cultivable_land: For PM-KISAN, whether the caller owns cultivable
                land. Leave unknown when the caller has not answered yet.
        """
        self._tools_used.add("check_scheme_eligibility")
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
                has_land=has_cultivable_land,
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
        self._tools_used.add("create_escalation")
        if not consent_given:
            logger.info("Escalation consent not given by %s — skipping.", caller_name)
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

    @llm.function_tool
    async def transfer_to_scheme_specialist(
        self,
        context: RunContext,
        conversation_summary: str,
    ):
        """Transfer the caller to Yojana Mitra, our Government Scheme Specialist.

        Call this tool immediately when the caller asks about ANY government financial
        scheme (e.g. PM-KISAN, MUDRA, APY, PMJDY, PMAY, SSY), eligibility checks,
        application process, required documents, or subsidies.

        Args:
            conversation_summary: A brief summary of what the caller asked and
                any profile details they shared so the specialist continues seamlessly.
        """
        self._tools_used.add("transfer_to_scheme_specialist")
        logger.info(
            "Handing off to Scheme Specialist (voice=%s). Context: %s",
            DEFAULT_MURF_VOICE_SCHEME,
            conversation_summary[:200],
        )

        specialist = SchemeSpecialistAgent(
            handoff_context=conversation_summary,
            tts=create_murf_tts(DEFAULT_MURF_VOICE_SCHEME),
        )
        return (
            specialist,
            "Transferring you to Yojana Mitra, our Government Scheme Specialist now.",
        )

    @llm.function_tool
    async def transfer_to_fraud_specialist(
        self,
        context: RunContext,
        conversation_summary: str,
    ):
        """Transfer the caller to Suraksha Mitra, our Fraud & Safety Specialist.

        Call this tool immediately when the caller reports a suspicious call,
        active scam, OTP/PIN/password request, unauthorized debit, or safety concern.

        Args:
            conversation_summary: A brief summary of what happened, credentials
                mentioned, and whether money moved.
        """
        self._tools_used.add("transfer_to_fraud_specialist")
        logger.info(
            "Handing off to Fraud Specialist (voice=%s). Context: %s",
            DEFAULT_MURF_VOICE_FRAUD,
            conversation_summary[:200],
        )

        specialist = FraudSpecialistAgent(
            handoff_context=conversation_summary,
            tts=create_murf_tts(DEFAULT_MURF_VOICE_FRAUD),
        )
        return (
            specialist,
            "Transferring you to Suraksha Mitra, our Fraud and Safety Specialist now.",
        )

    @llm.function_tool
    async def transfer_to_banking_specialist(
        self,
        context: RunContext,
        conversation_summary: str,
    ):
        """Transfer the caller to Bank Mitra, our Banking Guide Specialist.

        Call this tool immediately when the caller asks about everyday banking:
        UPI setup/usage, opening accounts, KYC, fixed deposits, interest rates,
        cheques, bank statements, or card usage.

        Args:
            conversation_summary: A brief summary of which banking topic the
                caller needs help with.
        """
        self._tools_used.add("transfer_to_banking_specialist")
        logger.info(
            "Handing off to Banking Specialist (voice=%s). Context: %s",
            DEFAULT_MURF_VOICE_BANKING,
            conversation_summary[:200],
        )

        specialist = BankingSpecialistAgent(
            handoff_context=conversation_summary,
            tts=create_murf_tts(DEFAULT_MURF_VOICE_BANKING),
        )
        return (
            specialist,
            "Transferring you to Bank Mitra, our Banking Guide now.",
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

    call_started_at = datetime.now(timezone.utc).isoformat()
    call_id = ctx.room.name
    assistant: Assistant | None = None
    await ctx.connect()

    main_tts = create_murf_tts(DEFAULT_MURF_VOICE_MAIN)
    session = AgentSession(
        stt=deepgram.STT(model="nova-3", language="multi"),
        llm=google.LLM(
            model="gemini-3.5-flash-lite",
        ),
        tts=main_tts
        or murf.TTS(
            voice=DEFAULT_MURF_VOICE_MAIN,
            style="Conversation",
            tokenizer=tokenize.basic.SentenceTokenizer(min_sentence_len=2),
            text_pacing=True,
        ),
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        preemptive_generation=True,
    )

    assistant = Assistant(tts=main_tts)
    await session.start(
        agent=assistant,
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

    caller_type_str = "web"

    greeting_done = False
    _bg_tasks: set = set()

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
            "Greet the caller, state that you are धनसाथी from the Financial Literacy Initiative, "
            "and ask how you can help them with government schemes, banking, or financial safety today.\n"
            "For example: 'नमस्ते! मैं धनसाथी, Financial Literacy Initiative से। आज मैं आपकी क्या मदद कर सकता हूँ?' "
            "(Or in English: 'Namaste! This is DhanSathi from the Financial Literacy Initiative. How can I help you today?')"
        )
        session.generate_reply(instructions=instruction)

    def _log_call(p: rtc.RemoteParticipant | None = None) -> None:
        """Write call log when participant disconnects or session ends."""
        nonlocal caller_type_str
        if assistant is None:
            return
        tools = list(assistant._tools_used)
        outcome = (
            "success" if assistant._tools_used & Assistant.SUCCESS_TOOLS else "failed"
        )
        identity = p.identity if p is not None else ""
        asyncio.get_event_loop().run_in_executor(
            None,
            lambda: save_call_log(
                call_id=call_id,
                room_name=ctx.room.name,
                caller_identity=identity,
                caller_type=caller_type_str,
                outcome=outcome,
                tools_used=tools,
                started_at=call_started_at,
            ),
        )
        logger.info(
            "Call ended — room=%s outcome=%s tools=%s",
            ctx.room.name,
            outcome,
            tools,
        )

    @ctx.room.on("participant_disconnected")
    def on_participant_disconnected(p: rtc.RemoteParticipant):
        _log_call(p)

    if participant.kind == rtc.ParticipantKind.PARTICIPANT_KIND_SIP:
        caller_type_str = "sip"
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

            await asyncio.sleep(1.5)
            if not greeting_done:
                await trigger_outbound_greeting(participant)
    else:
        caller_type_str = "web"
        await trigger_outbound_greeting(participant)


if __name__ == "__main__":
    cli.run_app(server)
