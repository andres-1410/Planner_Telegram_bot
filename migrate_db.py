# migrate_db.py
# Script de un solo uso para añadir la columna GERENCIA a la base de datos existente.

import sqlite3

DB_FILE = "bot_database.db"


def migrate_add_gerencia_column():
    """Añade la columna GERENCIA a la tabla de solicitudes si no existe."""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        # Revisar si la columna ya existe para evitar errores
        cursor.execute("PRAGMA table_info(solicitudes)")
        columns = [column[1] for column in cursor.fetchall()]

        if "gerencia" not in columns:
            print("Columna 'gerencia' no encontrada. Añadiéndola...")
            # Usamos ALTER TABLE para añadir la nueva columna
            cursor.execute("ALTER TABLE solicitudes ADD COLUMN gerencia TEXT")
            conn.commit()
            print(
                "¡Éxito! La columna 'gerencia' ha sido añadida a la tabla de solicitudes."
            )
        else:
            print("La columna 'gerencia' ya existe. No se necesita ninguna acción.")

        conn.close()

    except sqlite3.Error as e:
        print(f"Ocurrió un error en la base de datos: {e}")


if __name__ == "__main__":
    migrate_add_gerencia_column()
