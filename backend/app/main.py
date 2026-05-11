from fastapi import FastAPI


def create_app() -> FastAPI:
    app = FastAPI(title="Riya Backend", version="0.1.0")

    @app.get("/health")
    async def health() -> dict:
        return {"ok": True, "service": "riya-backend"}

    @app.get("/api/version")
    async def version() -> dict:
        return {"version": app.version}

    return app


app = create_app()
