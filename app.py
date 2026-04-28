from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import statsapi
from datetime import datetime

app = FastAPI(title="Sports BET API - Pro")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- UTILIDADES ---
def obtener_logo_mlb(team_id):
    return f"https://www.mlbstatic.com/team-logos/{team_id}.svg"

def calcular_power_rating(era, whip, k):
    if era == "N/A" or whip == "N/A": return 50.0
    try:
        era_f, whip_f = float(era), float(whip)
        k_i = int(k) if k != "N/A" else 0
        score = 50.0 + (4.00 - era_f) * 10 + (1.30 - whip_f) * 25 + (k_i * 0.2)
        return max(10.0, min(90.0, round(score, 2)))
    except: return 50.0

def calcular_probabilidades(score_vis, score_loc):
    score_loc_adj = score_loc + 3.0 
    total = score_vis + score_loc_adj
    return round((score_vis / total) * 100, 2), round((score_loc_adj / total) * 100, 2)

def obtener_stats_pitcher(pitcher_id):
    if not pitcher_id: return {"era": "N/A", "whip": "N/A", "k": "N/A"}
    try:
        stats = statsapi.player_stat_data(pitcher_id, group="pitching", type="season")
        if stats and 'stats' in stats and len(stats['stats']) > 0:
            s = stats['stats'][0]['stats']
            return {"era": s.get("era", "0.00"), "whip": s.get("whip", "0.00"), "k": s.get("strikeOuts", 0)}
    except: pass
    return {"era": "N/A", "whip": "N/A", "k": "N/A"}

# --- ENDPOINTS ---

@app.get("/api/mlb/hoy")
def obtener_juegos_hoy():
    hoy = datetime.now().strftime("%m/%d/%Y")
    try:
        juegos_raw = statsapi.schedule(date=hoy)
        juegos_formateados = []

        for juego in juegos_raw:
            game_id = juego.get("game_id")
            # IDs de equipos para logos
            id_vis = juego.get("away_id")
            id_loc = juego.get("home_id")
            
            p_vis_id, p_loc_id = None, None
            nombre_vis = juego.get("away_probable_pitcher", "")
            nombre_loc = juego.get("home_probable_pitcher", "")

            if nombre_vis:
                res = statsapi.lookup_player(nombre_vis)
                if res: p_vis_id = res[0].get('id')
            if nombre_loc:
                res = statsapi.lookup_player(nombre_loc)
                if res: p_loc_id = res[0].get('id')

            stats_vis = obtener_stats_pitcher(p_vis_id)
            stats_loc = obtener_stats_pitcher(p_loc_id)
            
            r_vis = calcular_power_rating(stats_vis["era"], stats_vis["whip"], stats_vis["k"])
            r_loc = calcular_power_rating(stats_loc["era"], stats_loc["whip"], stats_loc["k"])
            p_vis, p_loc = calcular_probabilidades(r_vis, r_loc)

            juegos_formateados.append({
                "id_juego": game_id,
                "equipos": {
                    "visitante": {"nombre": juego.get("away_name"), "logo": obtener_logo_mlb(id_vis)},
                    "local": {"nombre": juego.get("home_name"), "logo": obtener_logo_mlb(id_loc)}
                },
                "prediccion": {"prob_vis": f"{p_vis}%", "prob_loc": f"{p_loc}%", "pick": "Visitante" if p_vis > p_loc else "Local"},
                "pitchers": {
                    "vis": {"nombre": nombre_vis or "TBD", "era": stats_vis["era"]},
                    "loc": {"nombre": nombre_loc or "TBD", "era": stats_loc["era"]}
                }
            })
        return {"data": juegos_formateados}
    except Exception as e: return {"error": str(e)}

@app.get("/api/futbol/hoy")
def obtener_futbol_hoy():
    # Aquí simulamos la estructura que vendrá de la API de fútbol
    # para que tu dashboard pueda ir trabajando la UI
    return {
        "deporte": "Futbol",
        "ligas": [
            {
                "nombre": "UEFA Champions League",
                "juegos": [
                    {
                        "equipo_local": "Real Madrid",
                        "logo_local": "https://media.api-sports.io/football/teams/541.png",
                        "equipo_visitante": "Man. City",
                        "logo_visitante": "https://media.api-sports.io/football/teams/50.png",
                        "probabilidades": {"1": "38%", "X": "25%", "2": "37%"},
                        "recomendacion": "Gana Local o Empate"
                    }
                ]
            }
        ]
    }

@app.get("/")
def home(): return {"status": "Online", "sports": ["MLB", "Fútbol"]}
