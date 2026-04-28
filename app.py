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

API_KEY_SPORTS = "d32efe9d296f4f8268b3a83c024a312c"

# === 1. ALGORITMOS DE PREDICCIÓN ===

# MLB
def calcular_power_rating_mlb(era, whip, k):
    if era == "N/A" or whip == "N/A": return 50.0
    try:
        score = 50.0 + (4.00 - float(era)) * 10 + (1.30 - float(whip)) * 25 + (int(k) * 0.2)
        return max(10.0, min(90.0, round(score, 2)))
    except: return 50.0

# FUTBOL (Modelo 3-Way: 1X2)
def calcular_prediccion_futbol(id_local, id_visitante):
    # Generamos un Power Rating base usando el ID del equipo (MVP)
    # En el futuro, esto se conectará a tu base de datos de estadísticas
    rating_loc = 70.0 + (id_local % 25) + 5.0 # +5 por ventaja de localía
    rating_vis = 70.0 + (id_visitante % 25)
    
    total = rating_loc + rating_vis
    # Asignamos un 25% base al empate, que es el promedio histórico en ligas top
    prob_empate = 25.0
    margen_restante = 100.0 - prob_empate
    
    prob_loc = round((rating_loc / total) * margen_restante, 2)
    prob_vis = round((rating_vis / total) * margen_restante, 2)
    
    if prob_loc > prob_vis and prob_loc > 40:
        pick = "Local"
    elif prob_vis > prob_loc and prob_vis > 40:
        pick = "Visitante"
    else:
        pick = "Empate o Doble Oportunidad"
        
    return prob_loc, prob_empate, prob_vis, pick

# NBA
def calcular_prediccion_nba(id_local, id_visitante):
    rating_loc = 75.0 + (id_local % 20) + 4.0 # +4 por localía en basket
    rating_vis = 75.0 + (id_visitante % 20)
    
    total = rating_loc + rating_vis
    prob_loc = round((rating_loc / total) * 100, 2)
    prob_vis = round((rating_vis / total) * 100, 2)
    
    return prob_loc, prob_vis, "Local" if prob_loc > prob_vis else "Visitante"

# === 2. ENDPOINTS ===

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
    params = {"date": datetime.now().strftime("%Y-%m-%d")}
    headers = {"x-rapidapi-key": API_KEY_SPORTS, "x-rapidapi-host": "v3.football.api-sports.io"}
    
    try:
        response = requests.get(url, headers=headers, params=params)
        data = response.json().get("response", [])
        juegos = []
        ligas_permitidas = [2, 39, 140, 135, 78]
        
        for f in data:
            if f["league"]["id"] in ligas_permitidas:
                id_loc = f["teams"]["home"]["id"]
                id_vis = f["teams"]["away"]["id"]
                p_loc, p_emp, p_vis, pick = calcular_prediccion_futbol(id_loc, id_vis)
                
                juegos.append({
                    "liga": f["league"]["name"],
                    "estado": f["fixture"]["status"]["long"],
                    "local": {"n": f["teams"]["home"]["name"], "l": f["teams"]["home"]["logo"]},
                    "visitante": {"n": f["teams"]["away"]["name"], "l": f["teams"]["away"]["logo"]},
                    "marcador": f"{f['goals']['home']} - {f['goals']['away']}",
                    "prediccion_modelo": {
                        "prob_local": f"{p_loc}%",
                        "prob_empate": f"{p_emp}%",
                        "prob_visitante": f"{p_vis}%",
                        "pick_recomendado": pick
                    }
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
            id_loc = g["teams"]["home"]["id"]
            id_vis = g["teams"]["visitors"]["id"]
            p_loc, p_vis, pick = calcular_prediccion_nba(id_loc, id_vis)
            
            juegos.append({
                "estado": g["status"]["long"],
                "local": {"n": g["teams"]["home"]["name"], "l": g["teams"]["home"]["logo"]},
                "visitante": {"n": g["teams"]["visitors"]["name"], "l": g["teams"]["visitors"]["logo"]},
                "marcador": f"{g['scores']['home']['points']} - {g['scores']['visitors']['points']}",
                "prediccion_modelo": {
                    "prob_local": f"{p_loc}%",
                    "prob_visitante": f"{p_vis}%",
                    "pick_recomendado": pick
                }
            })
        return {"total": len(juegos), "data": juegos}
    except: return {"error": "Error NBA"}

@app.get("/")
def home():
    return {"status": "Online", "msg": "Especialista BET Central Ready"}
