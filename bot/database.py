# bot/database.py
# Todas las funciones que interactúan con la base de datos SQLite.

import sqlite3
from datetime import datetime, timedelta
from .config import DB_FILE, HITOS_SECUENCIA


def db_connect():
    """Crea una conexión a la base de datos."""
    return sqlite3.connect(DB_FILE, check_same_thread=False)


def get_config_value(key):
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("SELECT valor FROM configuracion WHERE clave = ?", (key,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None


def set_config_value(key, value):
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO configuracion (clave, valor) VALUES (?, ?)",
        (key, str(value)),
    )
    conn.commit()
    conn.close()


def get_admin_id():
    admin_id_str = get_config_value("admin_id")
    return int(admin_id_str) if admin_id_str else None


def set_admin_id(user_id):
    set_config_value("admin_id", user_id)


def get_user_status(user_id):
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("SELECT estado FROM usuarios WHERE telegram_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None


def get_user_role(user_id):
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT rol FROM usuarios WHERE telegram_id = ? AND estado = 'autorizado'",
        (user_id,),
    )
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None


def add_pending_user(user_id, name):
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR IGNORE INTO usuarios (telegram_id, nombre, rol, estado) VALUES (?, ?, ?, ?)",
        (user_id, name, "desconocido", "pendiente"),
    )
    conn.commit()
    conn.close()


def get_notifiable_users():
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("SELECT telegram_id FROM usuarios WHERE estado = 'autorizado'")
    results = cursor.fetchall()
    conn.close()
    return [row[0] for row in results]


def update_user_status(user_id, rol):
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE usuarios SET rol = ?, estado = 'autorizado' WHERE telegram_id = ?",
        (rol, user_id),
    )
    conn.commit()
    updated_rows = cursor.rowcount
    conn.close()
    return updated_rows > 0


def get_all_users():
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("SELECT telegram_id, nombre, rol, estado FROM usuarios")
    users = cursor.fetchall()
    conn.close()
    return users


def get_solicitud_by_id(solicitud_id):
    conn = db_connect()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM solicitudes WHERE id = ?", (solicitud_id,))
    solicitud = cursor.fetchone()
    conn.close()
    return solicitud


def get_solicitudes_for_balance(distrito=None, gerencia=None, servicio=None):
    """Obtiene todas las solicitudes activas con su gerencia, hito actual y fecha planificada."""
    conn = db_connect()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    query_parts = []
    for hito in HITOS_SECUENCIA:
        query_parts.append(f"WHEN '{hito}' THEN fecha_planificada_{hito}")
    case_statement = "CASE hito_actual " + " ".join(query_parts) + " END"

    query = f"SELECT gerencia, ({case_statement}) as fecha_planificada FROM solicitudes WHERE hito_actual IS NOT NULL"
    params = []

    if distrito and distrito != "TODOS":
        query += " AND distrito = ?"
        params.append(distrito)
    if gerencia and gerencia != "TODOS":
        query += " AND gerencia = ?"
        params.append(gerencia)
    if servicio and servicio != "TODOS":
        query += " AND servicio = ?"
        params.append(servicio)

    cursor.execute(query, params)
    results = cursor.fetchall()
    conn.close()
    return [dict(row) for row in results]


def get_unique_column_values(column_name, distrito=None, gerencia=None, status="all"):
    """Obtiene valores únicos de una columna, con filtros opcionales."""
    conn = db_connect()
    cursor = conn.cursor()

    query = f"SELECT DISTINCT {column_name} FROM solicitudes WHERE {column_name} IS NOT NULL AND {column_name} != ''"
    params = []

    if status == "delayed":
        hoy_str = datetime.now().strftime("%Y-%m-%d")
        case_statement = "CASE hito_actual "
        for hito in HITOS_SECUENCIA:
            case_statement += f"WHEN '{hito}' THEN fecha_planificada_{hito} "
        case_statement += "END"
        query += f" AND hito_actual IS NOT NULL AND ({case_statement}) < ?"
        params.append(hoy_str)

    if distrito and distrito != "TODOS":
        query += " AND distrito = ?"
        params.append(distrito)
    if gerencia and gerencia != "TODOS":
        query += " AND gerencia = ?"
        params.append(gerencia)

    query += f" ORDER BY {column_name}"
    cursor.execute(query, params)
    values = [row[0] for row in cursor.fetchall()]
    conn.close()
    return values


