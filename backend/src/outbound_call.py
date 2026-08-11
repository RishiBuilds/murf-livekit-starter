import argparse
import asyncio
import logging
import os
import sys

from dotenv import load_dotenv
from livekit import api

# Load environment variables from .env.local (preferred) or .env
load_dotenv(".env.local")
load_dotenv(".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("outbound_call")


async def make_outbound_call(
    phone_number: str,
    room_name: str = "outbound-call-room",
    sip_trunk_id: str | None = None,
    participant_identity: str | None = None,
    participant_name: str | None = None,
) -> api.SIPParticipantInfo:
    """Initiates an outbound SIP call using LiveKit API.

    Args:
        phone_number: Destination phone number (e.g. "+1234567890") or SIP URI.
        room_name: LiveKit room name for the participant to join.
        sip_trunk_id: LiveKit Outbound SIP Trunk ID. Defaults to LIVEKIT_SIP_TRUNK_ID env var.
        participant_identity: Optional identity for the participant in LiveKit room.
        participant_name: Optional display name for the participant.
    """
    livekit_url = os.getenv("LIVEKIT_URL")
    api_key = os.getenv("LIVEKIT_API_KEY")
    api_secret = os.getenv("LIVEKIT_API_SECRET")
    sip_trunk_id = (
        sip_trunk_id or os.getenv("LIVEKIT_SIP_TRUNK_ID") or os.getenv("SIP_TRUNK_ID")
    )

    if not livekit_url or not api_key or not api_secret:
        logger.error(
            "Missing LiveKit credentials! Ensure LIVEKIT_URL, LIVEKIT_API_KEY, "
            "and LIVEKIT_API_SECRET are set in environment or .env.local"
        )
        sys.exit(1)

    if not sip_trunk_id:
        logger.error(
            "Missing SIP Trunk ID! Set LIVEKIT_SIP_TRUNK_ID or SIP_TRUNK_ID in .env.local or pass --trunk-id."
        )
        sys.exit(1)

    # Sanitize sip_call_to for LiveKit SIP API (expects phone number or username, not full sip:uri@domain)
    sip_call_to = phone_number.strip()
    if sip_call_to.lower().startswith("sip:"):
        sip_call_to = sip_call_to[4:]
    if "@" in sip_call_to:
        sip_call_to = sip_call_to.split("@")[0]

    # Sanitize identity
    clean_number = sip_call_to.replace("+", "")
    identity = participant_identity or f"sip_{clean_number}"
    display_name = participant_name or f"Caller ({sip_call_to})"

    logger.info("Initiating outbound SIP call...")
    logger.info("Raw Input: %s", phone_number)
    logger.info("SIP Call To User/Number: %s", sip_call_to)
    logger.info("Target Room: %s", room_name)
    logger.info("SIP Trunk ID: %s", sip_trunk_id)
    logger.info("Participant Identity: %s", identity)

    async with api.LiveKitAPI(
        url=livekit_url,
        api_key=api_key,
        api_secret=api_secret,
    ) as lk_api:
        # Dispatch AI Agent to the target room so it joins the call
        agent_name = os.getenv("LIVEKIT_AGENT_NAME", "my-agent")
        try:
            dispatch_req = api.CreateAgentDispatchRequest(
                agent_name=agent_name,
                room=room_name,
            )
            dispatch_info = await lk_api.agent_dispatch.create_dispatch(dispatch_req)
            logger.info(
                "Dispatched agent '%s' to room '%s' (Dispatch ID: %s)",
                agent_name,
                room_name,
                dispatch_info.id,
            )
        except Exception as e:
            logger.warning("Agent dispatch note: %s", e)

        request = api.CreateSIPParticipantRequest(
            sip_trunk_id=sip_trunk_id,
            sip_call_to=sip_call_to,
            room_name=room_name,
            participant_identity=identity,
            participant_name=display_name,
        )

        try:
            info = await lk_api.sip.create_sip_participant(request)
            logger.info("Outbound call dispatched successfully!")
            logger.info("Participant ID: %s", info.participant_id)
            logger.info("Participant Identity: %s", info.participant_identity)
            logger.info("Room Name: %s", info.room_name)
            return info
        except Exception as e:
            logger.exception("Failed to dispatch outbound SIP call: %s", e)
            raise


def parse_args():
    parser = argparse.ArgumentParser(
        description="Make an outbound SIP call using LiveKit API."
    )
    parser.add_argument(
        "phone_number",
        nargs="?",
        default=os.getenv("LINPHONE_SIP_URI") or os.getenv("OUTBOUND_PHONE_NUMBER"),
        help="Phone number or SIP URI to call (e.g. +1234567890 or sip:user@domain.com). Defaults to LINPHONE_SIP_URI in .env.local if set.",
    )
    parser.add_argument(
        "--room",
        default="outbound-call-room",
        help="LiveKit room name (default: outbound-call-room)",
    )
    parser.add_argument(
        "--trunk-id",
        default=None,
        help="LiveKit SIP Trunk ID (defaults to LIVEKIT_SIP_TRUNK_ID env var)",
    )
    parser.add_argument(
        "--identity",
        default=None,
        help="Participant identity in the LiveKit room",
    )
    return parser.parse_args()


async def main():
    args = parse_args()
    if not args.phone_number:
        logger.error("No phone number or SIP URI provided.")
        logger.error(
            "Usage: python src/outbound_call.py <phone_number_or_sip_uri> [--room ROOM] [--trunk-id TRUNK_ID]"
        )
        sys.exit(1)

    await make_outbound_call(
        phone_number=args.phone_number,
        room_name=args.room,
        sip_trunk_id=args.trunk_id,
        participant_identity=args.identity,
    )


if __name__ == "__main__":
    asyncio.run(main())
