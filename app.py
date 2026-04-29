from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import statsapi
import requests
from datetime import datetime, timedelta
from typing import Optional

app = FastAPI(title="Especialista BET")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# RECOMENDACIÓN: Si sigue sin cargar, intenta crear una cuenta nueva en API-Sports para probar otra Key
API_KEY_SPORTS = "d32efe9d296f4f8268b3a83c024a312c"

def prob_to_ml(prob_str):
    try:
        p = float(prob_str.replace('%',''))
        return f"-{int((p/(100-p))*100)}" if p >= 50 else f"+{int(((100-p)/p)*100)}"
    except: return "+100"

def get_et_date_str(utc_str, default_date):
    try:
        clean_str = str(utc_str)[:19].replace("T", " ")
        dt = datetime.strptime(clean_str, "%Y-%m-%d %H:%M:%S")
        return (dt - timedelta(hours=4)).strftime("%Y-%m-%d")
    except: return default_date

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
            top_bot = str(j.get("inning_state", "")).lower()
            inning_num = str(j.get("current_inning", ""))
            
            if "top" in top_bot or top_bot == "t": estado_v = f"▲ {inning_num}"
            elif "bot" in top_bot or top_bot == "b": estado_v = f"▼ {inning_num}"
            else: estado_v = j.get("detailed_state", "")

            res.append({
                "id": j.get("game_id"), "deporte": "mlb", "estado": j.get("status"),
                "estado_vivo": estado_v.strip(), "hora_utc": j.get("game_date"),
                "equipos": {
                    "vis": {"n": j.get("away_name"), "l": f"https://www.mlbstatic.com/team-logos/{id_v}.svg", "form": ["W","L","W","W","L"]},
                    "loc": {"n": j.get("home_name"), "l": f"https://www.mlbstatic.com/team-logos/{id_l}.svg", "form": ["L","W","L","W","W"]}
                },
                "score": {"vis": j.get("away_score"), "loc": j.get("home_score")},
                "betting": {"ml_v": prob_to_ml(p_v), "ml_l": prob_to_ml(p_l), "spread": "-1.5", "total": "8.5"},
                "prediccion_modelo": {"prob_visitante": p_v, "prob_local": p_l, "pick_recomendado": "Local" if float(p_l.replace('%','')) > 50 else "Visitante"}
            })
        return {"data": res}
    except: return {"data": []}

@app.get("/api/futbol/hoy")
def obtener_futbol(date: Optional[str] = None):
    target_date = date if date else datetime.now().strftime("%Y-%m-%d")
    url = "https://v3.football.api-sports.io/fixtures"
    headers = {"x-rapidapi-key": API_KEY_SPORTS, "x-rapidapi-host": "v3.football.api-sports.io"}
    try:
        # Petición simple con timeout para no bloquear el servidor
        response = requests.get(url, headers=headers, params={"date": target_date}, timeout=5)
        raw_data = response.json()
        data = raw_data.get("response", [])
        juegos = []
        ligas_top = [1, 2, 3, 9, 13, 17, 39, 45, 48, 61, 66, 78, 81, 94, 135, 137, 140, 143, 253, 529, 848]
        
        for f in data:
            if f["league"]["id"] in ligas_top:
                juegos.append({
                    "id": f["fixture"]["id"], "deporte": "futbol", 
                    "liga": f["league"]["name"], "liga_logo": f["league"]["logo"],
                    "estado": f["fixture"]["status"]["short"],
                    "estado_vivo": str(f["fixture"]["status"]["elapsed"]) + "'" if f["fixture"]["status"]["elapsed"] else f["fixture"]["status"]["short"],
                    "hora_utc": f["fixture"]["date"],
                    "equipos": {
                        "loc": {"n": f["teams"]["home"]["name"], "l": f["teams"]["home"]["logo"], "form": ["W","D","W","L","W"]},
                        "vis": {"n": f["teams"]["away"]["name"], "l": f["teams"]["away"]["logo"], "form": ["L","L","D","W","L"]}
                    },
                    "score": {"loc": f["goals"]["home"], "vis": f["goals"]["away"]},
                    "betting": {"ml_v": "+210", "ml_l": "-115", "spread": "0.0", "total": "2.5"},
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
        response = requests.get(url, headers=headers, params={"date": target_date}, timeout=5)
        data = response.json().get("response", [])
        juegos = []
        for g in data:
            status_short = str(g["status"]["short"]).strip()
            reloj = str(g["status"].get("clock", "")).replace("None", "").strip()
            vivo = "FINAL" if status_short in ["FT", "AOT", "Final"] else f"{status_short} {reloj}".strip()

            juegos.append({
                "id": g["id"], "deporte": "nba", "estado": status_short,
                "estado_vivo": vivo, "hora_utc": g["date"]["start"],
                "equipos": {
                    "loc": {"n": g["teams"]["home"]["name"], "l": g["teams"]["home"]["logo"], "form": ["W","W","L","W","L"]},
                    "vis": {"n": g["teams"]["visitors"]["name"], "l": g["teams"]["visitors"]["logo"], "form": ["L","W","W","L","W"]}
                },
                "score": {"loc": g["scores"]["home"]["points"], "vis": g["scores"]["visitors"]["points"]},
                "betting": {"ml_v": "+150", "ml_l": "-180", "spread": "-4.5", "total": "224.5"},
                "prediccion_modelo": {"prob_local": "60%", "prob_visitante": "40%", "pick_recomendado": "Local"}
            })
        return {"data": juegos}
    except: return {"data": []}