def get_filtered_solicitudes(distrito=None, servicio=None):
    conn = db_connect()
    cursor = conn.cursor()
    query = "SELECT id, solicitud_contratacion FROM solicitudes"
    params = []
    conditions = []
    if distrito and distrito != "TODOS":
        conditions.append("distrito = ?")
        params.append(distrito)
    if servicio and servicio != "TODOS":
        conditions.append("servicio = ?")
        params.append(servicio)
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY id"
    cursor.execute(query, params)
    solicitudes = cursor.fetchall()
    conn.close()
    return solicitudes


def completar_hito_actual(solicitud_id):
    conn = db_connect()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT hito_actual FROM solicitudes WHERE id = ?", (solicitud_id,))
    solicitud = cursor.fetchone()
    if not solicitud or not solicitud["hito_actual"]:
        return None, None
    hito_actual = solicitud["hito_actual"]
    fecha_real_col = f"fecha_real_{hito_actual}"
    hoy_str = datetime.now().strftime("%Y-%m-%d")
    cursor.execute(
        f"UPDATE solicitudes SET {fecha_real_col} = ? WHERE id = ?",
        (hoy_str, solicitud_id),
    )
    indice_actual = HITOS_SECUENCIA.index(hito_actual)
    nuevo_hito = None
    if indice_actual + 1 < len(HITOS_SECUENCIA):
        nuevo_hito = HITOS_SECUENCIA[indice_actual + 1]
    cursor.execute(
        "UPDATE solicitudes SET hito_actual = ? WHERE id = ?",
        (nuevo_hito, solicitud_id),
    )
    conn.commit()
    conn.close()
    return hito_actual, nuevo_hito


def replanificar_hito_actual(solicitud_id, nueva_fecha_str):
    conn = db_connect()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    solicitud = get_solicitud_by_id(solicitud_id)
    if not solicitud or not solicitud["hito_actual"]:
        return None, []
    hito_actual = solicitud["hito_actual"]
    indice_hito_actual = HITOS_SECUENCIA.index(hito_actual)
    fecha_plan_col = f"fecha_planificada_{hito_actual}"
    historial_col = f"historial_fechas_{hito_actual}"
    posposiciones_col = f"posposiciones_{hito_actual}"
    fecha_anterior = solicitud[fecha_plan_col]
    if fecha_anterior:
        query = f"UPDATE solicitudes SET {fecha_plan_col} = ?, {historial_col} = CASE WHEN {historial_col} IS NULL OR {historial_col} = '' THEN ? ELSE {historial_col} || ', ' || ? END, {posposiciones_col} = {posposiciones_col} + 1 WHERE id = ?"
        cursor.execute(
            query, (nueva_fecha_str, fecha_anterior, fecha_anterior, solicitud_id)
        )
    else:
        cursor.execute(
            f"UPDATE solicitudes SET {fecha_plan_col} = ? WHERE id = ?",
            (nueva_fecha_str, solicitud_id),
        )
    hitos_ajustados = []
    fecha_referencia = datetime.strptime(nueva_fecha_str, "%Y-%m-%d")
    for i in range(indice_hito_actual + 1, len(HITOS_SECUENCIA)):
        hito_futuro = HITOS_SECUENCIA[i]
        fecha_futura_col = f"fecha_planificada_{hito_futuro}"
        fecha_futura_actual_str = solicitud[fecha_futura_col]
        if fecha_futura_actual_str:
            fecha_futura_actual = datetime.strptime(fecha_futura_actual_str, "%Y-%m-%d")
            if fecha_futura_actual <= fecha_referencia:
                fecha_referencia += timedelta(days=1)
                nueva_fecha_futura_str = fecha_referencia.strftime("%Y-%m-%d")
                cursor.execute(
                    f"UPDATE solicitudes SET {fecha_futura_col} = ? WHERE id = ?",
                    (nueva_fecha_futura_str, solicitud_id),
                )
                hitos_ajustados.append((hito_futuro, nueva_fecha_futura_str))
    conn.commit()
    conn.close()
    return hito_actual, hitos_ajustados


