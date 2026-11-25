
from fastapi import FastAPI

app = FastAPI(title="Manoa Recommendation Service")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/recommendations")
def recommendations(payload: dict):
    products = payload.get("products", [])
    limit = payload.get("limit", 8)

    return {
        "recommendations": products[:limit],
        "total": min(len(products), limit)
    }
