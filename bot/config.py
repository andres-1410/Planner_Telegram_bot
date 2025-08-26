# bot/config.py
# Carga de variables de entorno y configuración de logging.

import os
import logging
from dotenv import load_dotenv

# Cargar variables de entorno desde el archivo .env
load_dotenv()

# --- Constantes ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
NOMBRE_ARCHIVO_EXCEL = "CRONOGRAMA DE CONTRATACIÓN.xlsx"
DB_FILE = "bot_database.db"
TIMEZONE = "America/Caracas"  # Asegúrate de que esta sea tu zona horaria

# --- Constantes de Hitos (Movidas aquí para evitar importación circular) ---
HITOS_SECUENCIA = [
    "estrategia",
    "inicio",
    "decision",
    "acta_otorgamiento",
    "notif_otorgamiento",
    "contrato",
]

HITO_NOMBRES_LARGOS = {
    "estrategia": "Estrategia de Contratación",
    "inicio": "Acta de Inicio - Solicitud A",
    "decision": "Decisión de Inicio",
    "acta_otorgamiento": "Acta de Decisión de Otorgamiento",
    "notif_otorgamiento": "Notificación de Otorgamiento",
    "contrato": "Contrato",
}

# --- Configuración de Logging ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)
