from __future__ import annotations

import httpx


class BolnaError(Exception):
    """Raised when Bolna API call fails."""


class BolnaClient:
    def __init__(self, api_key: str, base_url: str = "https://api.bolna.dev", timeout: float = 10.0):
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
        """POST /v2/calls — returns Bolna call_id on success."""
        payload = {
            "agent_id": agent_id,
            "recipient_phone": recipient_phone,
            "variables": variables,
            "webhook_url": webhook_url,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(f"{self.base_url}/v2/calls", json=payload, headers=headers)
        except httpx.HTTPError as e:
            raise BolnaError(f"network error calling Bolna: {e}") from e
        if resp.status_code >= 400:
            raise BolnaError(f"Bolna returned {resp.status_code}: {resp.text}")
        data = resp.json()
        # Defensive: Bolna may return id under various keys; check a few.
        for key in ("call_id", "id", "callId"):
            if key in data:
                return str(data[key])
        raise BolnaError(f"unexpected Bolna response shape: {data}")
