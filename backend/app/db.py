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
    # Drop legacy "unique + sparse" bolna_call_id index if present.
    # Sparse only excludes missing-field docs; it still treats `null` values as
    # equal, which collides when we insert orders with bolna_call_id=null.
    # The replacement is a partial-filter index that only indexes when
    # bolna_call_id is a string (i.e., actually set by Bolna).
    try:
        await orders().drop_index("bolna_call_id_1")
    except Exception:
        pass
    await orders().create_index(
        "bolna_call_id",
        unique=True,
        partialFilterExpression={"bolna_call_id": {"$type": "string"}},
    )
    await orders().create_index([("created_at", -1)])
    await orders().create_index("bucket")
    await call_events().create_index([("order_id", 1), ("ts", 1)])
