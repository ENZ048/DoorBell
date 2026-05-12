from __future__ import annotations

import httpx


class BolnaError(Exception):
    """Raised when Bolna API call fails."""


class BolnaClient:
    def __init__(
        self, api_key: str, base_url: str = "https://api.bolna.ai", timeout: float = 10.0
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def create_call(
        self,
        agent_id: str,
        recipient_phone: str,
        variables: dict,
        webhook_url: str,
    ) -> str:
        """POST /call — returns Bolna execution_id on success.

        The webhook URL is configured per-agent in the Bolna dashboard
        (Analytics tab → "Push all execution data to webhook"), not per call.
        The ``webhook_url`` parameter is accepted for API compatibility but is
        not forwarded to Bolna.

        Bolna API reference: https://www.bolna.ai/docs/api-reference/calls/make
        Required fields: agent_id, recipient_phone_number
        Optional fields: from_phone_number, user_data, agent_data,
                         retry_config, scheduled_at, bypass_call_guardrails
        Response: { "message": "...", "status": "queued",
                    "execution_id": "<uuid>" }
        """
        payload: dict = {
            "agent_id": agent_id,
            # Correct field name per Bolna docs (was recipient_phone)
            "recipient_phone_number": recipient_phone,
        }
        # Pass dynamic variables under user_data (was variables)
        if variables:
            payload["user_data"] = variables
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    f"{self.base_url}/call", json=payload, headers=headers
                )
        except httpx.HTTPError as e:
            raise BolnaError(f"network error calling Bolna: {e}") from e
        if resp.status_code >= 400:
            raise BolnaError(f"Bolna returned {resp.status_code}: {resp.text}")
        data = resp.json()
        # Defensive: check documented key first, then legacy fallbacks.
        for key in ("execution_id", "call_id", "id", "callId"):
            if key in data:
                return str(data[key])
        raise BolnaError(f"unexpected Bolna response shape: {data}")
