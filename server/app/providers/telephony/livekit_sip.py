"""Outbound PSTN calls as LiveKit SIP participants over a Plivo or Exotel SIP trunk (D-501).

place_call creates a room named after our call_ref and dials the callee into it through the
configured outbound trunk; the agent worker joins the same room. hang_up deletes the room,
which ends the SIP leg. We speak LiveKit's Twirp JSON API directly over httpx so that every
request is visible and contract-testable against fixtures.

The CLI shown is the number LiveKit sends as `sip_number`; we pass the clearance's declared
CLI and nothing else (REQ-CLI-01). The trunk is provisioned with exactly the declared CLIs,
so the operator also rejects any other.
"""

from __future__ import annotations

from typing import Literal

import httpx
from livekit import api as lk
from pydantic import BaseModel, ConfigDict, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.errors import ConfigError, ProviderError, ProviderTimeoutError
from app.providers.base import PlacedCall
from app.providers.livekit_settings import LiveKitSettings

TrunkVendor = Literal["plivo", "exotel"]
CREATE_PATH = "/twirp/livekit.SIP/CreateSIPParticipant"
DELETE_ROOM_PATH = "/twirp/livekit.RoomService/DeleteRoom"
# Ring long enough for a person to reach the phone, short enough not to hold a slot.
RINGING_TIMEOUT = "30s"
# Outbound service calls are short; a hard cap stops a stuck call from running up cost.
MAX_CALL_DURATION = "600s"


class SipTrunkSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AV_SIP_", extra="ignore", frozen=True)

    outbound_trunk_id: str = ""
    timeout_seconds: float = 10.0

    def require_complete(self) -> None:
        if not self.outbound_trunk_id:
            raise ConfigError("AV_SIP_OUTBOUND_TRUNK_ID must be set for real telephony")


class _Participant(BaseModel):
    model_config = ConfigDict(extra="ignore")
    participant_id: str
    room_name: str
    sip_call_id: str = ""


class LiveKitSipTelephony:
    def __init__(
        self,
        vendor: TrunkVendor,
        livekit: LiveKitSettings,
        trunk: SipTrunkSettings,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        livekit.require_complete()
        trunk.require_complete()
        self.name: str = vendor
        self._lk = livekit
        self._trunk = trunk
        self._client = httpx.Client(
            base_url=livekit.http_url, timeout=trunk.timeout_seconds, transport=transport
        )

    def _token(self, *, sip_call: bool, room: str) -> str:
        token = lk.AccessToken(self._lk.api_key, self._lk.api_secret).with_identity("av-dispatcher")
        if sip_call:
            token = token.with_sip_grants(lk.SIPGrants(call=True))
        token = token.with_grants(lk.VideoGrants(room_create=True, room_admin=True, room=room))
        return token.to_jwt()

    def _post(self, path: str, body: dict[str, object], token: str) -> httpx.Response:
        try:
            response = self._client.post(
                path, json=body, headers={"Authorization": f"Bearer {token}"}
            )
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError(f"livekit {path} timed out") from exc
        except httpx.HTTPError as exc:
            raise ProviderError(f"livekit {path} failed: {exc}") from exc
        if response.status_code != 200:
            raise ProviderError(f"livekit {path} returned {response.status_code}")
        return response

    def place_call(self, to_e164: str, from_cli_e164: str, call_ref: str) -> PlacedCall:
        body: dict[str, object] = {
            "sip_trunk_id": self._trunk.outbound_trunk_id,
            "sip_call_to": to_e164,
            "sip_number": from_cli_e164,
            "room_name": call_ref,
            "participant_identity": "callee",
            "participant_name": "callee",
            "ringing_timeout": RINGING_TIMEOUT,
            "max_call_duration": MAX_CALL_DURATION,
            # Return once the INVITE is accepted; answer detection and AMD run in the worker.
            "wait_until_answered": False,
        }
        response = self._post(CREATE_PATH, body, self._token(sip_call=True, room=call_ref))
        try:
            participant = _Participant.model_validate_json(response.content)
        except ValidationError as exc:
            raise ProviderError("livekit returned an unexpected SIP participant body") from exc
        return PlacedCall(provider_call_id=participant.room_name)

    def hang_up(self, provider_call_id: str) -> None:
        token = self._token(sip_call=False, room=provider_call_id)
        self._post(DELETE_ROOM_PATH, {"room": provider_call_id}, token)
