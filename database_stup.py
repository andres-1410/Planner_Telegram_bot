# database_setup.py
# Este script crea la base de datos SQLite y las tablas necesarias para el bot.
# Ejecútalo una sola vez o cada vez que cambie la estructura de las tablas.

import sqlite3


def setup_database():
    """Crea y configura la base de datos y sus tablas."""
    try:
        conn = sqlite3.connect("bot_database.db")
        cursor = conn.cursor()

        # --- Tabla de Solicitudes (Actualizada) ---
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS solicitudes (
            id INTEGER PRIMARY KEY, -- Ya no es autoincremental, se basa en el Excel
            solicitud_contratacion TEXT NOT NULL,
            servicio TEXT,
            distrito TEXT,
            gerencia TEXT,
            responsable TEXT, -- NUEVA COLUMNA
            presupuesto_base REAL,
            fecha_solicitud DATE,
            etapa_contratacion TEXT,
            hito_actual TEXT,

            -- Hito: Presupuesto Base (NUEVO)
            fecha_planificada_presupuesto_base DATE,
            fecha_real_presupuesto_base DATE,
            posposiciones_presupuesto_base INTEGER DEFAULT 0,
            historial_fechas_presupuesto_base TEXT,

            -- Hito: Fecha de Solicitud (NUEVO)
            fecha_planificada_fecha_solicitud DATE,
            fecha_real_fecha_solicitud DATE,
            posposiciones_fecha_solicitud INTEGER DEFAULT 0,
            historial_fechas_fecha_solicitud TEXT,

            -- Hitos existentes
            fecha_planificada_estrategia DATE,
            fecha_real_estrategia DATE,
            posposiciones_estrategia INTEGER DEFAULT 0,
            historial_fechas_estrategia TEXT,
            
            fecha_planificada_inicio DATE,
            fecha_real_inicio DATE,
            posposiciones_inicio INTEGER DEFAULT 0,
            historial_fechas_inicio TEXT,
            
            fecha_planificada_decision DATE,
            fecha_real_decision DATE,
            posposiciones_decision INTEGER DEFAULT 0,
            historial_fechas_decision TEXT,
            
            fecha_planificada_acta_otorgamiento DATE,
            fecha_real_acta_otorgamiento DATE,
            posposiciones_acta_otorgamiento INTEGER DEFAULT 0,
            historial_fechas_acta_otorgamiento TEXT,
            
            fecha_planificada_notif_otorgamiento DATE,
            fecha_real_notif_otorgamiento DATE,
            posposiciones_notif_otorgamiento INTEGER DEFAULT 0,
            historial_fechas_notif_otorgamiento TEXT,

            fecha_planificada_contrato DATE,
            fecha_real_contrato DATE,
            posposiciones_contrato INTEGER DEFAULT 0,
            historial_fechas_contrato TEXT
        )
        """
        )

        # --- Tablas sin cambios ---
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS usuarios (
            telegram_id INTEGER PRIMARY KEY,
            nombre TEXT NOT NULL,
            rol TEXT NOT NULL,
            estado TEXT NOT NULL 
        )
        """
        )
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS configuracion (
            clave TEXT PRIMARY KEY,
            valor TEXT NOT NULL
        )
        """
        )
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS log_notificaciones (
            id_notificacion INTEGER PRIMARY KEY AUTOINCREMENT,
            id_solicitud INTEGER,
            nombre_evento TEXT NOT NULL,
            fecha_notificacion DATETIME NOT NULL,
            telegram_id_usuario INTEGER NOT NULL,
            FOREIGN KEY (id_solicitud) REFERENCES solicitudes (id)
        )
        """
        )

        conn.commit()
        conn.close()
        print(
            "Base de datos y tablas creadas/verificadas exitosamente en 'bot_database.db'"
        )

    except sqlite3.Error as e:
        print(f"Error al configurar la base de datos: {e}")


if __name__ == "__main__":
    setup_database()
