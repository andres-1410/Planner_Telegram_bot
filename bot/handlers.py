# bot/handlers.py
# Manejadores para todos los comandos y mensajes del bot.

import os
import pandas as pd
import html
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CallbackQueryHandler,
    CommandHandler,
)
from telegram.constants import ParseMode

from .config import logger, NOMBRE_ARCHIVO_EXCEL, HITOS_SECUENCIA, HITO_NOMBRES_LARGOS
from .database import *

from .scheduler import check_and_send_notifications

# Estados para los ConversationHandlers
SELECTING_DISTRITO, SELECTING_SERVICIO = range(2)
LIST_SELECTING_DISTRITO, LIST_SELECTING_SERVICIO = range(2, 4)
RETRASO_SELECTING_DISTRITO, RETRASO_SELECTING_GERENCIA, RETRASO_SELECTING_SERVICIO = (
    range(4, 7)
)
REPORTE_SELECTING_DISTRITO, REPORTE_SELECTING_GERENCIA, REPORTE_SELECTING_SERVICIO = (
    range(7, 10)
)


# --- Funciones de Utilidad ---
def safe_date_convert(date_value):
    if pd.isna(date_value) or date_value == "" or str(date_value).strip() == "-":
        return None
    try:
        return pd.to_datetime(date_value, dayfirst=True).strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        logger.warning(f"No se pudo convertir el valor '{date_value}' a una fecha.")
        return None


def format_date_for_display(date_str_db):
    """Convierte una fecha de formato YYYY-MM-DD a DD/MM/YYYY para mostrar al usuario."""
    if not date_str_db:
        return "No especificada"
    try:
        return datetime.strptime(date_str_db, "%Y-%m-%d").strftime("%d/%m/%Y")
    except (ValueError, TypeError):
        return date_str_db


def get_weekday_in_spanish(date_obj):
    """Devuelve el nombre del día de la semana en español."""
    weekdays = [
        "Lunes",
        "Martes",
        "Miércoles",
        "Jueves",
        "Viernes",
        "Sábado",
        "Domingo",
    ]
    return weekdays[date_obj.weekday()]


def calculate_balance(solicitudes):
    total = len(solicitudes)
    atrasadas, proximas, al_dia = 0, 0, 0
    dias_anticipacion = int(get_config_value("dias_anticipacion") or 0)
    hoy = datetime.now().date()
    for solicitud in solicitudes:
        fecha_plan = solicitud.get("fecha_planificada")
        if fecha_plan:
            fecha_plan_dt = datetime.strptime(fecha_plan, "%Y-%m-%d").date()
            dias_restantes = (fecha_plan_dt - hoy).days
            if dias_restantes < 0:
                atrasadas += 1
            elif dias_restantes <= dias_anticipacion:
                proximas += 1
            else:
                al_dia += 1
    return total, atrasadas, proximas, al_dia


