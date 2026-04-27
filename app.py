¡Excelente decisión! Las interfaces bonitas no sirven de nada si los datos que muestran no son precisos. Entremos al terreno del Machine Learning y la Sabermetría.

Para crear nuestro MVP (Producto Mínimo Viable) del algoritmo, vamos a construir una función matemática que asigne una calificación del 1 al 100 a cada lanzador basándose en sus métricas, castigando el descontrol (alto WHIP) y premiando la efectividad (bajo ERA). Luego, enfrentaremos esas dos calificaciones para sacar el Win Probability (Probabilidad de Victoria), agregando un pequeño bono por la ventaja de jugar en casa (Home Field Advantage).

🧠 El Algoritmo en Python
Abre tu archivo app.py y vamos a inyectar las funciones matemáticas. Copia y reemplaza todo tu código con esta nueva versión:

Python
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

# === 1. NUEVAS FUNCIONES ALGORÍTMICAS ===

def calcular_power_rating(era, whip, k):
    """Calcula un puntaje de 10 a 90 basado en métricas sabermétricas"""
    if era == "N/A" or whip == "N/A":
        return 50.0  # Puntaje promedio si no hay datos

    try:
        era_f = float(era)
        whip_f = float(whip)
        k_i = int(k) if k != "N/A" else 0
        
        # Fórmula: Base 50 + Puntos por ERA menor a 4.00 + Puntos por WHIP menor a 1.30 + Bono de K's
        score = 50.0
        score += (4.00 - era_f) * 10
        score += (1.30 - whip_f) * 25
        score += (k_i * 0.2)
        
        # Limitamos el puntaje entre 10 y 90 para que sea realista
        return max(10.0, min(90.0, round(score, 2)))
    except:
        return 50.0

def calcular_probabilidades(score_vis, score_loc):
    """Calcula el % de victoria enfrentando los ratings y dando ventaja al local"""
    # Ventaja de localía estándar en MLB (+3 puntos al rating)
    score_loc_adj = score_loc + 3.0 
    
    total = score_vis + score_loc_adj
    prob_vis = (score_vis / total) * 100
    prob_loc = (score_loc_adj / total) * 100
    
    return round(prob_vis, 2), round(prob_loc, 2)

# === 2. FUNCIONES DE EXTRACCIÓN ===

def obtener_stats_pitcher(pitcher_id):
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
            lineup_visitante, lineup_local = [], []
            p_vis_id, p_loc_id = None, None

            try:
                detalles = statsapi.boxscore_data(game_id)
                for p in detalles.get('awayBatters', []):
                    if isinstance(p, dict) and p.get('person') and p.get('battingOrder'):
                        lineup_visitante.append(p['person'].get('fullName'))
                for p in detalles.get('homeBatters', []):
                    if isinstance(p, dict) and p.get('person') and p.get('battingOrder'):
                        lineup_local.append(p['person'].get('fullName'))
            except: pass

            nombre_vis = juego.get("away_probable_pitcher", "")
            nombre_loc = juego.get("home_probable_pitcher", "")

            if nombre_vis:
                busqueda_vis = statsapi.lookup_player(nombre_vis)
                if busqueda_vis: p_vis_id = busqueda_vis[0].get('id')

            if nombre_loc:
                busqueda_loc = statsapi.lookup_player(nombre_loc)
                if busqueda_loc: p_loc_id = busqueda_loc[0].get('id')

            stats_vis = obtener_stats_pitcher(p_vis_id)
            stats_loc = obtener_stats_pitcher(p_loc_id)

            # === 3. INYECCIÓN DEL ALGORITMO ===
            rating_vis = calcular_power_rating(stats_vis["era"], stats_vis["whip"], stats_vis["k"])
            rating_loc = calcular_power_rating(stats_loc["era"], stats_loc["whip"], stats_loc["k"])
            prob_vis, prob_loc = calcular_probabilidades(rating_vis, rating_loc)

            # Determinamos el Pick Recomendado
            pick_recomendado = "Visitante" if prob_vis > prob_loc else "Local"
            confianza = "Alta" if max(prob_vis, prob_loc) >= 60.0 else "Media"

            juegos_formateados.append({
                "id_juego": game_id,
                "estado": juego.get("status"),
                "equipos": {
                    "visitante": juego.get("away_name"),
                    "local": juego.get("home_name")
                },
                "prediccion_modelo": {
                    "rating_visitante": rating_vis,
                    "rating_local": rating_loc,
                    "probabilidad_visitante": f"{prob_vis}%",
                    "probabilidad_local": f"{prob_loc}%",
                    "pick_recomendado": pick_recomendado,
                    "nivel_confianza": confianza
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
    return {"mensaje": "API MLB Predicciones Activa"}
#prueba
