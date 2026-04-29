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
def get_pitcher_stats(pitcher_name):
    if not pitcher_name or pitcher_name == "Por anunciar":
        return {"era": "-.--", "wl": "0-0", "id": None}
    try:
        player_lookup = statsapi.lookup_player(pitcher_name)
        if player_lookup:
            p_id = player_lookup[0]['id']
            stats = statsapi.player_stat_data(p_id, group="pitching", type="season")
            if stats and 'stats' in stats and len(stats['stats']) > 0:
                s = stats['stats'][0]['stats']
                return {"id": p_id, "era": str(s.get("era", "0.00")), "wl": f"{s.get('wins', 0)}-{s.get('losses', 0)}"}
    except: pass
    return {"era": "-.--", "wl": "0-0", "id": None}

# --- ENDPOINTS ---

@app.get("/api/mlb/hoy")
def obtener_mlb(date: Optional[str] = None):
    target_date = date if date else datetime.now().strftime("%Y-%m-%d")
    date_formatted = datetime.strptime(target_date, "%Y-%m-%d").strftime("%m/%d/%Y")
    try:
        juegos_raw = statsapi.schedule(date=date_formatted)
        res = []
        for j in juegos_raw:
            id_vis, id_loc = j.get("away_id"), j.get("home_id")
            p_vis_name = j.get("away_probable_pitcher", "Por anunciar")
            p_loc_name = j.get("home_probable_pitcher", "Por anunciar")
            
            res.append({
                "id": j.get("game_id"),
                "deporte": "mlb",
                "estado": j.get("status"),
                "estado_vivo": f"{j.get('inning_state', '')} {j.get('current_inning', '')}".strip() or j.get("detailed_state"),
                "hora_utc": j.get("game_date"),
                "equipos": {
                    "vis": {"n": j.get("away_name"), "l": f"https://www.mlbstatic.com/team-logos/{id_vis}.svg", "form": ["W","L","W","W","L"]}, # Mock Form
                    "loc": {"n": j.get("home_name"), "l": f"https://www.mlbstatic.com/team-logos/{id_loc}.svg", "form": ["L","W","L","W","W"]}
                },
                "pitchers": {
                    "vis": get_pitcher_stats(p_vis_name) if p_vis_name != "Por anunciar" else {"n": "TBD", "era": "-.--", "wl": "0-0"},
                    "loc": get_pitcher_stats(p_loc_name) if p_loc_name != "Por anunciar" else {"n": "TBD", "era": "-.--", "wl": "0-0"}
                },
                "score": {"vis": j.get("away_score", ""), "loc": j.get("home_score", "")},
                "prediccion_modelo": {"prob_visitante": "51.2%", "prob_local": "48.8%", "pick_recomendado": "Visitante"}
            })
            # Limpieza rápida de nombres de pitcher
            res[-1]["pitchers"]["vis"]["n"] = p_vis_name
            res[-1]["pitchers"]["loc"]["n"] = p_loc_name
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
                juegos.append({
                    "id": f["fixture"]["id"],
                    "deporte": "futbol",
                    "estado_vivo": str(f["fixture"]["status"]["elapsed"]) + "'" if f["fixture"]["status"]["elapsed"] else f["fixture"]["status"]["short"],
                    "hora_utc": f["fixture"]["date"],
                    "equipos": {
                        "loc": {"n": f["teams"]["home"]["name"], "l": f["teams"]["home"]["logo"], "form": ["W","D","W","L","W"]},
                        "vis": {"n": f["teams"]["away"]["name"], "l": f["teams"]["away"]["logo"], "form": ["L","L","D","W","L"]}
                    },
                    "score": {"loc": f["goals"]["home"], "vis": f["goals"]["away"]},
                    "prediccion_modelo": {"prob_local": "45%", "prob_visitante": "30%", "pick_recomendado": "Local"}
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
            juegos.append({
                "id": g["id"],
                "deporte": "nba",
                "estado_vivo": f"{g['status']['short']} {g['status'].get('clock','')}",
                "hora_utc": g["date"]["start"],
                "equipos": {
                    "loc": {"n": g["teams"]["home"]["name"], "l": g["teams"]["home"]["logo"], "form": ["W","W","L","W","L"]},
                    "vis": {"n": g["teams"]["visitors"]["name"], "l": g["teams"]["visitors"]["logo"], "form": ["L","W","W","L","W"]}
                },
                "score": {"loc": g["scores"]["home"]["points"], "vis": g["scores"]["visitors"]["points"]},
                "prediccion_modelo": {"prob_local": "60%", "prob_visitante": "40%", "pick_recomendado": "Local"}
            })
        return {"data": juegos}
    except: return {"data": []}