# --- Lógica de Autorización Centralizada ---
async def handle_unauthorized(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Función central para manejar a cualquier usuario no autorizado."""
    user = update.effective_user
    user_id, user_name = user.id, user.first_name
    user_status = get_user_status(user_id)
    admin_id = get_admin_id()

    if user_id == admin_id and user_status == "autorizado":
        await update.message.reply_text("Comando no reconocido. Usa /help.")
        return

    if user_status is None:
        logger.info(f"Usuario nuevo no autorizado: {user_name} ({user.id}).")
        add_pending_user(user_id, user_name)
        await update.message.reply_text(
            "Tu solicitud de acceso está siendo validada por el administrador. Por favor, espera."
        )
        if admin_id:
            try:
                user_name_safe = html.escape(user_name)
                text_to_admin = (
                    f"<b>⚠️ Nueva Solicitud de Acceso ⚠️</b>\n\n"
                    f"El usuario <b>{user_name_safe}</b> (ID: <code>{user_id}</code>) quiere usar el bot.\n\n"
                    f"Para autorizarlo, usa el comando:\n<code>/autorizar {user_id} [rol]</code>\n\n"
                    f"Roles disponibles: <code>notificado</code>, <code>contrataciones</code>."
                )
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=text_to_admin,
                    parse_mode=ParseMode.HTML,
                )
            except Exception as e:
                logger.error(f"No se pudo notificar al admin {admin_id}: {e}")

    elif user_status == "pendiente":
        await update.message.reply_text(
            "Tu solicitud de acceso todavía está pendiente."
        )


# --- Handlers de Comandos ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    admin_id = get_admin_id()
    if not admin_id:
        set_admin_id(user.id)
        add_pending_user(user.id, user.first_name)
        conn = db_connect()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE usuarios SET rol = ?, estado = ? WHERE telegram_id = ?",
            ("admin", "autorizado", user.id),
        )
        conn.commit()
        conn.close()
        await update.message.reply_text(
            f"¡Hola, {user.first_name}! Has sido configurado como administrador."
        )
    else:
        if get_user_status(user.id) != "autorizado":
            await handle_unauthorized(update, context)
        else:
            await update.message.reply_text(
                "¡Bienvenido al Bot de Alertas de Contratación!"
            )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if get_user_status(update.effective_user.id) != "autorizado":
        await handle_unauthorized(update, context)
        return

    help_text = (
        "Comandos disponibles para todos:\n"
        "/start - Inicia la conversación.\n"
        "/help - Muestra esta ayuda.\n"
        "/hoy - Muestra los hitos que vencen hoy.\n"
        "/retrasado - Muestra un listado filtrado de solicitudes retrasadas.\n"
        "/balance - Muestra un resumen del estado de todas las solicitudes.\n"
        "/balance_filtro - Muestra un resumen filtrado por distrito y servicio.\n"
        "/listar_solicitudes - Inicia un listado filtrado de solicitudes.\n"
        "/ver_solicitud [ID] - Muestra el detalle de una solicitud.\n\n"
        "<b>Comandos de Gestión (Rol: contrataciones o admin):</b>\n"
        "/replanificar [ID] [DD/MM/YYYY] - Cambia la fecha del hito actual.\n"
        "/completar [ID] - Marca el hito actual como completado.\n\n"
        "<b>Comandos de Administrador (Rol: admin):</b>\n"
        "/reporte - Genera un reporte consolidado por gerencia.\n"
        "/cargar_excel - Actualiza los datos desde el archivo Excel.\n"
        "/configurar_dias N - Define los días de antelación.\n"
        "/configurar_hora HH:MM - Define la hora de las alertas.\n"
        "/listar_usuarios - Muestra todos los usuarios registrados.\n"
        "/autorizar [ID] [rol] - Autoriza a un usuario."
    )
    await update.message.reply_text(help_text, parse_mode=ParseMode.HTML)


async def cargar_excel_local(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if get_user_role(update.effective_user.id) != "admin":
        await update.message.reply_text("No tienes permiso para ejecutar este comando.")
        return
    file_path = NOMBRE_ARCHIVO_EXCEL
    if not os.path.exists(file_path):
        await update.message.reply_text(
            f"❌ Error: No se encontró el archivo {file_path}."
        )
        return
    await update.message.reply_text(
        f"Archivo {file_path} encontrado. Actualizando datos..."
    )
    try:
        df = pd.read_excel(file_path).fillna("")
        conn = db_connect()
        cursor = conn.cursor()

        column_mapping = {
            "N": "id",
            "GERENCIA": "gerencia",
        }
        df_renamed = df.rename(columns=column_mapping)

        if "id" not in df_renamed.columns or "gerencia" not in df_renamed.columns:
            await update.message.reply_text(
                "❌ Error: El archivo Excel debe contener las columnas 'N' y 'GERENCIA'."
            )
            return

        updated_count = 0
        for index, row in df_renamed.iterrows():
            solicitud_id = row.get("id")
            gerencia = row.get("gerencia")

            if pd.notna(solicitud_id) and pd.notna(gerencia):
                cursor.execute(
                    "UPDATE solicitudes SET gerencia = ? WHERE id = ?",
                    (str(gerencia), int(solicitud_id)),
                )
                if cursor.rowcount > 0:
                    updated_count += 1

        conn.commit()
        conn.close()
        await update.message.reply_text(
            f"✅ ¡Éxito! Se han actualizado {updated_count} solicitudes con la nueva información de gerencia."
        )
    except Exception as e:
        logger.error(f"Error al procesar el archivo Excel local: {e}")
        await update.message.reply_text(
            f"❌ Ocurrió un error al procesar el archivo: {e}"
        )


async def ver_solicitud_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if get_user_status(update.effective_user.id) != "autorizado":
        await handle_unauthorized(update, context)
        return
    try:
        solicitud_id = int(context.args[0])
    except (IndexError, ValueError):
        await update.message.reply_text("Uso incorrecto. Ejemplo: `/ver_solicitud 1`")
        return
    solicitud = get_solicitud_by_id(solicitud_id)
    if not solicitud:
        await update.message.reply_text(
            f"No se encontró ninguna solicitud con el ID {solicitud_id}."
        )
        return
    message = f"<b>Detalles de la Solicitud ID: {solicitud['id']}</b>\n"
    message += f"<b>Nombre:</b> {solicitud['solicitud_contratacion']}\n"
    message += f"<b>Gerencia:</b> {solicitud['gerencia'] or 'No especificada'}\n"
    message += f"<b>Etapa (Manual):</b> {solicitud['etapa_contratacion'] or 'No especificada'}\n"
    hito_actual_key = solicitud["hito_actual"]
    if hito_actual_key:
        nombre_largo = HITO_NOMBRES_LARGOS.get(hito_actual_key, hito_actual_key)
        message += f"<b>Próximo Hito:</b> {nombre_largo}\n\n"
    else:
        message += "<b>Estatus General:</b> 🎉 ¡Completado! 🎉\n\n"
    for hito_key in HITOS_SECUENCIA:
        nombre_hito = HITO_NOMBRES_LARGOS.get(hito_key, hito_key)
        fecha_plan = solicitud[f"fecha_planificada_{hito_key}"]
        fecha_real = solicitud[f"fecha_real_{hito_key}"]
        if fecha_real:
            message += f"✅ <b>{nombre_hito}:</b> Completado el {format_date_for_display(fecha_real)}\n"
        elif fecha_plan:
            if hito_key == hito_actual_key:
                fecha_plan_dt = datetime.strptime(fecha_plan, "%Y-%m-%d")
                hoy = datetime.now()
                dias_restantes = (fecha_plan_dt.date() - hoy.date()).days
                dias_anticipacion = int(get_config_value("dias_anticipacion") or 0)
                if dias_restantes < 0:
                    estatus = f"🔴 Retrasado por {-dias_restantes} día(s)"
                elif dias_restantes <= dias_anticipacion:
                    estatus = f"🟡 Próximo (faltan {dias_restantes} día(s))"
                else:
                    estatus = f"🟢 A tiempo (faltan {dias_restantes} día(s))"
                message += f"➡️ <b>{nombre_hito}:</b> Planificado para {format_date_for_display(fecha_plan)} ({estatus})\n"
            else:
                message += f"⚪️ <b>{nombre_hito}:</b> Pendiente para el {format_date_for_display(fecha_plan)}\n"
        else:
            message += f"⚪️ <b>{nombre_hito}:</b> Sin fecha planificada\n"
    await update.message.reply_text(message, parse_mode=ParseMode.HTML)


async def configurar_dias_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if get_user_role(update.effective_user.id) != "admin":
        await update.message.reply_text("No tienes permiso para ejecutar este comando.")
        return
    try:
        days = int(context.args[0])
        if days < 0:
            raise ValueError
        set_config_value("dias_anticipacion", days)
        await update.message.reply_text(
            f"✅ Configuración guardada: Notificaciones con {days} día(s) de antelación."
        )
    except (IndexError, ValueError):
        await update.message.reply_text("Uso incorrecto. Ejemplo: /configurar_dias 2")


async def configurar_hora_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if get_user_role(update.effective_user.id) != "admin":
        await update.message.reply_text("No tienes permiso para ejecutar este comando.")
        return
    try:
        time_str = context.args[0]
        hour, minute = map(int, time_str.split(":"))
        scheduler = context.application.job_queue.scheduler
        scheduler.add_job(
            check_and_send_notifications,
            "cron",
            hour=hour,
            minute=minute,
            id="daily_check",
            args=[context.application],
            replace_existing=True,
        )
        set_config_value("hora_notificacion", time_str)
        await update.message.reply_text(
            f"✅ Configuración guardada: La revisión diaria se ejecutará a las {time_str}."
        )
    except (IndexError, ValueError):
        await update.message.reply_text(
            "Uso incorrecto. Formato HH:MM. Ejemplo: /configurar_hora 08:30"
        )


async def autorizar_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if get_user_role(update.effective_user.id) != "admin":
        await update.message.reply_text("No tienes permiso para ejecutar este comando.")
        return
    try:
        user_id_to_auth = int(context.args[0])
        rol = context.args[1].lower()
        valid_roles = ["notificado", "contrataciones"]
        if rol not in valid_roles:
            await update.message.reply_text(
                f"Rol no válido. Roles permitidos: {', '.join(valid_roles)}"
            )
            return
        if update_user_status(user_id_to_auth, rol):
            await update.message.reply_text(
                f"✅ Usuario {user_id_to_auth} autorizado con el rol de '{rol}'."
            )
            try:
                await context.bot.send_message(
                    chat_id=user_id_to_auth,
                    text=f"¡Has sido autorizado en el bot con el rol de '{rol}'!",
                )
            except Exception as e:
                logger.warning(
                    f"No se pudo notificar al usuario {user_id_to_auth}: {e}"
                )
        else:
            await update.message.reply_text(
                "No se encontró al usuario. Pídele que envíe un mensaje al bot primero."
            )
    except (IndexError, ValueError):
        await update.message.reply_text(
            "Uso incorrecto. Ejemplo: `/autorizar 12345678 notificado`"
        )


async def listar_usuarios_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if get_user_role(update.effective_user.id) != "admin":
        await update.message.reply_text("No tienes permiso para ejecutar este comando.")
        return
    users = get_all_users()
    if not users:
        await update.message.reply_text("No hay usuarios registrados.")
        return
    message = "<b>👥 Lista de Usuarios Registrados 👥</b>\n\n"
    for user in users:
        telegram_id, nombre, rol, estado = user
        message += f"<b>Nombre:</b> {nombre}\n"
        message += f"   - <b>ID:</b> <code>{telegram_id}</code>\n"
        message += f"   - <b>Rol:</b> {rol}\n"
        message += f"   - <b>Estado:</b> {estado}\n\n"
    await update.message.reply_text(message, parse_mode=ParseMode.HTML)


async def replanificar_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    user_role = get_user_role(update.effective_user.id)
    if user_role not in ["admin", "contrataciones"]:
        await update.message.reply_text("No tienes permiso para ejecutar este comando.")
        return
    try:
        solicitud_id = int(context.args[0])
        nueva_fecha_usuario = context.args[1]
        nueva_fecha_dt = datetime.strptime(nueva_fecha_usuario, "%d/%m/%Y")
        nueva_fecha_db = nueva_fecha_dt.strftime("%Y-%m-%d")

        hito_replanificado, hitos_ajustados = replanificar_hito_actual(
            solicitud_id, nueva_fecha_db
        )
        if hito_replanificado:
            nombre_largo = HITO_NOMBRES_LARGOS.get(
                hito_replanificado, hito_replanificado
            )
            message = f"✅ Hito '{nombre_largo}' de la solicitud {solicitud_id} replanificado para el {nueva_fecha_usuario}."
            if hitos_ajustados:
                message += "\n\n⚠️ <b>Hitos futuros ajustados automáticamente:</b>\n"
                for hito, fecha in hitos_ajustados:
                    nombre_largo_ajustado = HITO_NOMBRES_LARGOS.get(hito, hito)
                    message += f"- {nombre_largo_ajustado} movido a {format_date_for_display(fecha)}\n"
            await update.message.reply_text(message, parse_mode=ParseMode.HTML)
        else:
            await update.message.reply_text(
                "No se pudo replanificar. Verifica el ID o si la solicitud ya fue completada."
            )

    except (IndexError, ValueError):
        await update.message.reply_text(
            "Uso incorrecto. Ejemplo:\n`/replanificar 15 31/12/2025`"
        )


async def completar_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_role = get_user_role(update.effective_user.id)
    if user_role not in ["admin", "contrataciones"]:
        await update.message.reply_text("No tienes permiso para ejecutar este comando.")
        return
    try:
        solicitud_id = int(context.args[0])
        hito_completado, nuevo_hito = completar_hito_actual(solicitud_id)
        if hito_completado:
            nombre_largo_completado = HITO_NOMBRES_LARGOS.get(
                hito_completado, hito_completado
            )
            await update.message.reply_text(
                f"✅ Hito '{nombre_largo_completado}' de la solicitud {solicitud_id} marcado como completado."
            )
            if nuevo_hito:
                nombre_largo_nuevo = HITO_NOMBRES_LARGOS.get(nuevo_hito, nuevo_hito)
                await update.message.reply_text(
                    f"➡️ El próximo hito es: '{nombre_largo_nuevo}'."
                )
            else:
                await update.message.reply_text(
                    "🎉 ¡Todos los hitos de esta solicitud han sido completados! 🎉"
                )
        else:
            await update.message.reply_text(
                "No se pudo completar. Verifica el ID o si la solicitud ya fue completada."
            )
    except (IndexError, ValueError):
        await update.message.reply_text("Uso incorrecto. Ejemplo:\n`/completar 15`")


async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if get_user_status(update.effective_user.id) != "autorizado":
        await handle_unauthorized(update, context)
        return
    solicitudes = get_solicitudes_for_balance()
    total, atrasadas, proximas, al_dia = calculate_balance(solicitudes)
    message = (
        "📊 <b>Balance General de Solicitudes Activas</b> 📊\n\n"
        f"Total de Solicitudes en Proceso: <b>{total}</b>\n"
        f"🟢 A tiempo: <b>{al_dia}</b>\n"
        f"🟡 Próximas a vencer: <b>{proximas}</b>\n"
        f"🔴 Retrasadas: <b>{atrasadas}</b>"
    )
    await update.message.reply_text(message, parse_mode=ParseMode.HTML)


async def hoy_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if get_user_status(update.effective_user.id) != "autorizado":
        await handle_unauthorized(update, context)
        return
    solicitudes = get_solicitudes_for_today()
    if not solicitudes:
        await update.message.reply_text(
            "No hay hitos con fecha de vencimiento para hoy."
        )
        return
    message = "<b>🗓️ Hitos con Vencimiento Hoy</b> 🗓️\n\n"
    for solicitud in solicitudes:
        hito_actual = solicitud["hito_actual"]
        nombre_hito = HITO_NOMBRES_LARGOS.get(hito_actual, hito_actual)
        message += f"<b>Solicitud ID {solicitud['id']}:</b> {solicitud['solicitud_contratacion']}\n"
        message += f"   - <b>Hito pendiente:</b> {nombre_hito}\n\n"
    await update.message.reply_text(message, parse_mode=ParseMode.HTML)


# --- ConversationHandlers ---
async def cancel_filtro(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Función genérica para cancelar cualquier conversación."""
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("Operación cancelada.")
    else:
        await update.message.reply_text("Operación cancelada.")
    context.user_data.clear()
    return ConversationHandler.END


async def balance_filtro_start(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    if get_user_status(update.effective_user.id) != "autorizado":
        await handle_unauthorized(update, context)
        return ConversationHandler.END
    distritos = get_unique_column_values("distrito")
    if not distritos:
        await update.message.reply_text("No hay distritos disponibles para filtrar.")
        return ConversationHandler.END
    keyboard = [
        [InlineKeyboardButton(distrito, callback_data=distrito)]
        for distrito in distritos
    ]
    keyboard.insert(
        0, [InlineKeyboardButton("TODOS LOS DISTRITOS", callback_data="TODOS")]
    )
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "<b>Paso 1/2:</b> Por favor, selecciona un distrito:",
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML,
    )
    return SELECTING_DISTRITO


async def distrito_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    distrito_seleccionado = query.data
    context.user_data["distrito_filtro"] = distrito_seleccionado
    servicios = get_unique_column_values("servicio", distrito=distrito_seleccionado)
    if not servicios:
        await query.edit_message_text(
            "No hay servicios disponibles para este distrito."
        )
        return ConversationHandler.END
    keyboard = [
        [InlineKeyboardButton(servicio, callback_data=servicio)]
        for servicio in servicios
    ]
    keyboard.insert(
        0, [InlineKeyboardButton("TODOS LOS SERVICIOS", callback_data="TODOS")]
    )
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        f"<b>Paso 2/2:</b> Distrito seleccionado: <i>{distrito_seleccionado}</i>.\nAhora, selecciona un servicio:",
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML,
    )
    return SELECTING_SERVICIO


