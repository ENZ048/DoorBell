import httpx
import pytest

from app.bolna import BolnaClient, BolnaError


async def test_create_call_posts_with_correct_payload(respx_mock):
    route = respx_mock.post("https://api.bolna.dev/v2/calls").mock(
        return_value=httpx.Response(200, json={"call_id": "bolna_abc123"})
    )
    client = BolnaClient(api_key="key123", base_url="https://api.bolna.dev")
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
    assert b'"agent_id":"agent_riya"' in body or b'"agent_id": "agent_riya"' in body
    assert b"+919876543210" in body
    assert b"Ananya" in body


async def test_create_call_raises_on_4xx(respx_mock):
    respx_mock.post("https://api.bolna.dev/v2/calls").mock(
        return_value=httpx.Response(400, json={"error": "bad agent"})
    )
    client = BolnaClient(api_key="k", base_url="https://api.bolna.dev")
    with pytest.raises(BolnaError):
        await client.create_call(
            agent_id="x", recipient_phone="+919999999999", variables={}, webhook_url="https://x"
        )


async def test_create_call_raises_on_network_error(respx_mock):
    respx_mock.post("https://api.bolna.dev/v2/calls").mock(side_effect=httpx.ConnectError("nope"))
    client = BolnaClient(api_key="k", base_url="https://api.bolna.dev")
    with pytest.raises(BolnaError):
        await client.create_call(
            agent_id="x", recipient_phone="+919999999999", variables={}, webhook_url="https://x"
        )
