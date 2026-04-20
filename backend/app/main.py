from fastapi import FastAPI

from app.api.v1 import stats

app = FastAPI(title="LEIPal API", version="0.1.0")

app.include_router(stats.router, prefix="/api/v1")


@app.get("/health")
def health():
    return {"status": "ok"}
