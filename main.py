from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def home():
    return {"message": "Snap Picks API is live"}

@app.get("/parlay")
def get_parlay():
    sample = {
        "sport": "NFL",
        "legs": [
            {"team": "Chiefs", "pick": "ML"},
            {"team": "Eagles", "pick": "ML"},
            {"team": "Ravens", "pick": "ML"}
        ],
        "style": "normal",
        "confidence": "82%"
    }
    return sample
