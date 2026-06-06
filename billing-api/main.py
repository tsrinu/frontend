"""distrebute billing-service (stub)."""
import os
import secrets
from datetime import datetime, timezone, timedelta
from fastapi import FastAPI, HTTPException, Path, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

ALLOWED_ORIGINS = [o.strip() for o in os.getenv(
    "ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8080,http://localhost:8888,null"
).split(",") if o.strip()]

app = FastAPI(title="distrebute billing-service", version="0.1.0")


# Observability — exposes /metrics, integrates Sentry if SENTRY_DSN set
try:
    import sys as _s, os as _o
    _s.path.insert(0, _o.path.abspath(_o.path.join(_o.path.dirname(__file__), "..", "..", "shared")))
    _s.path.insert(0, _o.path.abspath(_o.path.join(_o.path.dirname(__file__), "..", "shared")))
    from observability import init_observability as _init_obs
    _init_obs(app, _o.path.basename(_o.path.dirname(_o.path.abspath(__file__))) or "service")
except Exception as _e:
    import logging as _log
    _log.getLogger().warning("observability skipped: %s", _e)


# ────────────────────────────────────────────────────────────────
# Shared security middleware (response headers, request size cap,
# request ID, production-mode guard, /docs hidden in prod)
# ────────────────────────────────────────────────────────────────
try:
    import sys as _ss, os as _so
    _ss.path.insert(0, _so.path.abspath(_so.path.join(_so.path.dirname(__file__), "..", "..", "shared")))
    _ss.path.insert(0, _so.path.abspath(_so.path.join(_so.path.dirname(__file__), "..", "shared")))
    from security import install_security as _install_sec, require_auth as _require_auth
    _install_sec(app)
except Exception as _se:
    import logging as _slog
    _slog.getLogger().warning("security middleware skipped: %s", _se)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
    allow_credentials=False,
)

def _now() -> str: return datetime.now(timezone.utc).isoformat()


@app.get("/healthz")
def healthz(): return {"status": "ok", "service": "billing-service"}


TIERS = [
    {"id": "tier_free", "name": "Watcher", "priceAmount": 0, "priceCurrency": "USD",
     "billingInterval": "month",
     "perks": ["All public videos", "Public comments"], "popular": False},
    {"id": "tier_supporter", "name": "Supporter", "priceAmount": 4.99, "priceCurrency": "USD",
     "billingInterval": "month",
     "perks": ["Ad-free", "Members chat", "Custom emotes", "Discord access"], "popular": True},
    {"id": "tier_insider", "name": "Insider", "priceAmount": 9.99, "priceCurrency": "USD",
     "billingInterval": "month",
     "perks": ["Early access", "Behind-the-scenes", "Monthly Q&A", "Podcast feed"], "popular": False},
    {"id": "tier_producer", "name": "Producer", "priceAmount": 24.99, "priceCurrency": "USD",
     "billingInterval": "month",
     "perks": ["Name in credits", "1:1 office hours", "Topic voting", "Annual merch"], "popular": False},
]


@app.get("/billing/memberships/tiers/{channel_id}")
def tiers(channel_id: str = Path(..., max_length=100)):
    return [{**t, "channelId": channel_id} for t in TIERS]


class Subscribe(BaseModel):
    tierId: str = Field(..., max_length=100)
    paymentMethodId: str = Field(..., max_length=200)


@app.post("/billing/memberships/subscribe", status_code=201)
def subscribe(body: Subscribe, claims: dict = Depends(_require_auth)):
    if not any(t["id"] == body.tierId for t in TIERS):
        raise HTTPException(status_code=400, detail="unknown tierId")
    return {
        "id": f"sub_{secrets.token_hex(6)}", "tierId": body.tierId,
        "status": "active", "startedAt": _now(),
        "renewsAt": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
    }


class SuperChat(BaseModel):
    streamId: str = Field(..., max_length=100)
    amount: float = Field(..., gt=0, le=10000)
    currency: str = Field("USD", max_length=3)
    message: str = Field("", max_length=200)


@app.post("/billing/super-chat", status_code=201)
def super_chat(body: SuperChat, claims: dict = Depends(_require_auth)):
    color = "blue" if body.amount < 10 else "pink" if body.amount < 50 else "gold"
    return {
        "id": f"sc_{secrets.token_hex(6)}", "streamId": body.streamId,
        "amount": body.amount, "currency": body.currency, "message": body.message,
        "color": color, "pinnedSeconds": min(int(body.amount) * 6, 300),
        "from": {"handle": "@you", "avatarUrl": ""},
    }


class GiftSubs(BaseModel):
    streamId: str = Field(..., max_length=100)
    count: int
    tierId: str = Field(..., max_length=100)


@app.post("/billing/gift-subs", status_code=201)
def gift_subs(body: GiftSubs, claims: dict = Depends(_require_auth)):
    if body.count not in (5, 25, 50, 100):
        raise HTTPException(status_code=400, detail="count must be 5/25/50/100")
    tier = next((t for t in TIERS if t["id"] == body.tierId), None)
    if not tier:
        raise HTTPException(status_code=400, detail="unknown tierId")
    return {"giftedTo": [f"viewer_{secrets.token_hex(3)}" for _ in range(body.count)],
            "totalCharged": round(body.count * tier["priceAmount"], 2)}


@app.get("/billing/creator/earnings")
def earnings(range: str = "30d", claims: dict = Depends(_require_auth)):
    if range not in ("30d", "90d", "ytd", "all"):
        raise HTTPException(status_code=400, detail="range must be 30d/90d/ytd/all")
    return {
        "rangeLabel": "Last 30 days" if range == "30d" else range,
        "totals": {"total": 14820.0, "ads": 6140.0, "tips": 3260.0,
                   "members": 5420.0, "merch": 0.0},
        "monthlyTrend": [{"month": m, "total": v} for m, v in
            [("Jun", 4720), ("Jul", 6090), ("Aug", 5640), ("Sep", 7780),
             ("Oct", 7090), ("Nov", 8920), ("Dec", 8010), ("Jan", 9810),
             ("Feb", 10530), ("Mar", 11640), ("Apr", 10980), ("May", 14820)]],
        "topVideos": [
            {"videoId": "vid_001", "title": "How we cut churn 38%…",
             "views": 1_200_000, "earnings": 2872.0},
            {"videoId": "vid_002", "title": "3 onboarding flows that beat Stripe's",
             "views": 680_000, "earnings": 1311.0},
            {"videoId": "vid_003", "title": "The metric I deleted from every dashboard",
             "views": 412_000, "earnings": 1206.0},
        ],
    }


PRICING_BY_REGION = {
    "IN": {"currency": "INR", "multiplier": 25},
    "US": {"currency": "USD", "multiplier": 1},
    "EU": {"currency": "EUR", "multiplier": 0.92},
    "BR": {"currency": "BRL", "multiplier": 4.8},
    "JP": {"currency": "JPY", "multiplier": 140},
}


@app.get("/billing/pricing/regional")
def regional(region: str = "IN"):
    if len(region) > 5:
        raise HTTPException(status_code=400, detail="invalid region")
    p = PRICING_BY_REGION.get(region.upper(), PRICING_BY_REGION["US"])
    return {
        "currency": p["currency"], "region": region.upper(),
        "tiers": [{**t,
                   "priceAmount": round(t["priceAmount"] * p["multiplier"], 2),
                   "priceCurrency": p["currency"]} for t in TIERS],
    }
