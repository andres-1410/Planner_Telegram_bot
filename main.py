# main.py
# Punto de entrada principal para iniciar el bot.

import logging
from telegram.ext import Application, CommandHandler, MessageHandler, filters

from bot.config import TELEGRAM_TOKEN, logger
from bot.handlers import (
    start_command,
    help_command,
    handle_unauthorized,
    cargar_excel_local,
    configurar_dias_command,
    configurar_hora_command,
    autorizar_command,
    listar_usuarios_command,
    ver_solicitud_command,
    replanificar_command,
    completar_command,
    balance_command,
    hoy_command,
    sincerar_datos_command,
    balance_filtro_handler,
    listar_solicitudes_handler,
    retrasado_handler,
    reporte_handler,
    # --- NUEVO HANDLER ---
    unidad_usuaria_handler,
)
from bot.scheduler import post_init


def main() -> None:
    """Inicia el bot y lo mantiene en ejecución."""
    if not TELEGRAM_TOKEN:
        logger.error(
            "No se encontró el TELEGRAM_TOKEN. Asegúrate de que tu archivo .env es correcto."
        )
        return

    application = (
        Application.builder().token(TELEGRAM_TOKEN).post_init(post_init).build()
    )

    # Registrar handlers de comandos
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("cargar_excel", cargar_excel_local))
    application.add_handler(CommandHandler("configurar_dias", configurar_dias_command))
    application.add_handler(CommandHandler("configurar_hora", configurar_hora_command))
    application.add_handler(CommandHandler("autorizar", autorizar_command))
    application.add_handler(CommandHandler("listar_usuarios", listar_usuarios_command))
    application.add_handler(CommandHandler("ver_solicitud", ver_solicitud_command))
    application.add_handler(CommandHandler("replanificar", replanificar_command))
    application.add_handler(CommandHandler("completar", completar_command))
    application.add_handler(CommandHandler("balance", balance_command))
    application.add_handler(CommandHandler("hoy", hoy_command))
    application.add_handler(CommandHandler("sincerar_datos", sincerar_datos_command))
    # Handlers de Conversación
    application.add_handler(balance_filtro_handler)
    application.add_handler(listar_solicitudes_handler)
    application.add_handler(retrasado_handler)
    application.add_handler(reporte_handler)
    # --- NUEVO HANDLER ---
    application.add_handler(unidad_usuaria_handler)

    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_unauthorized)
    )

    logger.info("Iniciando el bot...")
    application.run_polling()


if __name__ == "__main__":
    main()