async def servicio_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    servicio_seleccionado = query.data
    distrito_seleccionado = context.user_data.get("distrito_filtro", "TODOS")
    await query.edit_message_text("Calculando balance con los filtros seleccionados...")
    solicitudes = get_solicitudes_for_balance(
        distrito=distrito_seleccionado, servicio=servicio_seleccionado
    )
    total, atrasadas, proximas, al_dia = calculate_balance(solicitudes)
    message = (
        f"📊 <b>Balance Filtrado</b> 📊\n\n"
        f"<b>Distrito:</b> {distrito_seleccionado}\n"
        f"<b>Servicio:</b> {servicio_seleccionado}\n\n"
        f"Total de Solicitudes en Proceso: <b>{total}</b>\n"
        f"🟢 A tiempo: <b>{al_dia}</b>\n"
        f"🟡 Próximas a vencer: <b>{proximas}</b>\n"
        f"🔴 Retrasadas: <b>{atrasadas}</b>"
    )
    await query.edit_message_text(text=message, parse_mode=ParseMode.HTML)
    context.user_data.clear()
    return ConversationHandler.END


balance_filtro_handler = ConversationHandler(
    entry_points=[CommandHandler("balance_filtro", balance_filtro_start)],
    states={
        SELECTING_DISTRITO: [CallbackQueryHandler(distrito_callback)],
        SELECTING_SERVICIO: [CallbackQueryHandler(servicio_callback)],
    },
    fallbacks=[CommandHandler("cancelar", cancel_filtro)],
)


