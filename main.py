from fastapi import FastAPI

app = FastAPI()


@app.get("/")
def root():
    return {"message": "Snap Picks API is live"}


@app.get("/parlay")
def test_parlay():
    """
    Temporary test endpoint for Snap Picks.
    Later we'll plug in real odds + AI logic.
    """
    return {
        "status": "ok",
        "message": "Parlay test endpoint is working",
        "example_slip": {
            "sport": "nfl",
            "style": "normal",
            "legs": 3,
            "picks": [
                {"team": "Team A", "pick": "Moneyline"},
                {"team": "Team B", "pick": "Moneyline"},
                {"team": "Team C", "pick": "Moneyline"},
            ],
        },
    }
