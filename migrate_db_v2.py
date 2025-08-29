# migrate_db_v2.py
# Script de un solo uso para añadir las nuevas columnas a la base de datos existente.

import sqlite3

DB_FILE = "bot_database.db"


def run_migration():
    """Añade las nuevas columnas a la tabla de solicitudes si no existen."""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        # Obtener la información de las columnas actuales
        cursor.execute("PRAGMA table_info(solicitudes)")
        columns = [column[1] for column in cursor.fetchall()]

        # Lista de nuevas columnas a añadir
        new_columns = {
            "responsable": "TEXT",
            "fecha_planificada_presupuesto_base": "DATE",
            "fecha_real_presupuesto_base": "DATE",
            "posposiciones_presupuesto_base": "INTEGER DEFAULT 0",
            "historial_fechas_presupuesto_base": "TEXT",
            "fecha_planificada_fecha_solicitud": "DATE",
            "fecha_real_fecha_solicitud": "DATE",
            "posposiciones_fecha_solicitud": "INTEGER DEFAULT 0",
            "historial_fechas_fecha_solicitud": "TEXT",
        }

        added_count = 0
        for col_name, col_type in new_columns.items():
            if col_name not in columns:
                print(f"Añadiendo columna '{col_name}'...")
                cursor.execute(
                    f"ALTER TABLE solicitudes ADD COLUMN {col_name} {col_type}"
                )
                added_count += 1

        if added_count > 0:
            conn.commit()
            print(
                f"¡Éxito! Se han añadido {added_count} nuevas columnas a la tabla 'solicitudes'."
            )
        else:
            print(
                "No se necesitaron añadir nuevas columnas. La base de datos ya está actualizada."
            )

        conn.close()

    except sqlite3.Error as e:
        print(f"Ocurrió un error en la base de datos: {e}")


if __name__ == "__main__":
    run_migration()
