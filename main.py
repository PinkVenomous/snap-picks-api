from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Snap Picks API")


class ParlayRequest(BaseModel):
    sport: str
    legs: int


@app.get("/")
def root():
    return {"message": "Snap Picks API is live"}


@app.post("/parlay")
def build_parlay(req: ParlayRequest):
    """
    Super basic dummy parlay endpoint.
    Later we’ll hook this into your real logic + Odds API.
    """
    legs = []
    for i in range(req.legs):
        legs.append(
            {
                "game": f"{req.sport.upper()} Match {i + 1}",
                "pick": "home",
                "odds": -150 + i * 10,
            }
        )

    return {
        "sport": req.sport,
        "legs": legs,
        "note": "Dummy data – just confirming the API works.",
    }