async def listar_solicitudes_start(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    if get_user_status(update.effective_user.id) != "autorizado":
        await handle_unauthorized(update, context)
        return ConversationHandler.END
    distritos = get_unique_column_values("distrito")
    if not distritos:
        await update.message.reply_text("No hay distritos disponibles para filtrar.")
        return ConversationHandler.END
    keyboard = [
        [InlineKeyboardButton(distrito, callback_data=distrito)]
        for distrito in distritos
    ]
    keyboard.insert(
        0, [InlineKeyboardButton("TODOS LOS DISTRITOS", callback_data="TODOS")]
    )
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "<b>Paso 1/2:</b> Por favor, selecciona un distrito para listar:",
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML,
    )
    return LIST_SELECTING_DISTRITO


async def distrito_callback_list(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    query = update.callback_query
    await query.answer()
    distrito_seleccionado = query.data
    context.user_data["distrito_filtro_list"] = distrito_seleccionado
    servicios = get_unique_column_values("servicio", distrito=distrito_seleccionado)
    if not servicios:
        await query.edit_message_text(
            "No hay servicios disponibles para este distrito."
        )
        context.user_data.clear()
        return ConversationHandler.END
    keyboard = [
        [InlineKeyboardButton(servicio, callback_data=servicio)]
        for servicio in servicios
    ]
    keyboard.insert(
        0, [InlineKeyboardButton("TODOS LOS SERVICIOS", callback_data="TODOS")]
    )
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        f"<b>Paso 2/2:</b> Distrito seleccionado: <i>{distrito_seleccionado}</i>.\nAhora, selecciona un servicio:",
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML,
    )
    return LIST_SELECTING_SERVICIO


