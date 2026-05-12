import httpx
import pytest

from app.bolna import BolnaClient, BolnaError

# Correct Bolna API endpoint per official docs:
# POST https://api.bolna.ai/call
# https://www.bolna.ai/docs/api-reference/calls/make
_BASE = "https://api.bolna.ai"
_ENDPOINT = f"{_BASE}/call"


async def test_create_call_posts_with_correct_payload(respx_mock):
    route = respx_mock.post(_ENDPOINT).mock(
        return_value=httpx.Response(
            200,
            json={"message": "Call queued", "status": "queued", "execution_id": "bolna_abc123"},
        )
    )
    client = BolnaClient(api_key="key123", base_url=_BASE)
    call_id = await client.create_call(
        agent_id="agent_riya",
        recipient_phone="+919876543210",
        variables={"customer_name": "Ananya", "order_id": "SNT-1"},
        webhook_url="https://riya.example.com/webhook/bolna",
    )
    assert call_id == "bolna_abc123"
    assert route.called
    req = route.calls.last.request
    assert req.headers["Authorization"] == "Bearer key123"
    body = req.read()
    # Correct field names per Bolna docs
    assert b'"agent_id"' in body
    assert b'"agent_riya"' in body
    assert b'"recipient_phone_number"' in body
    assert b"+919876543210" in body
    # Dynamic variables are passed under user_data
    assert b'"user_data"' in body
    assert b"Ananya" in body
    # Legacy wrong fields must NOT be present
    assert b'"recipient_phone"' not in body
    assert b'"variables"' not in body


async def test_create_call_raises_on_4xx(respx_mock):
    respx_mock.post(_ENDPOINT).mock(
        return_value=httpx.Response(400, json={"error": 1, "message": "bad agent"})
    )
    client = BolnaClient(api_key="k", base_url=_BASE)
    with pytest.raises(BolnaError):
        await client.create_call(
            agent_id="x", recipient_phone="+919999999999", variables={}, webhook_url="https://x"
        )


async def test_create_call_raises_on_network_error(respx_mock):
    respx_mock.post(_ENDPOINT).mock(side_effect=httpx.ConnectError("nope"))
    client = BolnaClient(api_key="k", base_url=_BASE)
    with pytest.raises(BolnaError):
        await client.create_call(
            agent_id="x", recipient_phone="+919999999999", variables={}, webhook_url="https://x"
        )
