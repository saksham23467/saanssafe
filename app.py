"""SaansSafe web app (FastAPI). Run: uvicorn app:app --port 8000"""
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from saanssafe.agent import advise, rank_schools
from saanssafe import alerts

app = FastAPI(title="SaansSafe")
STATIC = Path(__file__).parent / "static"

class Q(BaseModel):
    place: str
    school: str = "Our School"
    start: int = 8
    end: int = 14

class M(BaseModel):
    places: list[str]
    start: int = 8
    end: int = 14

@app.post("/api/plan")
def plan(q: Q):
    try:
        return advise(q.place, q.school or "Our School", q.start, q.end)
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(502, f"Data source error: {e}")

@app.post("/api/rank")
def rank(m: M):
    return rank_schools(m.places[:15], m.start, m.end)

class Sub(BaseModel):
    school: str
    place: str
    contact: str = ""
    start: int = 8
    end: int = 14

STORE = alerts.get_store()

@app.post("/api/alerts/subscribe")
def subscribe(s: Sub):
    try:
        return alerts.subscribe(STORE, s.school, s.place, s.contact, s.start, s.end)
    except ValueError as e:
        raise HTTPException(422, str(e))

@app.get("/api/alerts/subscriptions")
def subscriptions():
    return STORE.list()

@app.delete("/api/alerts/subscriptions/{sid}")
def unsubscribe(sid: str):
    return {"deleted": STORE.delete(sid)}

@app.post("/api/alerts/run-now")
def run_now():
    return alerts.run_daily_alerts(STORE)

@app.get("/api/alerts/outbox")
def outbox():
    return STORE.outbox()

@app.get("/healthz")
def health():
    return {"ok": True}

@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")

app.mount("/static", StaticFiles(directory=STATIC), name="static")

# AWS Lambda entry (via Mangum) — optional
try:
    from mangum import Mangum
    handler = Mangum(app)
except ImportError:
    pass