async def servicio_callback_list(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    query = update.callback_query
    await query.answer()
    servicio_seleccionado = query.data
    distrito_seleccionado = context.user_data.get("distrito_filtro_list", "TODOS")
    await query.edit_message_text(
        f"Buscando solicitudes para:\n<b>Distrito:</b> {distrito_seleccionado}\n<b>Servicio:</b> {servicio_seleccionado}",
        parse_mode=ParseMode.HTML,
    )
    solicitudes = get_filtered_solicitudes(
        distrito=distrito_seleccionado, servicio=servicio_seleccionado
    )
    if not solicitudes:
        await query.message.reply_text(
            "No se encontraron solicitudes con los filtros seleccionados."
        )
        context.user_data.clear()
        return ConversationHandler.END
    chunk_size = 20
    message_chunk = ""
    for i, (solicitud_id, nombre) in enumerate(solicitudes, 1):
        message_chunk += f"ID: {solicitud_id} - {nombre}\n"
        if i % chunk_size == 0 or i == len(solicitudes):
            try:
                await query.message.reply_text(message_chunk)
                message_chunk = ""
            except Exception as e:
                logger.error(f"Error enviando bloque de solicitudes: {e}")
                await query.message.reply_text(
                    "Ocurrió un error al enviar una parte de la lista."
                )
                break
    await query.message.reply_text(
        "--- Fin de la lista ---\nUsa /ver_solicitud [ID] para ver los detalles."
    )
    context.user_data.clear()
    return ConversationHandler.END


listar_solicitudes_handler = ConversationHandler(
    entry_points=[CommandHandler("listar_solicitudes", listar_solicitudes_start)],
    states={
        LIST_SELECTING_DISTRITO: [CallbackQueryHandler(distrito_callback_list)],
        LIST_SELECTING_SERVICIO: [CallbackQueryHandler(servicio_callback_list)],
    },
    fallbacks=[CommandHandler("cancelar", cancel_filtro)],
)


async def retrasado_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if get_user_status(update.effective_user.id) != "autorizado":
        await handle_unauthorized(update, context)
        return ConversationHandler.END
    distritos = get_unique_column_values("distrito", status="delayed")
    if not distritos:
        await update.message.reply_text(
            "¡Buenas noticias! No hay distritos con solicitudes retrasadas."
        )
        return ConversationHandler.END
    keyboard = [
        [InlineKeyboardButton(distrito, callback_data=distrito)]
        for distrito in distritos
    ]
    keyboard.insert(
        0, [InlineKeyboardButton("TODOS LOS DISTRITOS", callback_data="TODOS")]
    )
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "<b>Paso 1/3:</b> Selecciona un distrito para ver las solicitudes retrasadas:",
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML,
    )
    return RETRASO_SELECTING_DISTRITO


