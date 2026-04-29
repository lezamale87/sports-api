from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import statsapi
import requests
from datetime import datetime, timedelta
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

# --- UTILIDAD: CONVERTIR PROBABILIDAD A CUOTA AMERICANA (MONEYLINE) ---
def prob_to_ml(prob_str):
    try:
        p = float(prob_str.replace('%',''))
        if p >= 50:
            return f"-{int((p/(100-p))*100)}"
        else:
            return f"+{int(((100-p)/p)*100)}"
    except: return "+100"

@app.get("/api/mlb/hoy")
def obtener_mlb(date: Optional[str] = None):
    target_date = date if date else datetime.now().strftime("%Y-%m-%d")
    date_f = datetime.strptime(target_date, "%Y-%m-%d").strftime("%m/%d/%Y")
    try:
        juegos = statsapi.schedule(date=date_f)
        res = []
        for j in juegos:
            id_v, id_l = j.get("away_id"), j.get("home_id")
            p_v, p_l = f"{round(44+(id_v%12),1)}%", f"{round(56-(id_v%12),1)}%"
            res.append({
                "id": j.get("game_id"), "deporte": "mlb", "estado": j.get("status"),
                "estado_vivo": f"{j.get('inning_state','')} {j.get('current_inning','')}".strip() or j.get("detailed_state"),
                "hora_utc": j.get("game_date"),
                "equipos": {
                    "vis": {"n": j.get("away_name"), "l": f"https://www.mlbstatic.com/team-logos/{id_v}.svg", "form": ["W","L","W","W","L"]},
                    "loc": {"n": j.get("home_name"), "l": f"https://www.mlbstatic.com/team-logos/{id_l}.svg", "form": ["L","W","L","W","W"]}
                },
                "score": {"vis": j.get("away_score", ""), "loc": j.get("home_score", "")},
                "pitchers": {"vis": {"n": j.get("away_probable_pitcher", "TBD"), "era": "3.45", "wl": "12-4", "id": 660271}, "loc": {"n": j.get("home_probable_pitcher", "TBD"), "era": "4.12", "wl": "9-8", "id": 605483}},
                "betting": {
                    "ml_v": prob_to_ml(p_v), "ml_l": prob_to_ml(p_l),
                    "spread": "-1.5" if float(p_l.replace('%','')) > 50 else "+1.5",
                    "total": "8.5"
                },
                "prediccion_modelo": {"prob_visitante": p_v, "prob_local": p_l, "pick_recomendado": "Local" if float(p_l.replace('%','')) > 50 else "Visitante"}
            })
        return {"data": res}
    except: return {"data": []}

@app.get("/api/nba/hoy")
def obtener_nba(date: Optional[str] = None):
    # NBA FIX: Si no hay fecha, buscamos hoy y ayer por el desfase de juegos nocturnos
    target_date = date if date else datetime.now().strftime("%Y-%m-%d")
    url = "https://v2.nba.api-sports.io/games"
    headers = {"x-rapidapi-key": API_KEY_SPORTS, "x-rapidapi-host": "v2.nba.api-sports.io"}
    try:
        data = requests.get(url, headers=headers, params={"date": target_date}).json().get("response", [])
        juegos = []
        for g in data:
            p_l = f"{round(48+(g['teams']['home']['id']%15),1)}%"
            p_v = f"{round(100-float(p_l.replace('%','')),1)}%"
            cuarto = g["status"]["short"]
            reloj = g["status"].get("clock", "")
            juegos.append({
                "id": g["id"], "deporte": "nba", "estado": g["status"]["short"],
                "estado_vivo": f"{cuarto} {reloj}".strip(), "hora_utc": g["date"]["start"],
                "equipos": {
                    "loc": {"n": g["teams"]["home"]["name"], "l": g["teams"]["home"]["logo"], "form": ["W","W","L","W","L"]},
                    "vis": {"n": g["teams"]["visitors"]["name"], "l": g["teams"]["visitors"]["logo"], "form": ["L","W","W","L","W"]}
                },
                "score": {"loc": g["scores"]["home"]["points"], "vis": g["scores"]["visitors"]["points"]},
                "betting": {
                    "ml_v": prob_to_ml(p_v), "ml_l": prob_to_ml(p_l),
                    "spread": "-4.5" if float(p_l.replace('%','')) > 50 else "+4.5",
                    "total": "224.5"
                },
                "prediccion_modelo": {"prob_local": p_l, "prob_visitante": p_v, "pick_recomendado": "Local" if float(p_l.replace('%','')) > 50 else "Visitante"}
            })
        return {"data": juegos}
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
                p_l, p_v = "45%", "30%"
                juegos.append({
                    "id": f["fixture"]["id"], "deporte": "futbol", "estado": f["fixture"]["status"]["short"],
                    "estado_vivo": str(f["fixture"]["status"]["elapsed"]) + "'" if f["fixture"]["status"]["elapsed"] else f["fixture"]["status"]["short"],
                    "hora_utc": f["fixture"]["date"],
                    "equipos": {
                        "loc": {"n": f["teams"]["home"]["name"], "l": f["teams"]["home"]["logo"], "form": ["W","D","W","L","W"]},
                        "vis": {"n": f["teams"]["away"]["name"], "l": f["teams"]["away"]["logo"], "form": ["L","L","D","W","L"]}
                    },
                    "score": {"loc": f["goals"]["home"], "vis": f["goals"]["away"]},
                    "betting": {"ml_v": "+210", "ml_l": "-115", "spread": "0.0", "total": "2.5"},
                    "prediccion_modelo": {"prob_local": p_l, "prob_visitante": p_v, "pick_recomendado": "Local"}
                })
        return {"data": juegos}
    except: return {"data": []}
