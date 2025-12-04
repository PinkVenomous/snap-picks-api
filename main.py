import os
import logging
from datetime import datetime, timedelta
from typing import List

import requests
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

# ---------- CORS so the website can call this API ----------
origins = [
    "https://snappickspro.com",
    "https://www.snappickspro.com",
    "http://localhost",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Root endpoint ----------
@app.get("/")
def read_root():
    return {"message": "Snap Picks API is live"}


# ---------- Models ----------
class ParlayLeg(BaseModel):
    team: str
    pick: str  # e.g. "ML", "Spread", etc.


class ParlayRequest(BaseModel):
    sport: str
    legs: List[ParlayLeg]
    style: str = "normal"  # "safe", "normal", "spicy"


class ParlayResponse(BaseModel):
    sport: str
    legs: List[ParlayLeg]
    style: str
    confidence: str
    note: str


# ---------- Odds API config ----------
ODDS_API_KEY = os.environ.get("ODDS_API_KEY")

SPORT_KEYS = {
    "nfl": "americanfootball_nfl",
    "nba": "basketball_nba",
    "mlb": "baseball_mlb",
    "nhl": "icehockey_nhl",
    "cfb": "americanfootball_ncaaf",
}


def fetch_moneyline_candidates(sport: str, days: int = 3) -> list[dict]:
    """
    Pulls moneyline odds from The Odds API and returns a flat list of
    {team, price, event} candidate legs.
    """
    if not ODDS_API_KEY:
        logging.error("ODDS_API_KEY is not set")
        return []

    api_sport_key = SPORT_KEYS.get(sport, sport)
    url = f"https://api.the-odds-api.com/v4/sports/{api_sport_key}/odds"

    params = {
        "apiKey": ODDS_API_KEY,
        "regions": "us",        # US books
        "markets": "h2h",       # moneyline
        "oddsFormat": "decimal",
        "dateFormat": "iso",
    }

    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logging.exception("Error talking to The Odds API: %s", e)
        return []

    # Optionally filter by start time (next N days)
    now = datetime.utcnow()
    cutoff = now + timedelta(days=days)
    candidates: list[dict] = []

    for event in data:
        # Filter by time so you don't get way-future games
        try:
            commence = datetime.fromisoformat(
                event["commence_time"].replace("Z", "+00:00")
            )
            if not (now <= commence <= cutoff):
                continue
        except Exception:
            pass  # if parsing fails, just include it

        bookmakers = event.get("bookmakers") or []
        if not bookmakers:
            continue

        # Take first bookmaker for simplicity
        markets = bookmakers[0].get("markets") or []
        market = next((m for m in markets if m.get("key") == "h2h"), None)
        if not market:
            continue

        outcomes = market.get("outcomes") or []
        for o in outcomes:
            name = o.get("name")
            price = o.get("price")
            if name is None or price is None:
                continue
            candidates.append(
                {
                    "team": name,
                    "price": float(price),
                    "event": event,
                }
            )

    return candidates


def generate_real_parlay(sport: str, style: str, legs: int) -> List[ParlayLeg]:
    """
    Turn live odds into a parlay list:
      - safe  = more favorites (shorter odds)
      - normal = middle-of-the-pack
      - spicy = more underdogs (longer odds)
    """
    candidates = fetch_moneyline_candidates(sport)

    if not candidates:
        # Fallback to fake legs if odds fail
        return [ParlayLeg(team=f"Leg{i+1}", pick="ML") for i in range(legs)]

    # Sort by decimal price: smaller = stronger favorite
    candidates_sorted = sorted(candidates, key=lambda c: c["price"])

    if style == "safe":
        pool = candidates_sorted
    elif style == "spicy":
        pool = list(reversed(candidates_sorted))
    else:  # "normal"
        # trim the extreme ends and use the middle chunk
        n = len(candidates_sorted)
        start = max(0, n // 4)
        pool = candidates_sorted[start:]

    chosen = pool[:legs]

    return [ParlayLeg(team=c["team"], pick="ML") for c in chosen]


# ---------- Helper to compute confidence + note ----------
def build_parlay_response(req: ParlayRequest, using_real_odds: bool) -> ParlayResponse:
    num_legs = len(req.legs)

    confidence_map = {
        1: "92%",
        2: "88%",
        3: "82%",
        4: "76%",
        5: "70%",
    }
    confidence = confidence_map.get(num_legs, "65%")

    if using_real_odds:
        note = (
            f"Live odds parlay: {num_legs} legs for {req.sport.upper()} "
            f"using The Odds API (test mode)."
        )
    else:
        note = f"Test-only parlay: {num_legs} legs for {req.sport.upper()}. No real odds used."

    return ParlayResponse(
        sport=req.sport,
        legs=req.legs,
        style=req.style,
        confidence=confidence,
        note=note,
    )


# ---------- POST /parlay ----------
# This version still just echoes whatever legs the caller sends.
@app.post("/parlay", response_model=ParlayResponse)
async def parlay_post(req: ParlayRequest):
    return build_parlay_response(req, using_real_odds=False)


# ---------- GET /parlay?sport=nfl&style=normal&legs=3 ----------
# This is what Wix is calling.
@app.get("/parlay", response_model=ParlayResponse)
async def parlay_get(
    sport: str = Query("nfl", regex="^(nfl|nba|mlb|nhl|cfb)$"),
    style: str = Query("normal", regex="^(safe|normal|spicy)$"),
    legs: int = Query(3, ge=1, le=10),
):
    # Build legs from REAL odds
    real_legs = generate_real_parlay(sport=sport, style=style, legs=legs)

    req = ParlayRequest(sport=sport, style=style, legs=real_legs)
    return build_parlay_response(req, using_real_odds=True)