async def distrito_callback_retraso(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    query = update.callback_query
    await query.answer()
    distrito_seleccionado = query.data
    context.user_data["distrito_filtro_retraso"] = distrito_seleccionado
    gerencias = get_unique_column_values(
        "gerencia", distrito=distrito_seleccionado, status="delayed"
    )
    if not gerencias:
        await query.edit_message_text(
            "No hay gerencias con solicitudes retrasadas para este distrito."
        )
        context.user_data.clear()
        return ConversationHandler.END
    keyboard = [[InlineKeyboardButton(g, callback_data=g)] for g in gerencias]
    keyboard.insert(
        0, [InlineKeyboardButton("TODAS LAS GERENCIAS", callback_data="TODOS")]
    )
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        f"<b>Paso 2/3:</b> Distrito: <i>{distrito_seleccionado}</i>.\nAhora, selecciona una gerencia:",
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML,
    )
    return RETRASO_SELECTING_GERENCIA


async def gerencia_callback_retraso(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    query = update.callback_query
    await query.answer()
    gerencia_seleccionada = query.data
    context.user_data["gerencia_filtro_retraso"] = gerencia_seleccionada
    distrito_seleccionado = context.user_data.get("distrito_filtro_retraso", "TODOS")
    servicios = get_unique_column_values(
        "servicio",
        distrito=distrito_seleccionado,
        gerencia=gerencia_seleccionada,
        status="delayed",
    )
    if not servicios:
        await query.edit_message_text(
            "No hay servicios con solicitudes retrasadas para esta selección."
        )
        context.user_data.clear()
        return ConversationHandler.END
    keyboard = [[InlineKeyboardButton(s, callback_data=s)] for s in servicios]
    keyboard.insert(
        0, [InlineKeyboardButton("TODOS LOS SERVICIOS", callback_data="TODOS")]
    )
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        f"<b>Paso 3/3:</b> Gerencia: <i>{gerencia_seleccionada}</i>.\nAhora, selecciona un servicio:",
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML,
    )
    return RETRASO_SELECTING_SERVICIO


