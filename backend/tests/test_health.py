async def test_health_returns_ok(client):
    response = await client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["service"] == "riya-backend"
    assert body["mongo"] is True


async def test_version_endpoint(client):
    response = await client.get("/api/version")
    assert response.status_code == 200
    assert response.json() == {"version": "0.1.0"}
