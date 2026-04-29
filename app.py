from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import statsapi
import requests
from datetime import datetime
from typing import Optional

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_KEY_SPORTS = "d32efe9d296f4f8268b3a83c024a312c"

# --- UTILIDADES ---
def calcular_prob_mlb(r_vis, r_loc):
    r_loc_adj = r_loc + 3.0
    total = r_vis + r_loc_adj
    p_vis, p_loc = round((r_vis/total)*100, 1), round((r_loc_adj/total)*100, 1)
    return p_vis, p_loc, ("Local" if p_loc > p_vis else "Visitante")

# --- ENDPOINTS ---

@app.get("/api/mlb/hoy")
def obtener_mlb(date: Optional[str] = None):
    target_date = date if date else datetime.now().strftime("%Y-%m-%d")
    # statsapi usa mm/dd/yyyy
    date_formatted = datetime.strptime(target_date, "%Y-%m-%d").strftime("%m/%d/%Y")
    try:
        juegos = statsapi.schedule(date=date_formatted)
        res = []
        for j in juegos:
            id_vis, id_loc = j.get("away_id"), j.get("home_id")
            # En MLB, la hora viene en j['game_date'] en formato UTC
            res.append({
                "id": j.get("game_id"),
                "estado": j.get("status"),
                "hora_utc": j.get("game_date"), # Crucial para el frontend
                "equipos": {
                    "vis": {"n": j.get("away_name"), "l": f"https://www.mlbstatic.com/team-logos/{id_vis}.svg"},
                    "loc": {"n": j.get("home_name"), "l": f"https://www.mlbstatic.com/team-logos/{id_loc}.svg"}
                },
                "prediccion_modelo": {"prob_visitante": "52.4%", "prob_local": "47.6%", "pick_recomendado": "Visitante"}
            })
        return {"data": res}
    except: return {"data": []}

@app.get("/api/futbol/hoy")
def obtener_futbol(date: Optional[str] = None):
    target_date = date if date else datetime.now().strftime("%Y-%m-%d")
    url = "https://v3.football.api-sports.io/fixtures"
    headers = {"x-rapidapi-key": API_KEY_SPORTS, "x-rapidapi-host": "v3.football.api-sports.io"}
    params = {"date": target_date}
    
    try:
        data = requests.get(url, headers=headers, params=params).json().get("response", [])
        juegos = []
        ligas = [2, 39, 140, 135, 78]
        for f in data:
            if f["league"]["id"] in ligas:
                juegos.append({
                    "liga": f["league"]["name"],
                    "estado": f["fixture"]["status"]["short"],
                    "hora_utc": f["fixture"]["date"], # Formato ISO UTC
                    "local": {"n": f["teams"]["home"]["name"], "l": f["teams"]["home"]["logo"]},
                    "visitante": {"n": f["teams"]["away"]["name"], "l": f["teams"]["away"]["logo"]},
                    "marcador": f"{f['goals']['home']} - {f['goals']['away']}",
                    "prediccion_modelo": {"prob_local": "45%", "prob_empate": "25%", "prob_visitante": "30%", "pick_recomendado": "Local"}
                })
        return {"data": juegos}
    except: return {"data": []}

@app.get("/api/nba/hoy")
def obtener_nba(date: Optional[str] = None):
    target_date = date if date else datetime.now().strftime("%Y-%m-%d")
    url = "https://v2.nba.api-sports.io/games"
    headers = {"x-rapidapi-key": API_KEY_SPORTS, "x-rapidapi-host": "v2.nba.api-sports.io"}
    params = {"date": target_date}
    
    try:
        data = requests.get(url, headers=headers, params=params).json().get("response", [])
        juegos = []
        for g in data:
            juegos.append({
                "estado": g["status"]["short"],
                "hora_utc": g["date"]["start"], # Formato ISO UTC
                "local": {"n": g["teams"]["home"]["name"], "l": g["teams"]["home"]["logo"]},
                "visitante": {"n": g["teams"]["visitors"]["name"], "l": g["teams"]["visitors"]["logo"]},
                "marcador": f"{g['scores']['home']['points']} - {g['scores']['visitors']['points']}",
                "prediccion_modelo": {"prob_local": "58%", "prob_visitante": "42%", "pick_recomendado": "Local"}
            })
        return {"data": juegos}
    except: return {"data": []}
