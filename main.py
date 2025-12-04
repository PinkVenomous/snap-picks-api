from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List

app = FastAPI()

# ---------- CORS so the website can call this API ----------
origins = [
    "https://snappickspro.com",
    "https://www.snappickspro.com",
    "http://localhost",           # for testing
    "http://localhost:3000",      # for React / dev if you ever use it
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
    sport: str                 # e.g. "nfl"
    legs: List[ParlayLeg]
    style: str = "normal"      # "safe", "normal", "spicy"


class ParlayResponse(BaseModel):
    sport: str
    legs: List[ParlayLeg]
    style: str
    confidence: str
    note: str


# ---------- Helper ----------
def build_parlay_response(req: ParlayRequest) -> ParlayResponse:
    num_legs = len(req.legs)

    confidence_map = {
        1: "92%",
        2: "88%",
        3: "82%",
        4: "76%",
        5: "70%",
    }

    confidence = confidence_map.get(num_legs, "65%")
    note = f"Test-only parlay: {num_legs} legs for {req.sport.upper()}. No real odds used."

    return ParlayResponse(
        sport=req.sport,
        legs=req.legs,
        style=req.style,
        confidence=confidence,
        note=note,
    )


# ---------- POST /parlay ----------
@app.post("/parlay", response_model=ParlayResponse)
async def parlay_post(req: ParlayRequest):
    return build_parlay_response(req)


# ---------- GET /parlay?sport=nfl&style=normal&legs=3 ----------
@app.get("/parlay", response_model=ParlayResponse)
async def parlay_get(
    sport: str = Query("nfl", regex="^(nfl|nba|mlb|nhl|cfb)$"),
    style: str = Query("normal", regex="^(safe|normal|spicy)$"),
    legs: int = Query(3, ge=1, le=10),
):
    legs_list: List[ParlayLeg] = []
    for i in range(legs):
        legs_list.append(ParlayLeg(team=f"Leg{i+1}", pick="ML"))

    req = ParlayRequest(sport=sport, style=style, legs=legs_list)
    return build_parlay_response(req)
