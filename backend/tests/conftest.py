import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from mongomock_motor import AsyncMongoMockClient

from app import db
from app.main import create_app
from app.pubsub import bus as _pubsub_bus


@pytest.fixture(autouse=True)
def reset_pubsub():
    """Clear pubsub subscribers before and after every test to prevent cross-test leakage."""
    _pubsub_bus._subscribers.clear()
    yield
    _pubsub_bus._subscribers.clear()


@pytest_asyncio.fixture
async def mock_db():
    """Fresh in-memory Mongo for each test."""
    client = AsyncMongoMockClient()
    await db.connect(client=client)
    await db.ensure_indexes()
    yield db.database.db
    await db.disconnect()


@pytest_asyncio.fixture
async def client(mock_db):
    """HTTP client bound to the FastAPI app, with mock Mongo already wired."""

    # We bypass create_app's lifespan because mock_db already connected.
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def noop_lifespan(app):
        yield

    app = create_app(lifespan_fn=noop_lifespan)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
