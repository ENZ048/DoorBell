from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from . import db
from .routers import actions, calls, demo, orders, stats, stream, webhook


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.connect()
    await db.ensure_indexes()
    yield
    await db.disconnect()


def create_app(lifespan_fn=lifespan) -> FastAPI:
    app = FastAPI(title="Riya Backend", version="0.1.0", lifespan=lifespan_fn)

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        # If detail is already shaped as {"error": {...}}, pass through. Otherwise wrap.
        if isinstance(exc.detail, dict) and "error" in exc.detail:
            return JSONResponse(status_code=exc.status_code, content=exc.detail)
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": "HTTP_ERROR", "message": str(exc.detail)}},
        )

    @app.get("/health")
    async def health() -> dict:
        return {"ok": True, "service": "riya-backend", "mongo": db.database.db is not None}

    @app.get("/api/version")
    async def version() -> dict:
        return {"version": app.version}

    app.include_router(calls.router)
    app.include_router(demo.router)
    app.include_router(orders.router)
    app.include_router(webhook.router)
    app.include_router(actions.router)
    app.include_router(stats.router)
    app.include_router(stream.router)
    return app


app = create_app()
