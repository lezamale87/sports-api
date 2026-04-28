from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import statsapi
import requests
from datetime import datetime

app = FastAPI(title="Especialista BET - Central Multi-Sport")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === CONFIGURACIÓN ===
API_KEY_SPORTS = "d32efe9d296f4f8268b3a83c024a312c"

# === ENDPOINTS ===

@app.get("/api/mlb/hoy")
def obtener_mlb():
    hoy = datetime.now().strftime("%m/%d/%Y")
    try:
        juegos_raw = statsapi.schedule(date=hoy)
        res = []
        for j in juegos_raw:
            res.append({
                "id": j.get("game_id"),
                "estado": j.get("status"),
                "equipos": {
                    "vis": {"n": j.get("away_name"), "l": f"https://www.mlbstatic.com/team-logos/{j.get('away_id')}.svg"},
                    "loc": {"n": j.get("home_name"), "l": f"https://www.mlbstatic.com/team-logos/{j.get('home_id')}.svg"}
                }
            })
        return {"total": len(res), "data": res}
    except: return {"error": "Error MLB"}

@app.get("/api/futbol/hoy")
def obtener_futbol():
    url = "https://v3.football.api-sports.io/fixtures"
    # Quitamos el filtro 'NS' para que traiga TODO lo del día (en juego, terminados y por jugar)
    params = {"date": datetime.now().strftime("%Y-%m-%d")}
    headers = {"x-rapidapi-key": API_KEY_SPORTS, "x-rapidapi-host": "v3.football.api-sports.io"}
    
    try:
        response = requests.get(url, headers=headers, params=params)
        data = response.json().get("response", [])
        juegos = []
        # Ligas Top: Champions(2), Premier(39), LaLiga(140), Serie A(135), Bundesliga(78)
        ligas_permitidas = [2, 39, 140, 135, 78]
        
        for f in data:
            if f["league"]["id"] in ligas_permitidas:
                juegos.append({
                    "liga": f["league"]["name"],
                    "estado": f["fixture"]["status"]["long"],
                    "local": {"n": f["teams"]["home"]["name"], "l": f["teams"]["home"]["logo"]},
                    "visitante": {"n": f["teams"]["away"]["name"], "l": f["teams"]["away"]["logo"]},
                    "marcador": f"{f['goals']['home']} - {f['goals']['away']}"
                })
        return {"total": len(juegos), "data": juegos}
    except Exception as e: 
        return {"error": str(e)}

@app.get("/api/nba/hoy")
def obtener_nba():
    url = "https://v2.nba.api-sports.io/games"
    params = {"date": datetime.now().strftime("%Y-%m-%d")}
    headers = {"x-rapidapi-key": API_KEY_SPORTS, "x-rapidapi-host": "v2.nba.api-sports.io"}
    
    try:
        response = requests.get(url, headers=headers, params=params)
        data = response.json().get("response", [])
        juegos = []
        for g in data:
            juegos.append({
                "estado": g["status"]["long"],
                "local": {"n": g["teams"]["home"]["name"], "l": g["teams"]["home"]["logo"]},
                "visitante": {"n": g["teams"]["visitors"]["name"], "l": g["teams"]["visitors"]["logo"]},
                "marcador": f"{g['scores']['home']['points']} - {g['scores']['visitors']['points']}"
            })
        return {"total": len(juegos), "data": juegos}
    except: return {"error": "Error NBA"}

@app.get("/")
def home():
    return {"status": "Online", "msg": "Especialista BET Central Ready"}
