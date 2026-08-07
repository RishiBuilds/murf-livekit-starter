import logging

from dotenv import load_dotenv
from livekit import rtc
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    cli,
    inference,
    tokenize,
    room_io,
    UserInputTranscribedEvent,
)
from livekit.plugins import murf, silero, google, deepgram, noise_cancellation
from livekit.plugins.turn_detector.multilingual import MultilingualModel

logger = logging.getLogger("agent")

load_dotenv(".env.local")

# Financial Services voice agent — government schemes, banking literacy, fraud awareness.
SYSTEM_PROMPT = """\
You are a friendly and knowledgeable Financial Services voice assistant for Indian citizens. \
Your role covers three areas:

1. **Government Scheme Explainer** — Clearly explain central and state government financial schemes such as \
PM-KISAN, Pradhan Mantri Jan Dhan Yojana, MUDRA Yojana, Atal Pension Yojana, Sukanya Samriddhi Yojana, \
PM Awas Yojana, Stand-Up India, and others. Cover eligibility, benefits, required documents, and how to apply.

2. **Banking Literacy** — Help users understand everyday banking concepts: opening a savings or current account, \
using UPI and mobile banking safely, understanding KYC, fixed deposits, recurring deposits, interest rates, \
cheque usage, NEFT/RTGS/IMPS transfers, reading bank statements, and managing personal finances wisely.

3. **Fraud Awareness** — Educate users about common financial frauds and scams: OTP and PIN sharing tricks, \
phishing calls and fake SMS links, loan-app harassment, lottery and prize scams, QR-code payment fraud, \
and fake customer-care numbers. Explain how to identify scams, what to do if victimized (call 1930, report on \
cybercrime.gov.in), and how to protect personal financial data.

Guidelines:
- Speak in simple, clear language. Avoid heavy jargon; when a technical term is needed, explain it briefly.
- Be warm, patient, and encouraging — many users may be first-time banking customers.
- Keep answers concise and conversational since you are a voice assistant. Do not use complex formatting, emojis, or symbols.
- If you are unsure about a specific scheme detail or eligibility rule, say so honestly and suggest the user \
visit the nearest bank branch, Common Service Centre (CSC), or the official government portal for confirmation.
- Always prioritize the user's financial safety — when in doubt, advise caution.
"""


class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(instructions=SYSTEM_PROMPT)

    # To add tools, use the @function_tool decorator.
    # Here's an example that adds a simple weather tool.
    # You also have to add `from livekit.agents import function_tool, RunContext` to the top of this file
    # @function_tool
    # async def lookup_weather(self, context: RunContext, location: str):
    #     """Use this tool to look up current weather information in the given location.
    #
    #     If the location is not supported by the weather service, the tool will indicate this. You must tell the user the location's weather is unavailable.
    #
    #     Args:
    #         location: The location to look up weather information for (e.g. city name)
    #     """
    #
    #     logger.info(f"Looking up weather for {location}")
    #
    #     return "sunny with a temperature of 70 degrees."


server = AgentServer()


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


server.setup_fnc = prewarm


