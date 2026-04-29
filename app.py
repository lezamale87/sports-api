from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import statsapi
import requests
from datetime import datetime
from typing import Optional

app = FastAPI(title="Especialista BET - Central Multi-Sport")

# Configuración de CORS para permitir conexión con Bolt/Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_KEY_SPORTS = "d32efe9d296f4f8268b3a83c024a312c"

# --- UTILIDADES MLB ---
def get_pitcher_stats(pitcher_name):
    """Busca ERA y Record W-L del pitcher abridor"""
    if not pitcher_name or pitcher_name == "Por anunciar":
        return {"era": "-.--", "wl": "0-0", "id": None}
    try:
        player_lookup = statsapi.lookup_player(pitcher_name)
        if not player_lookup: 
            return {"era": "-.--", "wl": "0-0", "id": None}
        
        p_id = player_lookup[0]['id']
        stats = statsapi.player_stat_data(p_id, group="pitching", type="season")
        
        if stats and 'stats' in stats and len(stats['stats']) > 0:
            s = stats['stats'][0]['stats']
            return {
                "id": p_id,
                "era": str(s.get("era", "0.00")),
                "wl": f"{s.get('wins', 0)}-{s.get('losses', 0)}"
            }
    except: 
        pass
    return {"era": "-.--", "wl": "0-0", "id": None}

# --- ENDPOINTS ---

@app.get("/api/mlb/hoy")
def obtener_mlb(date: Optional[str] = None):
    target_date = date if date else datetime.now().strftime("%Y-%m-%d")
    # statsapi requiere formato mm/dd/yyyy
    date_formatted = datetime.strptime(target_date, "%Y-%m-%d").strftime("%m/%d/%Y")
    
    try:
        juegos_raw = statsapi.schedule(date=date_formatted)
        res = []
        for j in juegos_raw:
            id_vis, id_loc = j.get("away_id"), j.get("home_id")
            
            # Predicción simple basada en ID (Power Rating)
            p_vis = round(44 + (id_vis % 12), 1)
            p_loc = round(100 - p_vis, 1)
            
            # Stats de Pitchers para el Pop-up
            p_vis_name = j.get("away_probable_pitcher", "Por anunciar")
            p_loc_name = j.get("home_probable_pitcher", "Por anunciar")
            
            stats_v = get_pitcher_stats(p_vis_name)
            stats_l = get_pitcher_stats(p_loc_name)
            
            # Estado en vivo (Inning)
            inning = f"{j.get('inning_state', '')} {j.get('current_inning', '')}".strip()
            estado_detalle = j.get("detailed_state", j.get("status"))

            res.append({
                "id": j.get("game_id"),
                "deporte": "mlb",
                "estado": j.get("status"),
                "estado_vivo": inning if inning else estado_detalle,
                "hora_utc": j.get("game_date"),
                "equipos": {
                    "vis": {"n": j.get("away_name"), "l": f"https://www.mlbstatic.com/team-logos/{id_vis}.svg"},
                    "loc": {"n": j.get("home_name"), "l": f"https://www.mlbstatic.com/team-logos/{id_loc}.svg"}
                },
                "pitchers": {
                    "vis": {"n": p_vis_name, "id": stats_v["id"], "era": stats_v["era"], "wl": stats_v["wl"]},
                    "loc": {"n": p_loc_name, "id": stats_l["id"], "era": stats_l["era"], "wl": stats_l["wl"]}
                },
                "score": {
                    "vis": j.get("away_score", ""),
                    "loc": j.get("home_score", "")
                },
                "prediccion_modelo": {
                    "prob_visitante": f"{p_vis}%",
                    "prob_local": f"{p_loc}%",
                    "pick_recomendado": "Local" if p_loc > p_vis else "Visitante"
                }
            })
        return {"data": res}
    except:
        return {"data": []}

@app.get("/api/futbol/hoy")
def obtener_futbol(date: Optional[str] = None):
    target_date = date if date else datetime.now().strftime("%Y-%m-%d")
    url = "https://v3.football.api-sports.io/fixtures"
    headers = {"x-rapidapi-key": API_KEY_SPORTS, "x-rapidapi-host": "v3.football.api-sports.io"}
    
    try:
        response = requests.get(url, headers=headers, params={"date": target_date})
        data = response.json().get("response", [])
        juegos = []
        for f in data:
            if f["league"]["id"] in [2, 39, 140, 135, 78]:
                p_loc = round(38 + (f["teams"]["home"]["id"] % 22), 1)
                p_vis = round(100 - p_loc - 24, 1)
                minuto = str(f["fixture"]["status"]["elapsed"]) + "'" if f["fixture"]["status"]["elapsed"] else f["fixture"]["status"]["short"]
                
                juegos.append({
                    "id": f["fixture"]["id"],
                    "deporte": "futbol",
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
                    "prediccion_modelo": {
                        "prob_local": f"{p_loc}%",
                        "prob_visitante": f"{p_vis}%",
                        "pick_recomendado": "Local" if p_loc > p_vis else "Visitante"
                    }
                })
        return {"data": juegos}
    except:
        return {"data": []}

@app.get("/api/nba/hoy")
def obtener_nba(date: Optional[str] = None):
    target_date = date if date else datetime.now().strftime("%Y-%m-%d")
    url = "https://v2.nba.api-sports.io/games"
    headers = {"x-rapidapi-key": API_KEY_SPORTS, "x-rapidapi-host": "v2.nba.api-sports.io"}
    
    try:
        response = requests.get(url, headers=headers, params={"date": target_date})
        data = response.json().get("response", [])
        juegos = []
        for g in data:
            p_loc = round(45 + (g["teams"]["home"]["id"] % 18), 1)
            p_vis = round(100 - p_loc, 1)
            cuarto = g["status"]["short"]
            reloj = g["status"].get("clock", "")
            vivo = f"{cuarto} | {reloj}" if reloj else cuarto
            
            juegos.append({
                "id": g["id"],
                "deporte": "nba",
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
                "prediccion_modelo": {
                    "prob_local": f"{p_loc}%",
                    "prob_visitante": f"{p_vis}%",
                    "pick_recomendado": "Local" if p_loc > p_vis else "Visitante"
                }
            })
        return {"data": juegos}
    except:
        return {"data": []}

@app.get("/")
def home():
    return {"status": "Online", "msg": "Especialista BET Central Ready"}