def get_solicitudes_for_today():
    conn = db_connect()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    hoy_str = datetime.now().strftime("%Y-%m-%d")
    cursor.execute("SELECT * FROM solicitudes WHERE hito_actual IS NOT NULL")
    solicitudes_activas = cursor.fetchall()
    solicitudes_de_hoy = []
    for solicitud in solicitudes_activas:
        hito_actual = solicitud["hito_actual"]
        fecha_plan = solicitud[f"fecha_planificada_{hito_actual}"]
        if fecha_plan == hoy_str:
            solicitudes_de_hoy.append(dict(solicitud))
    conn.close()
    return solicitudes_de_hoy


def get_delayed_solicitudes(distrito=None, gerencia=None, servicio=None):
    """Obtiene las solicitudes retrasadas, opcionalmente filtradas."""
    conn = db_connect()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    hoy_str = datetime.now().strftime("%Y-%m-%d")
    query_parts = []
    for hito in HITOS_SECUENCIA:
        query_parts.append(f"WHEN '{hito}' THEN fecha_planificada_{hito}")
    case_statement = "CASE hito_actual " + " ".join(query_parts) + " END"
    query = f"SELECT id, solicitud_contratacion, gerencia, responsable, hito_actual, ({case_statement}) as fecha_planificada FROM solicitudes WHERE hito_actual IS NOT NULL AND ({case_statement}) < ?"
    params = [hoy_str]
    if distrito and distrito != "TODOS":
        query += " AND distrito = ?"
        params.append(distrito)
    if gerencia and gerencia != "TODOS":
        query += " AND gerencia = ?"
        params.append(gerencia)
    if servicio and servicio != "TODOS":
        query += " AND servicio = ?"
        params.append(servicio)
    query += " ORDER BY gerencia, fecha_planificada"
    cursor.execute(query, params)
    solicitudes = cursor.fetchall()
    conn.close()
    return [dict(row) for row in solicitudes]


def solicitud_exists(cursor, solicitud_id):
    """Verifica si una solicitud ya existe en la base de datos."""
    cursor.execute("SELECT 1 FROM solicitudes WHERE id = ?", (solicitud_id,))
    return cursor.fetchone() is not None


def update_solicitud_info_from_excel(cursor, data):
    """Actualiza la información descriptiva de una solicitud."""
    cursor.execute(
        """
        UPDATE solicitudes SET 
            solicitud_contratacion = ?, servicio = ?, distrito = ?, gerencia = ?, 
            responsable = ?, etapa_contratacion = ?
        WHERE id = ?
    """,
        (
            data["solicitud_contratacion"],
            data["servicio"],
            data["distrito"],
            data["gerencia"],
            data["responsable"],
            data["etapa_contratacion"],
            data["id"],
        ),
    )