@server.rtc_session(agent_name="my-agent")
async def my_agent(ctx: JobContext):
    # Logging setup
    # Add any other context you want in all log entries here
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    # Set up a voice AI pipeline using Murf Falcon, Gemini, Deepgram, and the LiveKit turn detector
    session = AgentSession(
        # Speech-to-text (STT) is your agent's ears, turning the user's speech into text that the LLM can understand
        # See all available models at https://docs.livekit.io/agents/models/stt/
        stt=deepgram.STT(model="nova-3", language="multi"),
        # A Large Language Model (LLM) is your agent's brain, processing user input and generating a response
        # See all available models at https://docs.livekit.io/agents/models/llm/
        llm=google.LLM(
                model="gemini-3.5-flash-lite",
            ),
        # Text-to-speech (TTS) is your agent's voice, turning the LLM's text into speech that the user can hear
        # See all available models as well as voice selections at https://docs.livekit.io/agents/models/tts/
        tts=murf.TTS(
                voice="Shweta", 
                locale="hi-IN",
                style="Conversation",
                tokenizer=tokenize.basic.SentenceTokenizer(min_sentence_len=2),
                text_pacing=True
            ),
        # VAD and turn detection are used to determine when the user is speaking and when the agent should respond
        # See more at https://docs.livekit.io/agents/build/turns
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        # allow the LLM to generate a response while waiting for the end of turn
        # See more at https://docs.livekit.io/agents/build/audio/#preemptive-generation
        preemptive_generation=True,
    )

    @session.on("user_input_transcribed")
    def on_user_input_transcribed(event: UserInputTranscribedEvent):
        transcript = event.transcript.strip().lower()
        if not transcript:
            return

        # Check for Devanagari script (U+0900–U+097F)
        has_devanagari = any("\u0900" <= c <= "\u097F" for c in transcript)

        hindi_keywords = {
            # Common Hindi / Hinglish words
            "kya", "hai", "hain", "ka", "ki", "ke", "ko", "se", "me", "mein",
            "aur", "ya", "par", "lekin", "agar", "toh", "bhi", "nahi", "nahin",
            "haan", "ji", "na", "mat", "kab", "kahan", "kaun", "kyun", "kitna",
            "kitne", "kaise", "kaisa", "woh", "yeh", "ye", "mera", "meri", "mere",
            "humara", "humari", "aapka", "aapki", "uska", "uski", "sabhi", "sab",
            "kuch", "bahut", "zyada", "kam", "accha", "theek", "thik", "sahi",
            # Financial & banking terms (Hinglish)
            "paisa", "paise", "rupaye", "rupaya", "dhan", "bachat", "khata",
            "jama", "nikasi", "byaj", "karz", "rin", "kist", "emi", "bima",
            "beema", "nivesh", "munafa", "hani", "udhar", "bharana", "bharna",
            "bhugtaan", "rashi", "raashi", "shulk", "fees", "salary", "pension",
            "passbook", "cheque", "challan", "aadhar", "aadhaar", "pancard",
            # Government scheme terms
            "yojana", "sarkari", "sarkar", "sarkaari", "pradhan", "mantri",
            "mudra", "sukanya", "kisan", "samriddhi", "awas", "ujjwala",
            "fasal", "swasthya", "ayushman", "atal", "garib", "kalyan",
            "janani", "suraksha", "ration", "bpl", "apl", "subsidy",
            "panchayat", "tehsil", "csc", "seva", "kendra",
            # Fraud & safety terms (Hinglish)
            "dhokha", "thagi", "fraud", "scam", "loot", "chori", "nakli",
            "farzi", "jhansa", "otp", "pin", "link", "cybercrime", "complaint",
            "shikayat", "fir", "thana", "helpline", "savdhan", "satark",
            "khatarnak", "virus", "hack",
            # Action & question words
            "batao", "bataiye", "bataye", "samjhao", "samjhaiye", "chahiye",
            "karein", "karo", "karna", "milega", "milegi", "dedo", "dijiye",
            "apply", "check", "verify", "register", "download",
            # Greetings & fillers
            "namaste", "namaskar", "shukriya", "dhanyavaad", "alvida",
            "bhai", "bhaiya", "didi", "madam", "sahab", "yaar",
            "achha", "chalo", "dekho", "suno", "suniye", "haanji",
        }
        words = set(transcript.split())
        has_hindi_words = not words.isdisjoint(hindi_keywords)

        if has_devanagari or has_hindi_words:
            logger.info(f"Detected Hindi/Hinglish speech: '{event.transcript}'. Switching TTS to Hindi...")
            session.tts.update_options(voice="Shweta", locale="hi-IN")
        else:
            logger.info(f"Detected English speech: '{event.transcript}'. Switching TTS to English...")
            session.tts.update_options(voice="Shweta", locale="en-IN")
    # To use a realtime model instead of a voice pipeline, use the following session setup instead.
    # (Note: This is for the OpenAI Realtime API. For other providers, see https://docs.livekit.io/agents/models/realtime/))
    # 1. Install livekit-agents[openai]
    # 2. Set OPENAI_API_KEY in .env.local
    # 3. Add `from livekit.plugins import openai` to the top of this file
    # 4. Use the following session setup instead of the version above
    # session = AgentSession(
    #     llm=openai.realtime.RealtimeModel(voice="marin")
    # )

    # # Add a virtual avatar to the session, if desired
    # # For other providers, see https://docs.livekit.io/agents/models/avatar/
    # avatar = hedra.AvatarSession(
    #   avatar_id="...",  # See https://docs.livekit.io/agents/models/avatar/plugins/hedra
    # )
    # # Start the avatar and wait for it to join
    # await avatar.start(session, room=ctx.room)

    # Start the session, which initializes the voice pipeline and warms up the models
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

    # Join the room and connect to the user
    await ctx.connect()


if __name__ == "__main__":
    cli.run_app(server)
