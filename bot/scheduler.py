# bot/scheduler.py
# Lógica para programar y ejecutar las notificaciones.

import html
import sqlite3  # <-- CORRECCIÓN: Se añadió la importación que faltaba.
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram.ext import Application
from telegram.constants import ParseMode

from .config import logger, TIMEZONE, HITO_NOMBRES_LARGOS
from .database import get_config_value, get_notifiable_users, db_connect


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
        target_date = (datetime.now() + timedelta(days=days_in_advance)).strftime(
            "%Y-%m-%d"
        )
        logger.info(f"Buscando eventos para la fecha: {target_date}")

        conn = db_connect()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # La lógica ahora se enfoca solo en el hito_actual de cada solicitud.
        # 1. Obtenemos todas las solicitudes que todavía están activas.
        cursor.execute(
            "SELECT id, solicitud_contratacion, hito_actual FROM solicitudes WHERE hito_actual IS NOT NULL"
        )
        solicitudes_activas = cursor.fetchall()

        users_to_notify = get_notifiable_users()
        if not users_to_notify:
            logger.warning("No hay usuarios configurados para recibir notificaciones.")
            conn.close()
            return

        for solicitud in solicitudes_activas:
            hito_actual = solicitud["hito_actual"]
            fecha_plan_col = f"fecha_planificada_{hito_actual}"

            # 2. Obtenemos la fecha específica del hito actual para esta solicitud.
            cursor.execute(
                f"SELECT {fecha_plan_col} FROM solicitudes WHERE id = ?",
                (solicitud["id"],),
            )
            fecha_plan_result = cursor.fetchone()

            if fecha_plan_result and fecha_plan_result[0] == target_date:
                solicitud_id = solicitud["id"]
                solicitud_name = solicitud["solicitud_contratacion"]
                event_name = HITO_NOMBRES_LARGOS.get(hito_actual, hito_actual)

                logger.info(
                    f"¡Evento encontrado! Solicitud: '{solicitud_name}', Evento: '{event_name}'"
                )

                solicitud_name_safe = html.escape(solicitud_name)
                event_name_safe = html.escape(event_name)

                message = (
                    f"🔔 <b>Alerta de Vencimiento</b> 🔔\n\n"
                    f"La fecha para el evento <b>{event_name_safe}</b> de la solicitud '<i>{solicitud_name_safe}</i>' está próxima.\n\n"
                    f"🗓️ <b>Fecha Planificada:</b> {target_date}\n"
                    f"⏳ <b>Anticipación:</b> {days_in_advance} día(s)"
                )
                for user_id in users_to_notify:
                    try:
                        await context.bot.send_message(
                            chat_id=user_id, text=message, parse_mode=ParseMode.HTML
                        )
                        logger.info(
                            f"Notificación enviada a {user_id} para el evento '{event_name}' de la solicitud ID {solicitud_id}"
                        )
                    except Exception as e:
                        logger.error(f"No se pudo enviar notificación a {user_id}: {e}")

        conn.close()
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
