# bot/scheduler.py
# Lógica para programar y ejecutar las notificaciones.

import html
import sqlite3
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram.ext import Application
from telegram.constants import ParseMode

from .config import logger, TIMEZONE, HITOS_SECUENCIA, HITO_NOMBRES_LARGOS
from .database import get_config_value, get_notifiable_users, db_connect


def get_tarea_a_cumplir(hito_key):
    """Determina la tarea a cumplir según el hito actual."""
    if not hito_key:
        return "N/A"
    if hito_key == "presupuesto_base":
        return "Gerencia responsable recibe presupuesto base."
    if hito_key == "fecha_solicitud":
        return "Gerencia responsable entrega a Gerencia de Contrataciones."
    return "Entrega para firma de Presidencia ENT."


async def check_and_send_notifications(context: Application):
    """Función ejecutada por el scheduler para revisar y enviar alertas."""
    logger.info("Ejecutando revisión diaria de notificaciones...")

    days_in_advance_str = get_config_value("dias_anticipacion")
    if not days_in_advance_str:
        logger.warning(
            "No se pueden enviar notificaciones: 'dias_anticipacion' no está configurado."
        )
        return

    try:
        days_in_advance = int(days_in_advance_str)
        target_date_db = (datetime.now() + timedelta(days=days_in_advance)).strftime(
            "%Y-%m-%d"
        )

        conn = db_connect()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Query optimizada para buscar todas las notificaciones del día
        query_parts = []
        for hito in HITOS_SECUENCIA:
            query_parts.append(f"WHEN '{hito}' THEN fecha_planificada_{hito}")
        case_statement = "CASE hito_actual " + " ".join(query_parts) + " END"

        query = f"""
            SELECT id, solicitud_contratacion, hito_actual, responsable 
            FROM solicitudes 
            WHERE hito_actual IS NOT NULL AND ({case_statement}) = ?
        """
        cursor.execute(query, (target_date_db,))
        solicitudes_a_notificar = cursor.fetchall()

        users_to_notify = get_notifiable_users()
        if not users_to_notify:
            logger.warning("No hay usuarios configurados para recibir notificaciones.")
            conn.close()
            return

        # Agrupar notificaciones por responsable
        notificaciones_por_responsable = {}
        for sol in solicitudes_a_notificar:
            responsable = sol["responsable"] or "Sin Responsable"
            if responsable not in notificaciones_por_responsable:
                notificaciones_por_responsable[responsable] = []
            notificaciones_por_responsable[responsable].append(sol)

        conn.close()

        # Enviar mensajes agrupados
        for responsable, solicitudes in notificaciones_por_responsable.items():
            target_date_display = datetime.strptime(
                target_date_db, "%Y-%m-%d"
            ).strftime("%d/%m/%Y")

            message = "<b>PLAZOS CUMPLIDOS DENTRO DEL PLAN DE CONTRATACIONES Y PROYECTOS DE INVERSIÓN</b>\n"
            message += f"<b>🗓️ Vencimiento: {target_date_display}</b> 🗓️\n\n"
            message += "----------------------------------------\n"
            message += f"<b>Gerencia Responsable:</b> {html.escape(responsable)}\n\n"

            for solicitud in solicitudes:
                hito_actual = solicitud["hito_actual"]
                nombre_hito = HITO_NOMBRES_LARGOS.get(hito_actual, hito_actual)
                tarea = get_tarea_a_cumplir(hito_actual)

                message += f"<b>Fase:</b> {html.escape(nombre_hito)}\n"
                message += f"<b>Tarea a Cumplir:</b> {html.escape(tarea)}\n\n"
                message += f"<b>Solicitud ID {solicitud['id']}:</b> {html.escape(solicitud['solicitud_contratacion'])}\n\n"

            for user_id in users_to_notify:
                try:
                    await context.bot.send_message(
                        chat_id=user_id, text=message, parse_mode=ParseMode.HTML
                    )
                    logger.info(
                        f"Notificación para responsable '{responsable}' enviada a {user_id}."
                    )
                except Exception as e:
                    logger.error(f"No se pudo enviar notificación a {user_id}: {e}")

        logger.info("Revisión de notificaciones completada.")
    except Exception as e:
        logger.error(f"Error fatal en el proceso de notificación: {e}")


async def post_init(application: Application) -> None:
    """
    Función para ejecutar después de que la aplicación se inicialice.
    Aquí es el lugar correcto para iniciar el scheduler.
    """
    scheduler = AsyncIOScheduler(timezone=TIMEZONE)

    saved_time = get_config_value("hora_notificacion")
    if saved_time:
        try:
            hour, minute = map(int, saved_time.split(":"))
            scheduler.add_job(
                check_and_send_notifications,
                "cron",
                hour=hour,
                minute=minute,
                id="daily_check",
                args=[application],
            )
            logger.info(
                f"Job de notificación programado para ejecutarse diariamente a las {saved_time}."
            )
        except ValueError:
            logger.error(f"La hora guardada '{saved_time}' no es válida.")

    application.job_queue.scheduler = scheduler
    scheduler.start()
    logger.info("Scheduler iniciado correctamente.")
