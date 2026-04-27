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
    """Busca ERA, WHIP y K's de un pitcher por su ID con manejo de errores"""
    if not pitcher_id:
        return {"era": "N/A", "whip": "N/A", "k": "N/A"}
    try:
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
        juegos_raw = statsapi.schedule(date=hoy)
        juegos_formateados = []

        for juego in juegos_raw:
            game_id = juego.get("game_id")
            
            # Valores por defecto
            lineup_visitante = []
            lineup_local = []
            p_vis_id = None
            p_loc_id = None

            # 1. Intentamos sacar lineups del boxscore
            try:
                detalles = statsapi.boxscore_data(game_id)
                for p in detalles.get('awayBatters', []):
                    if isinstance(p, dict) and p.get('person') and p.get('battingOrder'):
                        lineup_visitante.append(p['person'].get('fullName'))
                        
                for p in detalles.get('homeBatters', []):
                    if isinstance(p, dict) and p.get('person') and p.get('battingOrder'):
                        lineup_local.append(p['person'].get('fullName'))
            except Exception:
                pass

            # 2. Buscamos a los pitchers por nombre en la base de datos
            nombre_vis = juego.get("away_probable_pitcher", "")
            nombre_loc = juego.get("home_probable_pitcher", "")

            if nombre_vis:
                busqueda_vis = statsapi.lookup_player(nombre_vis)
                if busqueda_vis:
                    p_vis_id = busqueda_vis[0].get('id')

            if nombre_loc:
                busqueda_loc = statsapi.lookup_player(nombre_loc)
                if busqueda_loc:
                    p_loc_id = busqueda_loc[0].get('id')

            # 3. Obtener estadísticas reales de la temporada
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
                    "nombre": nombre_vis if nombre_vis else "TBD",
                    "era": stats_vis["era"],
                    "whip": stats_vis["whip"],
                    "k_temporada": stats_vis["k"]
                },
                "pitcher_local": {
                    "nombre": nombre_loc if nombre_loc else "TBD",
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
        return {"error_general": str(e)}

@app.get("/")
def home():
    return {"mensaje": "API MLB con Stats y Lineups Activa"}
