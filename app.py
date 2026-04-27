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

def obtener_stats_pitcher(pitcher_id):
    """Busca ERA, WHIP y K's de un pitcher por su ID"""
    if not pitcher_id:
        return {"era": "N/A", "whip": "N/A", "k": "N/A"}
    try:
        # Buscamos las estadísticas de la temporada actual
        stats = statsapi.player_stat_data(pitcher_id, group="pitching", type="season")
        if stats and 'stats' in stats and len(stats['stats']) > 0:
            s = stats['stats'][0]['stats']
            return {
                "era": s.get("era", "0.00"),
                "whip": s.get("whip", "0.00"),
                "k": s.get("strikeOuts", 0)
            }
    except:
        pass
    return {"era": "N/A", "whip": "N/A", "k": "N/A"}

@app.get("/api/mlb/hoy")
def obtener_juegos_hoy():
    hoy = datetime.now().strftime("%m/%d/%Y")
    try:
        # 1. Obtenemos el calendario básico
        juegos_raw = statsapi.schedule(date=hoy)
        juegos_formateados = []

        for juego in juegos_raw:
            game_id = juego.get("game_id")
            
            # 2. Obtenemos detalles profundos (Boxscore) para Lineups y IDs de Pitchers
            # Esto nos permite ver si ya hay jugadores en el orden al bate
            detalles = statsapi.boxscore_data(game_id)
            
            # Lógica de Lineup
            lineup_visitante = [p['person']['fullName'] for p in detalles['awayBatters'] if p['battingOrder']]
            lineup_local = [p['person']['fullName'] for p in detalles['homeBatters'] if p['battingOrder']]

            # Lógica de Pitchers y sus Stats
            p_vis_id = detalles['awayPitchers'][0]['person']['id'] if detalles['awayPitchers'] else None
            p_loc_id = detalles['homePitchers'][0]['person']['id'] if detalles['homePitchers'] else None

            stats_vis = obtener_stats_pitcher(p_vis_id)
            stats_loc = obtener_stats_pitcher(p_loc_id)

            juegos_formateados.append({
                "id_juego": game_id,
                "estado": juego.get("status"),
                "equipos": {
                    "visitante": juego.get("away_name"),
                    "local": juego.get("home_name")
                },
                "pitcher_visitante": {
                    "nombre": juego.get("away_probable_pitcher", "TBD"),
                    "era": stats_vis["era"],
                    "whip": stats_vis["whip"],
                    "k_temporada": stats_vis["k"]
                },
                "pitcher_local": {
                    "nombre": juego.get("home_probable_pitcher", "TBD"),
                    "era": stats_loc["era"],
                    "whip": stats_loc["whip"],
                    "k_temporada": stats_loc["k"]
                },
                "lineups": {
                    "visitante": lineup_visitante if lineup_visitante else "Lineup por confirmar",
                    "local": lineup_local if lineup_local else "Lineup por confirmar"
                }
            })

        return {"deporte": "MLB", "fecha": hoy, "total_juegos": len(juegos_formateados), "data": juegos_formateados}
    except Exception as e:
        return {"error": str(e)}

@app.get("/")
def home():
    return {"mensaje": "API MLB con Stats y Lineups Activa"}