def insert_solicitud_from_excel(cursor, data):
    """Inserta una nueva solicitud con todos sus datos desde el Excel."""
    cursor.execute(
        """
        INSERT INTO solicitudes (
            id, solicitud_contratacion, servicio, distrito, gerencia, responsable,
            etapa_contratacion, hito_actual,
            fecha_planificada_presupuesto_base, fecha_real_presupuesto_base,
            fecha_planificada_fecha_solicitud, fecha_real_fecha_solicitud,
            fecha_planificada_estrategia, fecha_real_estrategia,
            fecha_planificada_inicio, fecha_real_inicio,
            fecha_planificada_decision, fecha_real_decision,
            fecha_planificada_acta_otorgamiento, fecha_real_acta_otorgamiento,
            fecha_planificada_notif_otorgamiento, fecha_real_notif_otorgamiento,
            fecha_planificada_contrato, fecha_real_contrato
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            data["id"],
            data["solicitud_contratacion"],
            data["servicio"],
            data["distrito"],
            data["gerencia"],
            data["responsable"],
            data["etapa_contratacion"],
            data["hito_actual"],
            data.get("fecha_planificada_presupuesto_base"),
            data.get("fecha_real_presupuesto_base"),
            data.get("fecha_planificada_fecha_solicitud"),
            data.get("fecha_real_fecha_solicitud"),
            data.get("fecha_planificada_estrategia"),
            data.get("fecha_real_estrategia"),
            data.get("fecha_planificada_inicio"),
            data.get("fecha_real_inicio"),
            data.get("fecha_planificada_decision"),
            data.get("fecha_real_decision"),
            data.get("fecha_planificada_acta_otorgamiento"),
            data.get("fecha_real_acta_otorgamiento"),
            data.get("fecha_planificada_notif_otorgamiento"),
            data.get("fecha_real_notif_otorgamiento"),
            data.get("fecha_planificada_contrato"),
            data.get("fecha_real_contrato"),
        ),
    )


def get_solicitudes_unidad_usuaria(distrito=None, gerencia=None, servicio=None):
    """Obtiene las solicitudes donde la gerencia es igual al responsable."""
    conn = db_connect()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    query = "SELECT * FROM solicitudes WHERE gerencia = responsable"
    params = []
    conditions = ["gerencia = responsable"]

    if distrito and distrito != "TODOS":
        conditions.append("distrito = ?")
        params.append(distrito)
    if gerencia and gerencia != "TODOS":
        conditions.append("gerencia = ?")
        params.append(gerencia)
    if servicio and servicio != "TODOS":
        conditions.append("servicio = ?")
        params.append(servicio)

    query = (
        "SELECT * FROM solicitudes WHERE " + " AND ".join(conditions) + " ORDER BY id"
    )

    cursor.execute(query, params)
    solicitudes = cursor.fetchall()
    conn.close()
    return [dict(row) for row in solicitudes]


def get_solicitudes_pendientes_por_dia():
    """Obtiene todas las solicitudes pendientes, ordenadas por su próxima fecha de hito."""
    conn = db_connect()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    query_parts = []
    for hito in HITOS_SECUENCIA:
        query_parts.append(f"WHEN '{hito}' THEN fecha_planificada_{hito}")
    case_statement = "CASE hito_actual " + " ".join(query_parts) + " END"

    query = f"""
        SELECT 
            id, 
            solicitud_contratacion, 
            gerencia, 
            responsable, 
            hito_actual, 
            ({case_statement}) as fecha_planificada 
        FROM solicitudes 
        WHERE hito_actual IS NOT NULL AND fecha_planificada IS NOT NULL
        ORDER BY fecha_planificada
    """

    cursor.execute(query)
    solicitudes = cursor.fetchall()
    conn.close()
    return [dict(row) for row in solicitudes]


def get_solicitudes_unidad_usuaria_pendientes_por_dia():
    """
    Obtiene todas las solicitudes pendientes donde la gerencia es el responsable,
    ordenadas por su próxima fecha de hito.
    """
    conn = db_connect()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    query_parts = []
    for hito in HITOS_SECUENCIA:
        query_parts.append(f"WHEN '{hito}' THEN fecha_planificada_{hito}")
    case_statement = "CASE hito_actual " + " ".join(query_parts) + " END"

    query = f"""
        SELECT
            id,
            solicitud_contratacion,
            gerencia,
            responsable,
            hito_actual,
            ({case_statement}) as fecha_planificada
        FROM solicitudes
        WHERE hito_actual IS NOT NULL
          AND fecha_planificada IS NOT NULL
          AND gerencia = responsable
        ORDER BY fecha_planificada
    """

    cursor.execute(query)
    solicitudes = cursor.fetchall()
    conn.close()
    return [dict(row) for row in solicitudes]
