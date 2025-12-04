from fastapi import FastAPI
from pydantic import BaseModel
from typing import List

app = FastAPI()


# ---------- Existing root endpoint ----------
@app.get("/")
def read_root():
    return {"message": "Snap Picks API is live"}


# ---------- Models for /parlay ----------
class ParlayLeg(BaseModel):
    team: str
    pick: str  # e.g. "ML", "Spread", etc.


class ParlayRequest(BaseModel):
    sport: str          # e.g. "NFL"
    legs: List[ParlayLeg]
    style: str = "normal"  # "safe", "normal", "spicy"


class ParlayResponse(BaseModel):
    sport: str
    legs: List[ParlayLeg]
    style: str
    confidence: str
    note: str


# ---------- New /parlay endpoint ----------
@app.post("/parlay", response_model=ParlayResponse)
def build_parlay(req: ParlayRequest):
    """
    Very simple TEST endpoint for Snap Picks API.
    It just echoes the request and adds a fake confidence value.
    """

    num_legs = len(req.legs)

    # Totally fake confidence, just so we see something change.
    confidence_map = {
        1: "92%",
        2: "88%",
        3: "82%",
        4: "76%",
        5: "70%",
    }


from fastapi import Query

@app.get("/parlay", response_model=ParlayResponse)
async def parlay_get(
    sport: str = Query("nfl", pattern="^(nfl|nba|mlb|nhl|cfb)$"),
    style: str = Query("normal", pattern="^(safe|normal|spicy)$"),
    legs: int = Query(3, ge=1, le=10),
):
    """
    Convenience GET wrapper so you can call:
    /parlay?sport=nfl&style=normal&legs=3
    """
    # build a fake legs list just for testing
    from typing import List

    legs_list: List[ParlayLeg] = []
    for i in range(legs):
        legs_list.append(ParlayLeg(team=f"Leg{i+1}", pick="ML"))

    req = ParlayRequest(sport=sport, style=style, legs=legs_list)

    # reuse the same logic as POST
    return await parlay_endpoint(req)


















    confidence = confidence_map.get(num_legs, "65%")

    note = f"Test-only parlay: {num_legs} legs for {req.sport}. No real odds used."

    return {
        "sport": req.sport,
        "legs": req.legs,
        "style": req.style,
        "confidence": confidence,
        "note": note,
    }
