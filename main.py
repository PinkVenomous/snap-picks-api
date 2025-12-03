from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import List
import os
import math
import requests

app = FastAPI(
    title="Snap Picks API",
    version="1.0.0",
    description="Backend API for Snap Picks Pro – parlays, odds & more.",
)

# ---------- Models ----------

class ParlayLeg(BaseModel):
    matchup: str        # e.g. "Chiefs @ Bills"
    team: str           # e.g. "Chiefs"
    market: str = "ML"  # moneyline
    odds: int           # American odds, e.g. -145, +120
    implied_prob: float # 0–1

class ParlayResponse(BaseModel):
    sport: str
    style: str
    legs: List[ParlayLeg]
    est_hit_chance: float  # 0–100 (%)

# ---------- Odds API helpers ----------

SPORT_KEYS = {
    "nfl": "americanfootball_nfl",
    "nba": "basketball_nba",
    "mlb": "baseball_mlb",
    "nhl": "icehockey_nhl",
    "cfb": "americanfootball_ncaaf",
}


def american_to_implied_prob(odds: int) -> float:
    """Convert American odds to implied probability (0–1)."""
    if odds > 0:
        return 100 / (odds + 100)
    else:
        return -odds / (-odds + 100)


def fetch_moneyline_events(sport: str, days: int = 3) -> list:
    """
    Pull moneyline-capable events for the chosen sport
    using The Odds API.
    """
    api_key = os.getenv("ODDS_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="ODDS_API_KEY is not set on the server.",
        )

    sport_key = SPORT_KEYS.get(sport.lower())
    if not sport_key:
        raise HTTPException(status_code=400, detail=f"Unsupported sport: {sport}")

    url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds"
    params = {
        "apiKey": api_key,
        "regions": "us",
        "markets": "h2h",
        "oddsFormat": "american",
        "dateFormat": "iso",
    }

    resp = requests.get(url, params=params, timeout=10)
    if resp.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"Odds API error ({resp.status_code}): {resp.text}",
        )

    data = resp.json()
    if not isinstance(data, list) or not data:
        raise HTTPException(status_code=404, detail="No upcoming games found.")

    return data


def build_parlay(sport: str, style: str, legs: int) -> ParlayResponse:
    """
    Core parlay builder:

    - pulls odds for the sport
    - selects games & sides based on style
      (safe = favorites, spicy = underdogs, normal = mix)
    """
    events = fetch_moneyline_events(sport)
    picks: List[ParlayLeg] = []

    # Flatten into a list of candidate bets
    candidates = []
    for ev in events:
        home_team = ev.get("home_team")
        away_team = ev.get("away_team")
        matchup = f"{away_team} @ {home_team}"

        if not ev.get("bookmakers"):
            continue

        # Just use first book for now
        book = ev["bookmakers"][0]
        markets = book.get("markets", [])
        if not markets:
            continue

        h2h = markets[0]
        for outcome in h2h.get("outcomes", []):
            name = outcome.get("name")
            price = outcome.get("price")  # American odds
            if not isinstance(price, int):
                # Some APIs return float; coerce
                try:
                    price = int(price)
                except Exception:
                    continue

            prob = american_to_implied_prob(price)
            candidates.append(
                {
                    "matchup": matchup,
                    "team": name,
                    "odds": price,
                    "prob": prob,
                }
            )

    if not candidates:
        raise HTTPException(status_code=404, detail="No betting candidates found.")

    # Style filters
    if style == "safe":
        # Favorites only (negative odds)
        pool = [c for c in candidates if c["odds"] < 0]
        # Sort by highest probability
        pool.sort(key=lambda c: c["prob"], reverse=True)
    elif style == "spicy":
        # Underdogs only (positive odds)
        pool = [c for c in candidates if c["odds"] > 0]
        # Sort by lowest probability (spiciest first)
        pool.sort(key=lambda c: c["prob"])
    else:  # "normal"
        pool = candidates
        # Sort middle – not too chalky, not too crazy
        pool.sort(key=lambda c: abs(c["prob"] - 0.6))

    if len(pool) < legs:
        # If not enough in filtered pool, fall back to all candidates
        pool = candidates

    chosen = pool[:legs]

    hit_prob = 1.0
    for c in chosen:
        hit_prob *= c["prob"]
        picks.append(
            ParlayLeg(
                matchup=c["matchup"],
                team=c["team"],
                odds=c["odds"],
                implied_prob=round(c["prob"], 4),
            )
        )

    est_hit = round(hit_prob * 100, 1)

    return ParlayResponse(
        sport=sport.upper(),
        style=style,
        legs=picks,
        est_hit_chance=est_hit,
    )


# ---------- Routes ----------

@app.get("/")
def root():
    return {"message": "Snap Picks API is live"}


@app.get("/parlay", response_model=ParlayResponse)
def parlay_endpoint(
    sport: str = Query("nfl", pattern="^(nfl|nba|mlb|nhl|cfb)$"),
    style: str = Query("normal", pattern="^(safe|normal|spicy)$"),
    legs: int = Query(3, ge=2, le=10),
):
    """
    Example:
    GET /parlay?sport=nfl&style=normal&legs=3
    """
    return build_parlay(sport=sport, style=style, legs=legs)
