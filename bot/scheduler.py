# bot/scheduler.py
# Lógica para programar y ejecutar las notificaciones.

import html
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram.ext import Application
from telegram.constants import ParseMode

from .config import logger, TIMEZONE
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
        cursor = conn.cursor()

        date_columns_map = {
            "fecha_planificada_estrategia": (
                "Estrategia de Contratación",
                "fecha_real_estrategia",
            ),
            "fecha_planificada_inicio": (
                "Acta de Inicio - Solicitud A",
                "fecha_real_inicio",
            ),
            "fecha_planificada_decision": ("Decisión de Inicio", "fecha_real_decision"),
            "fecha_planificada_acta_otorgamiento": (
                "Acta de Decisión de Otorgamiento",
                "fecha_real_acta_otorgamiento",
            ),
            "fecha_planificada_notif_otorgamiento": (
                "Notificación de Otorgamiento",
                "fecha_real_notif_otorgamiento",
            ),
            "fecha_planificada_contrato": ("Contrato", "fecha_real_contrato"),
        }

        users_to_notify = get_notifiable_users()
        if not users_to_notify:
            logger.warning("No hay usuarios configurados para recibir notificaciones.")
            conn.close()
            return

        for planned_col, (event_name, real_col) in date_columns_map.items():
            query = f"SELECT id, solicitud_contratacion FROM solicitudes WHERE {planned_col} = ? AND {real_col} IS NULL"
            cursor.execute(query, (target_date,))
            events = cursor.fetchall()

            for event_id, solicitud_name in events:
                logger.info(
                    f"¡Evento encontrado! Solicitud: '{solicitud_name}', Evento: '{event_name}'"
                )

                # CORRECCIÓN DEFINITIVA: Usar HTML para el formato del mensaje.
                # html.escape() previene errores con caracteres como <, > y &.
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
                        # Usamos ParseMode.HTML que es más robusto
                        await context.bot.send_message(
                            chat_id=user_id, text=message, parse_mode=ParseMode.HTML
                        )
                        logger.info(
                            f"Notificación enviada a {user_id} para el evento '{event_name}' de la solicitud ID {event_id}"
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

    # Hacemos el scheduler accesible desde los handlers
    application.job_queue.scheduler = scheduler
    scheduler.start()
    logger.info("Scheduler iniciado correctamente.")
