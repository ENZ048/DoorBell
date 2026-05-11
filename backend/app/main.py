from contextlib import asynccontextmanager

from fastapi import FastAPI

from . import db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.connect()
    await db.ensure_indexes()
    yield
    await db.disconnect()


def create_app(lifespan_fn=lifespan) -> FastAPI:
    app = FastAPI(title="Riya Backend", version="0.1.0", lifespan=lifespan_fn)

    @app.get("/health")
    async def health() -> dict:
        mongo_ok = db.database.db is not None
        return {"ok": True, "service": "riya-backend", "mongo": mongo_ok}

    @app.get("/api/version")
    async def version() -> dict:
        return {"version": app.version}

    return app


app = create_app()
