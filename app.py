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

# MLB (Sabermetría Completa Restaurada)
def obtener_stats_pitcher(pitcher_id):
    if not pitcher_id: return {"era": "N/A", "whip": "N/A", "k": "N/A"}
    try:
        stats = statsapi.player_stat_data(pitcher_id, group="pitching", type="season")
        if stats and 'stats' in stats and len(stats['stats']) > 0:
            s = stats['stats'][0]['stats']
            return {"era": s.get("era", "0.00"), "whip": s.get("whip", "0.00"), "k": s.get("strikeOuts", 0)}
    except: pass
    return {"era": "N/A", "whip": "N/A", "k": "N/A"}

def calcular_power_rating_mlb(era, whip, k):
    if era == "N/A" or whip == "N/A": return 50.0
    try:
        score = 50.0 + (4.00 - float(era)) * 10 + (1.30 - float(whip)) * 25 + (int(k) * 0.2)
        return max(10.0, min(90.0, round(score, 2)))
    except: return 50.0

def calcular_probabilidades_mlb(score_vis, score_loc):
    score_loc_adj = score_loc + 3.0 # Ventaja local
    total = score_vis + score_loc_adj
    prob_vis = round((score_vis / total) * 100, 2)
    prob_loc = round((score_loc_adj / total) * 100, 2)
    pick = "Local" if prob_loc > prob_vis else "Visitante"
    return prob_vis, prob_loc, pick

# FUTBOL (Modelo 3-Way: 1X2)
def calcular_prediccion_futbol(id_local, id_visitante):
    rating_loc = 70.0 + (id_local % 25) + 5.0 # +5 por ventaja de localía
    rating_vis = 70.0 + (id_visitante % 25)
    
    total = rating_loc + rating_vis
    prob_empate = 25.0
    margen_restante = 100.0 - prob_empate
    
    prob_loc = round((rating_loc / total) * margen_restante, 2)
    prob_vis = round((rating_vis / total) * margen_restante, 2)
    
    if prob_loc > prob_vis and prob_loc > 40:
        pick = "Local"
    elif prob_vis > prob_loc and prob_vis > 40:
        pick = "Visitante"
    else:
        pick = "Empate / Doble Oportunidad"
        
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
            id_vis = j.get("away_id", 1)
            id_loc = j.get("home_id", 1)
            
            # Buscando los pitchers reales
            nombre_vis = j.get("away_probable_pitcher", "")
            nombre_loc = j.get("home_probable_pitcher", "")
            
            p_vis_id, p_loc_id = None, None
            if nombre_vis:
                busqueda = statsapi.lookup_player(nombre_vis)
                if busqueda: p_vis_id = busqueda[0].get('id')
            if nombre_loc:
                busqueda = statsapi.lookup_player(nombre_loc)
                if busqueda: p_loc_id = busqueda[0].get('id')
            
            stats_vis = obtener_stats_pitcher(p_vis_id)
            stats_loc = obtener_stats_pitcher(p_loc_id)
            
            r_vis = calcular_power_rating_mlb(stats_vis["era"], stats_vis["whip"], stats_vis["k"])
            r_loc = calcular_power_rating_mlb(stats_loc["era"], stats_loc["whip"], stats_loc["k"])
            p_vis, p_loc, pick = calcular_probabilidades_mlb(r_vis, r_loc)

            res.append({
                "id": j.get("game_id"),
                "estado": j.get("status"),
                "equipos": {
                    "vis": {"n": j.get("away_name"), "l": f"https://www.mlbstatic.com/team-logos/{id_vis}.svg"},
                    "loc": {"n": j.get("home_name"), "l": f"https://www.mlbstatic.com/team-logos/{id_loc}.svg"}
                },
                "marcador": None,
                "prediccion_modelo": {
                    "prob_visitante": f"{p_vis}%",
                    "prob_local": f"{p_loc}%",
                    "pick_recomendado": pick
                }
            })
        return {"total": len(res), "data": res}
    except Exception as e: return {"error": str(e)}

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
