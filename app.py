from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import statsapi
import requests
from datetime import datetime
from typing import Optional

app = FastAPI(title="Especialista BET - Central")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_KEY_SPORTS = "d32efe9d296f4f8268b3a83c024a312c"

def prob_to_ml(prob_str):
    try:
        p = float(prob_str.replace('%',''))
        return f"-{int((p/(100-p))*100)}" if p >= 50 else f"+{int(((100-p)/p)*100)}"
    except: return "+100"

def get_pitcher_stats(pitcher_name):
    if not pitcher_name or pitcher_name == "Por anunciar": return {"era": "-.--", "wl": "0-0", "id": None}
    try:
        player = statsapi.lookup_player(pitcher_name)
        if player:
            p_id = player[0]['id']
            stats = statsapi.player_stat_data(p_id, group="pitching", type="season")
            if stats and 'stats' in stats and len(stats['stats']) > 0:
                s = stats['stats'][0]['stats']
                return {"id": p_id, "era": str(s.get("era", "0.00")), "wl": f"{s.get('wins', 0)}-{s.get('losses', 0)}"}
    except: pass
    return {"era": "-.--", "wl": "0-0", "id": None}

@app.get("/api/mlb/hoy")
def obtener_mlb(date: Optional[str] = None):
    target_date = date if date else datetime.now().strftime("%Y-%m-%d")
    date_formatted = datetime.strptime(target_date, "%Y-%m-%d").strftime("%m/%d/%Y")
    try:
        juegos_raw = statsapi.schedule(date=date_formatted)
        res = []
        for j in juegos_raw:
            id_v, id_l = j.get("away_id"), j.get("home_id")
            p_v, p_l = f"{round(44+(id_v%12),1)}%", f"{round(56-(id_v%12),1)}%"
            
            top_bot = j.get("inning_state", "")
            inning_num = j.get("current_inning", "")
            estado_v = f"{top_bot} {inning_num}" if top_bot and inning_num else j.get("detailed_state", "")

            lineup = [{"n": f"{i}. Bateador", "avg": f".{290-i*5}"} for i in range(1, 10)]

            res.append({
                "id": j.get("game_id"), "deporte": "mlb", "estado": j.get("status"),
                "estado_vivo": estado_v, "hora_utc": j.get("game_date"),
                "equipos": {
                    "vis": {"n": j.get("away_name"), "l": f"https://www.mlbstatic.com/team-logos/{id_v}.svg", "form": ["W","L","W","W","L"]},
                    "loc": {"n": j.get("home_name"), "l": f"https://www.mlbstatic.com/team-logos/{id_l}.svg", "form": ["L","W","L","W","W"]}
                },
                "pitchers": {
                    "vis": get_pitcher_stats(j.get("away_probable_pitcher")),
                    "loc": get_pitcher_stats(j.get("home_probable_pitcher"))
                },
                "lineups": {"vis": lineup, "loc": lineup},
                "score": {
                    "vis": j.get("away_score") if j.get("away_score") is not None else "", 
                    "loc": j.get("home_score") if j.get("home_score") is not None else ""
                },
                "betting": {"ml_v": prob_to_ml(p_v), "ml_l": prob_to_ml(p_l), "spread": "-1.5" if float(p_l.replace('%','')) > 50 else "+1.5", "total": "8.5"},
                "prediccion_modelo": {"prob_visitante": p_v, "prob_local": p_l, "pick_recomendado": "Local" if float(p_l.replace('%','')) > 50 else "Visitante"}
            })
            res[-1]["pitchers"]["vis"]["n"] = j.get("away_probable_pitcher", "TBD")
            res[-1]["pitchers"]["loc"]["n"] = j.get("home_probable_pitcher", "TBD")
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
        # Ligas ampliadas: Mundial, Champions, Europa, Conference, Premier, FA Cup, La Liga, Copa del Rey, Serie A, Coppa Italia, Bundesliga, Ligue 1, Libertadores, Sudamericana, etc.
        ligas_top = [1, 2, 3, 9, 13, 17, 39, 45, 48, 61, 66, 78, 81, 94, 135, 137, 140, 143, 529, 848]
        
        for f in data:
            if f["league"]["id"] in ligas_top:
                p_l, p_v = "45%", "30%"
                juegos.append({
                    "id": f["fixture"]["id"], "deporte": "futbol", "liga": f["league"]["name"],
                    "estado": f["fixture"]["status"]["short"],
                    "estado_vivo": str(f["fixture"]["status"]["elapsed"]) + "'" if f["fixture"]["status"]["elapsed"] else f["fixture"]["status"]["short"],
                    "hora_utc": f["fixture"]["date"],
                    "equipos": {
                        "loc": {"n": f["teams"]["home"]["name"], "l": f["teams"]["home"]["logo"], "form": ["W","D","W","L","W"]},
                        "vis": {"n": f["teams"]["away"]["name"], "l": f["teams"]["away"]["logo"], "form": ["L","L","D","W","L"]}
                    },
                    "score": {
                        "loc": f["goals"]["home"] if f["goals"]["home"] is not None else "", 
                        "vis": f["goals"]["away"] if f["goals"]["away"] is not None else ""
                    },
                    "betting": {"ml_v": "+210", "ml_l": "-115", "spread": "0.0", "total": "2.5"},
                    "prediccion_modelo": {"prob_local": p_l, "prob_visitante": p_v, "pick_recomendado": "Local"}
                })
        return {"data": juegos}
    except: return {"data": []}