async def servicio_callback_retraso(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    query = update.callback_query
    await query.answer()
    servicio_seleccionado = query.data
    distrito_seleccionado = context.user_data.get("distrito_filtro_retraso", "TODOS")
    gerencia_seleccionada = context.user_data.get("gerencia_filtro_retraso", "TODOS")

    await query.edit_message_text(
        f"Buscando solicitudes retrasadas para:\n<b>Distrito:</b> {distrito_seleccionado}\n<b>Gerencia:</b> {gerencia_seleccionada}\n<b>Servicio:</b> {servicio_seleccionado}",
        parse_mode=ParseMode.HTML,
    )

    solicitudes = get_delayed_solicitudes(
        distrito=distrito_seleccionado,
        gerencia=gerencia_seleccionada,
        servicio=servicio_seleccionado,
    )

    if not solicitudes:
        await query.message.reply_text(
            "¡Buenas noticias! No se encontraron solicitudes retrasadas con los filtros seleccionados."
        )
        context.user_data.clear()
        return ConversationHandler.END

    retrasados_por_gerencia = {}
    for sol in solicitudes:
        g = sol.get("gerencia", "Sin Gerencia")
        if g not in retrasados_por_gerencia:
            retrasados_por_gerencia[g] = []
        retrasados_por_gerencia[g].append(sol)

    final_message = "<b>PLAZOS VENCIDOS DENTRO DEL PLAN DE CONTRATACIONES Y PROYECTOS DE INVERSIÓN</b>\n\n"

    for gerencia, solicitudes_gerencia in retrasados_por_gerencia.items():
        final_message += "----------------------------------------\n"
        final_message += f"<b>Gerencia:</b> {html.escape(gerencia)}\n\n"
        for solicitud in solicitudes_gerencia:
            nombre_hito = HITO_NOMBRES_LARGOS.get(
                solicitud["hito_actual"], solicitud["hito_actual"]
            )
            final_message += f"<b>Responsable:</b>\n"
            final_message += f"<b>Fase:</b> {html.escape(nombre_hito)}\n"
            # CORRECCIÓN: Se añade la fecha límite al reporte
            final_message += f"<b>Fecha Límite:</b> {format_date_for_display(solicitud['fecha_planificada'])}\n"
            final_message += f"🔴 <b>Solicitud (ID {solicitud['id']}):</b> {html.escape(solicitud['solicitud_contratacion'])}\n\n"

    chunk_size = 4096
    for i in range(0, len(final_message), chunk_size):
        await query.message.reply_text(
            final_message[i : i + chunk_size], parse_mode=ParseMode.HTML
        )

    context.user_data.clear()
    return ConversationHandler.END


retrasado_handler = ConversationHandler(
    entry_points=[CommandHandler("retrasado", retrasado_start)],
    states={
        RETRASO_SELECTING_DISTRITO: [CallbackQueryHandler(distrito_callback_retraso)],
        RETRASO_SELECTING_GERENCIA: [CallbackQueryHandler(gerencia_callback_retraso)],
        RETRASO_SELECTING_SERVICIO: [CallbackQueryHandler(servicio_callback_retraso)],
    },
    fallbacks=[CommandHandler("cancelar", cancel_filtro)],
)


async def reporte_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if get_user_role(update.effective_user.id) != "admin":
        await update.message.reply_text("No tienes permiso para ejecutar este comando.")
        return ConversationHandler.END

    distritos = get_unique_column_values("distrito")
    if not distritos:
        await update.message.reply_text(
            "No hay distritos disponibles para generar el reporte."
        )
        return ConversationHandler.END

    keyboard = [
        [InlineKeyboardButton(distrito, callback_data=distrito)]
        for distrito in distritos
    ]
    keyboard.insert(
        0, [InlineKeyboardButton("TODOS LOS DISTRITOS", callback_data="TODOS")]
    )
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "<b>Reporte - Paso 1/3:</b> Selecciona un distrito:",
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML,
    )
    return REPORTE_SELECTING_DISTRITO


