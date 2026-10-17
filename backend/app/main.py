from fastapi import FastAPI

app = FastAPI(title="Tidewell API", version="0.0.1")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
