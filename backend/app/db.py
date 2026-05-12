from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from .config import settings


class Database:
    client: AsyncIOMotorClient | None = None
    db: AsyncIOMotorDatabase | None = None


database = Database()


async def connect(client: AsyncIOMotorClient | None = None) -> None:
    """Connect to Mongo. Pass `client` to inject (e.g., mongomock) in tests."""
    database.client = client or AsyncIOMotorClient(settings.mongodb_uri)
    database.db = database.client[settings.mongodb_db]


async def disconnect() -> None:
    if database.client is not None:
        database.client.close()
        database.client = None
        database.db = None


def orders() -> Any:
    assert database.db is not None, "DB not initialized"
    return database.db["orders"]


def call_events() -> Any:
    assert database.db is not None, "DB not initialized"
    return database.db["call_events"]


async def ensure_indexes() -> None:
    await orders().create_index("bolna_call_id", unique=True, sparse=True)
    await orders().create_index([("created_at", -1)])
    await orders().create_index("bucket")
    await call_events().create_index([("order_id", 1), ("ts", 1)])