@app.get("/api/nba/hoy")
def obtener_nba(date: Optional[str] = None):
    target_date = date if date else datetime.now().strftime("%Y-%m-%d")
    url = "https://v2.nba.api-sports.io/games"
    headers = {"x-rapidapi-key": API_KEY_SPORTS, "x-rapidapi-host": "v2.nba.api-sports.io"}
    try:
        # Quitamos el timezone que causaba el conflicto, usamos la fecha pura programada
        data = requests.get(url, headers=headers, params={"date": target_date}).json().get("response", [])
        juegos = []
        for g in data:
            p_l = f"{round(48+(g['teams']['home']['id']%15),1)}%"
            p_v = f"{round(100-float(p_l.replace('%','')),1)}%"
            
            cuarto = str(g["status"]["short"]).strip()
            if cuarto.isdigit(): cuarto = f"Q{cuarto}" 
            reloj = str(g["status"].get("clock", "")).replace("None", "").strip()
            vivo = f"{cuarto} {reloj}".strip()

            juegos.append({
                "id": g["id"], "deporte": "nba", "estado": g["status"]["short"],
                "estado_vivo": vivo, "hora_utc": g["date"]["start"],
                "equipos": {
                    "loc": {"n": g["teams"]["home"]["name"], "l": g["teams"]["home"]["logo"], "form": ["W","W","L","W","L"]},
                    "vis": {"n": g["teams"]["visitors"]["name"], "l": g["teams"]["visitors"]["logo"], "form": ["L","W","W","L","W"]}
                },
                "score": {
                    "loc": g["scores"]["home"]["points"] if g["scores"]["home"]["points"] is not None else "", 
                    "vis": g["scores"]["visitors"]["points"] if g["scores"]["visitors"]["points"] is not None else ""
                },
                "betting": {"ml_v": prob_to_ml(p_v), "ml_l": prob_to_ml(p_l), "spread": "-4.5" if float(p_l.replace('%','')) > 50 else "+4.5", "total": "224.5"},
                "prediccion_modelo": {"prob_local": p_l, "prob_visitante": p_v, "pick_recomendado": "Local" if float(p_l.replace('%','')) > 50 else "Visitante"}
            })
        return {"data": juegos}
    except: return {"data": []}
