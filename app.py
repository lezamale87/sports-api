from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import statsapi
import requests
from datetime import datetime

app = FastAPI(title="Especialista BET - Central API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === CONFIGURACIÓN ===
API_KEY_SPORTS = "TU_API_KEY_AQUÍ" # <--- PEGA TU LLAVE AQUÍ

# === UTILIDADES MLB ===
def calcular_power_rating(era, whip, k):
    if era == "N/A" or whip == "N/A": return 50.0
    try:
        score = 50.0 + (4.00 - float(era)) * 10 + (1.30 - float(whip)) * 25 + (int(k) * 0.2)
        return max(10.0, min(90.0, round(score, 2)))
    except: return 50.0

def obtener_stats_pitcher(pitcher_id):
    if not pitcher_id: return {"era": "N/A", "whip": "N/A", "k": "N/A"}
    try:
        stats = statsapi.player_stat_data(pitcher_id, group="pitching", type="season")
        if stats and 'stats' in stats and len(stats['stats']) > 0:
            s = stats['stats'][0]['stats']
            return {"era": s.get("era", "0.00"), "whip": s.get("whip", "0.00"), "k": s.get("strikeOuts", 0)}
    except: pass
    return {"era": "N/A", "whip": "N/A", "k": "N/A"}

# === ENDPOINTS ===

@app.get("/api/mlb/hoy")
def obtener_mlb():
    hoy = datetime.now().strftime("%m/%d/%Y")
    try:
        juegos_raw = statsapi.schedule(date=hoy)
        res = []
        for j in juegos_raw:
            # Lógica simplificada para velocidad
            p_vis, p_loc = j.get("away_probable_pitcher"), j.get("home_probable_pitcher")
            res.append({
                "id": j.get("game_id"),
                "equipos": {
                    "vis": {"n": j.get("away_name"), "l": f"https://www.mlbstatic.com/team-logos/{j.get('away_id')}.svg"},
                    "loc": {"n": j.get("home_name"), "l": f"https://www.mlbstatic.com/team-logos/{j.get('home_id')}.svg"}
                },
                "pitchers": {"vis": p_vis or "TBD", "loc": p_loc or "TBD"}
            })
        return {"data": res}
    except: return {"error": "Error MLB"}

@app.get("/api/futbol/hoy")
def obtener_futbol():
    url = "https://v3.football.api-sports.io/fixtures"
    params = {"date": datetime.now().strftime("%Y-%m-%d"), "status": "NS"}
    headers = {"x-rapidapi-key": API_KEY_SPORTS, "x-rapidapi-host": "v3.football.api-sports.io"}
    
    try:
        response = requests.get(url, headers=headers, params=params)
        data = response.json().get("response", [])
        juegos = []
        for f in data:
            # Filtramos Ligas Top (Champions=2, Premier=39, LaLiga=140)
            if f["league"]["id"] in [2, 39, 140, 135, 78]:
                juegos.append({
                    "liga": f["league"]["name"],
                    "local": {"n": f["teams"]["home"]["name"], "l": f["teams"]["home"]["logo"]},
                    "visitante": {"n": f["teams"]["away"]["name"], "l": f["teams"]["away"]["logo"]},
                    "cuotas_mock": "1: 2.10 | X: 3.20 | 2: 3.50"
                })
        return {"data": juegos}
    except: return {"error": "Error Fútbol"}

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
                "visitante": {"n": g["teams"]["visitors"]["name"], "l": g["teams"]["visitors"]["logo"]}
            })
        return {"data": juegos}
    except: return {"error": "Error NBA"}

@app.get("/")
def home():
    return {"status": "Online", "servicios": ["MLB", "Fútbol", "NBA"]}