async def distrito_callback_reporte(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    query = update.callback_query
    await query.answer()
    distrito = query.data
    context.user_data["reporte_distrito"] = distrito

    gerencias = get_unique_column_values("gerencia", distrito=distrito)
    if not gerencias:
        await query.edit_message_text(
            "No hay gerencias disponibles para este distrito."
        )
        return ConversationHandler.END

    keyboard = [[InlineKeyboardButton(g, callback_data=g)] for g in gerencias]
    keyboard.insert(
        0, [InlineKeyboardButton("TODAS LAS GERENCIAS", callback_data="TODOS")]
    )
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        f"<b>Reporte - Paso 2/3:</b> Selecciona una gerencia:",
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML,
    )
    return REPORTE_SELECTING_GERENCIA


async def gerencia_callback_reporte(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    query = update.callback_query
    await query.answer()
    gerencia = query.data
    context.user_data["reporte_gerencia"] = gerencia
    distrito = context.user_data["reporte_distrito"]

    servicios = get_unique_column_values(
        "servicio", distrito=distrito, gerencia=gerencia
    )
    if not servicios:
        await query.edit_message_text(
            "No hay servicios disponibles para esta selección."
        )
        return ConversationHandler.END

    keyboard = [[InlineKeyboardButton(s, callback_data=s)] for s in servicios]
    keyboard.insert(
        0, [InlineKeyboardButton("TODOS LOS SERVICIOS", callback_data="TODOS")]
    )
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        f"<b>Reporte - Paso 3/3:</b> Selecciona un servicio:",
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML,
    )
    return REPORTE_SELECTING_SERVICIO


async def servicio_callback_reporte(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    query = update.callback_query
    await query.answer()
    servicio = query.data
    distrito = context.user_data.get("reporte_distrito", "TODOS")
    gerencia_filtro = context.user_data.get("reporte_gerencia", "TODOS")

    await query.edit_message_text("Generando reporte...")

    solicitudes = get_solicitudes_for_balance(
        distrito=distrito, gerencia=gerencia_filtro, servicio=servicio
    )

    # Agrupar solicitudes por gerencia
    reporte_por_gerencia = {}
    for sol in solicitudes:
        g = sol.get("gerencia")
        if g:
            if g not in reporte_por_gerencia:
                reporte_por_gerencia[g] = []
            reporte_por_gerencia[g].append(sol)

    if not reporte_por_gerencia:
        await query.edit_message_text(
            "No se encontraron solicitudes activas con los filtros seleccionados."
        )
        return ConversationHandler.END

    # Construir el mensaje final
    final_message = "<b>PLAZOS CUMPLIDOS DENTRO DEL PLAN DE CONTRATACIONES Y PROYECTOS DE INVERSIÓN</b>\n\n"

    for gerencia, solicitudes_gerencia in reporte_por_gerencia.items():
        total, atrasadas, proximas, al_dia = calculate_balance(solicitudes_gerencia)

        min_future_date = None
        hoy = datetime.now().date()
        for sol in solicitudes_gerencia:
            fecha_plan_str = sol.get("fecha_planificada")
            if fecha_plan_str:
                fecha_plan = datetime.strptime(fecha_plan_str, "%Y-%m-%d").date()
                if fecha_plan >= hoy:
                    if min_future_date is None or fecha_plan < min_future_date:
                        min_future_date = fecha_plan

        if min_future_date:
            nombre_dia = get_weekday_in_spanish(min_future_date)
            fecha_formateada = min_future_date.strftime("%d/%m/%Y")
            fecha_reporte = f"Fecha: {nombre_dia}, {fecha_formateada}"
        else:
            fecha_reporte = "Fecha: No hay hitos próximos"

        final_message += "----------------------------------------\n"
        final_message += f"{fecha_reporte}\n"
        final_message += f"<b>Gerencia:</b> {gerencia}\n\n"
        final_message += f"Total de Solicitudes en Proceso: <b>{total}</b>\n"
        final_message += f"🟢 A tiempo: <b>{al_dia}</b>\n"
        final_message += f"🔴 Retrasadas: <b>{atrasadas}</b>\n"

    await query.edit_message_text(final_message, parse_mode=ParseMode.HTML)
    context.user_data.clear()
    return ConversationHandler.END


reporte_handler = ConversationHandler(
    entry_points=[CommandHandler("reporte", reporte_start)],
    states={
        REPORTE_SELECTING_DISTRITO: [CallbackQueryHandler(distrito_callback_reporte)],
        REPORTE_SELECTING_GERENCIA: [CallbackQueryHandler(gerencia_callback_reporte)],
        REPORTE_SELECTING_SERVICIO: [CallbackQueryHandler(servicio_callback_reporte)],
    },
    fallbacks=[CommandHandler("cancelar", cancel_filtro)],
)
