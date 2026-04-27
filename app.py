from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import statsapi
from datetime import datetime

app = FastAPI(title="MLB BET API")

# Configuración CORS para que tu frontend pueda consultar esta API sin bloqueos de seguridad
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # En producción, aquí pondrás la URL de tu frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {"mensaje": "API de MLB BET funcionando correctamente"}

@app.get("/api/juegos/hoy")
def obtener_juegos_hoy():
    # Obtenemos la fecha actual en el formato que exige la API de MLB (MM/DD/YYYY)
    hoy = datetime.now().strftime("%m/%d/%Y")
    
    try:
        # statsapi.schedule extrae el cronograma de la fecha
        juegos_raw = statsapi.schedule(date=hoy)
        juegos_formateados = []
        
        for juego in juegos_raw:
            juegos_formateados.append({
                "id_juego": juego.get("game_id"),
                "estado": juego.get("status"),
                "hora": juego.get("game_datetime"),
                "equipo_visitante": juego.get("away_name"),
                "equipo_local": juego.get("home_name"),
                "pitcher_visitante": juego.get("away_probable_pitcher", "Por anunciar"),
                "pitcher_local": juego.get("home_probable_pitcher", "Por anunciar")
            })
            
        return {"fecha": hoy, "total_juegos": len(juegos_formateados), "data": juegos_formateados}
        
    except Exception as e:
        return {"error": str(e)}