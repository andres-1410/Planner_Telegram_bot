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
NOMBRE_ARCHIVO_PRINCIPAL = "CRONOGRAMA PRINCIPAL.xlsx"  # "CRONOGRAMA DE CONTRATACIÓN.xlsx"  #   # --- NUEVO ARCHIVO ---
DB_FILE = "bot_database.db"
TIMEZONE = "America/Caracas"  # Asegúrate de que esta sea tu zona horaria

# --- Constantes de Hitos (Movidas aquí para evitar importación circular) ---
HITOS_SECUENCIA = [
    "presupuesto_base",
    "fecha_solicitud",
    "estrategia",
    "inicio",
    "decision",
    "acta_otorgamiento",
    "notif_otorgamiento",
    "contrato",
]

HITO_NOMBRES_LARGOS = {
    "presupuesto_base": "PRESUPUESTO BASE",
    "fecha_solicitud": "FECHA DE SOLICITUD",
    "estrategia": "ESTRATEGIA DE CONTRATACIÓN",
    "inicio": "ACTA DE INICIO - SOLICITUD A",
    "decision": "DECISIÓN DE INICIO",
    "acta_otorgamiento": "ACTA DE DECISIÓN DE OTORGAMIENTO",
    "notif_otorgamiento": "NOTIFICACIÓN DE OTORGAMIENTO",
    "contrato": "CONTRATO",
}

# --- Configuración de Logging ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger("bot.config")
