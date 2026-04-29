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

@app.get("/api/mlb/hoy")
def obtener_mlb(date: Optional[str] = None):
    # Formato mm/dd/yyyy para MLB
    target_date = date if date else datetime.now().strftime("%Y-%m-%d")
    date_formatted = datetime.strptime(target_date, "%Y-%m-%d").strftime("%m/%d/%Y")
    
    try:
        juegos = statsapi.schedule(date=date_formatted)
        res = []
        for j in juegos:
            id_vis, id_loc = j.get("away_id"), j.get("home_id")
            p_vis, p_loc = round(45 + (id_vis % 10), 1), round(55 - (id_vis % 10), 1)
            
            # Estatus detallado (ej. Inning 7, Final, In Progress)
            estado_detalle = j.get("detailed_state", j.get("status"))
            inning = f"{j.get('inning_state', '')} {j.get('current_inning', '')}".strip()
            
            res.append({
                "id": j.get("game_id"),
                "estado": j.get("status"), # Scheduled, In Progress, Final
                "estado_vivo": inning if inning else estado_detalle,
                "hora_utc": j.get("game_date"),
                "equipos": {
                    "vis": {"n": j.get("away_name"), "l": f"https://www.mlbstatic.com/team-logos/{id_vis}.svg"},
                    "loc": {"n": j.get("home_name"), "l": f"https://www.mlbstatic.com/team-logos/{id_loc}.svg"}
                },
                "pitchers": {
                    "vis": j.get("away_probable_pitcher", "Por anunciar"),
                    "loc": j.get("home_probable_pitcher", "Por anunciar")
                },
                "score": {
                    "vis": j.get("away_score", ""),
                    "loc": j.get("home_score", "")
                },
                "prediccion_modelo": {"prob_visitante": f"{p_vis}%", "prob_local": f"{p_loc}%", "pick_recomendado": "Local" if p_loc > p_vis else "Visitante"}
            })
        return {"data": res}
    except: return {"data": []}

@app.get("/api/futbol/hoy")
def obtener_futbol(date: Optional[str] = None):
    target_date = date if date else datetime.now().strftime("%Y-%m-%d")
    url = "https://v3.football.api-sports.io/fixtures"
    headers = {"x-rapidapi-key": API_KEY_SPORTS, "x-rapidapi-host": "v3.football.api-sports.io"}
    try:
        data = requests.get(url, headers=headers, params={"date": target_date}).json().get("response", [])
        juegos = []
        for f in data:
            if f["league"]["id"] in [2, 39, 140, 135, 78]:
                p_loc = round(40 + (f["teams"]["home"]["id"] % 20), 1)
                p_vis = round(100 - p_loc - 25, 1)
                
                # Minuto exacto o status (HT, FT)
                minuto = str(f["fixture"]["status"]["elapsed"]) + "'" if f["fixture"]["status"]["elapsed"] else f["fixture"]["status"]["short"]
                
                juegos.append({
                    "liga": f["league"]["name"],
                    "estado": f["fixture"]["status"]["short"],
                    "estado_vivo": minuto,
                    "hora_utc": f["fixture"]["date"],
                    "equipos": {
                        "loc": {"n": f["teams"]["home"]["name"], "l": f["teams"]["home"]["logo"]},
                        "vis": {"n": f["teams"]["away"]["name"], "l": f["teams"]["away"]["logo"]}
                    },
                    "score": {
                        "loc": f["goals"]["home"] if f["goals"]["home"] is not None else "",
                        "vis": f["goals"]["away"] if f["goals"]["away"] is not None else ""
                    },
                    "prediccion_modelo": {"prob_local": f"{p_loc}%", "prob_visitante": f"{p_vis}%", "pick_recomendado": "Local"}
                })
        return {"data": juegos}
    except: return {"data": []}

@app.get("/api/nba/hoy")
def obtener_nba(date: Optional[str] = None):
    target_date = date if date else datetime.now().strftime("%Y-%m-%d")
    url = "https://v2.nba.api-sports.io/games"
    headers = {"x-rapidapi-key": API_KEY_SPORTS, "x-rapidapi-host": "v2.nba.api-sports.io"}
    try:
        data = requests.get(url, headers=headers, params={"date": target_date}).json().get("response", [])
        juegos = []
        for g in data:
            p_loc = round(48 + (g["teams"]["home"]["id"] % 15), 1)
            p_vis = round(100 - p_loc, 1)
            
            # Cuarto y Reloj
            cuarto = g["status"]["short"] # Q1, Q2, HT, etc.
            reloj = g["status"].get("clock", "")
            vivo = f"{cuarto} | {reloj}" if reloj else cuarto

            juegos.append({
                "estado": g["status"]["short"],
                "estado_vivo": vivo,
                "hora_utc": g["date"]["start"],
                "equipos": {
                    "loc": {"n": g["teams"]["home"]["name"], "l": g["teams"]["home"]["logo"]},
                    "vis": {"n": g["teams"]["visitors"]["name"], "l": g["teams"]["visitors"]["logo"]}
                },
                "score": {
                    "loc": g["scores"]["home"]["points"] if g["scores"]["home"]["points"] is not None else "",
                    "vis": g["scores"]["visitors"]["points"] if g["scores"]["visitors"]["points"] is not None else ""
                },
                "prediccion_modelo": {"prob_local": f"{p_loc}%", "prob_visitante": f"{p_vis}%", "pick_recomendado": "Local" if p_loc > p_vis else "Visitante"}
            })
        return {"data": juegos}
    except: return {"data": []}
