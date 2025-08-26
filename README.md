Bot de Alertas de Contratación para Telegram

Este es un bot de Telegram desarrollado en Python para gestionar, monitorear y notificar sobre las diferentes fases de los procesos de contratación de una empresa. El bot utiliza un archivo Excel como fuente de datos inicial y gestiona un flujo de trabajo basado en hitos, notificando a los usuarios autorizados sobre los próximos vencimientos.
Características Principales

    Gestión de Estado por Hitos: El bot entiende la secuencia de los procesos de contratación y monitorea siempre el próximo hito pendiente.

    Notificaciones Automáticas: Envía alertas diarias a los usuarios sobre los hitos que están por vencer, con días de antelación y hora configurables.

    Sistema de Roles: Administra diferentes niveles de acceso para los usuarios (admin, contrataciones, notificado).

    Consultas Dinámicas: Permite a los usuarios consultar el estado detallado de cualquier solicitud, mostrando si está a tiempo, próxima a vencer o retrasada.

    Reportes y Balances: Ofrece resúmenes generales y filtrados (por distrito y servicio) del estado de todas las solicitudes activas.

    Gestión Interactiva: Los usuarios del equipo de contrataciones pueden marcar hitos como completados o replanificar fechas directamente desde el chat, con una lógica de ajuste en cascada para fechas futuras.

    Carga de Datos Controlada: El administrador carga la información desde un archivo Excel local, manteniendo la seguridad de los datos.

Estructura del Proyecto

/PLANNER/
├── bot/
│   ├── __init__.py
│   ├── config.py           # Configuración y constantes
│   ├── database.py         # Lógica de la base de datos
│   ├── handlers.py         # Comandos y manejadores de mensajes
│   └── scheduler.py        # Lógica de notificaciones
│
├── CRONOGRAMA DE CONTRATACIÓN.xlsx
├── database_setup.py       # Script para crear la base de datos
├── .env                    # Archivo para guardar el token del bot
├── requirements.txt
└── main.py                 # Punto de entrada para iniciar el bot

Instalación y Puesta en Marcha

Sigue estos pasos para poner en funcionamiento el bot.
1. Prerrequisitos

    Python 3.9 o superior.

    Una cuenta de Telegram y un token de bot obtenido de @BotFather.

2. Clonar el Repositorio

git clone <URL_DEL_REPOSITORIO>
cd PLANNER

3. Crear un Entorno Virtual

python -m venv env
source env/bin/activate  # En Windows: env\Scripts\activate

4. Instalar Dependencias

pip install -r requirements.txt

5. Configurar el Token

Crea un archivo llamado .env en la raíz del proyecto y añade tu token de Telegram:

TELEGRAM_TOKEN=AQUI_VA_TU_TOKEN_SECRETO

6. Preparar el Archivo de Datos

Asegúrate de que tu archivo CRONOGRAMA DE CONTRATACIÓN.xlsx esté en la raíz del proyecto y que los encabezados de las columnas coincidan con los esperados por el bot.
7. Crear la Base de Datos

Ejecuta este comando una sola vez para crear el archivo bot_database.db con la estructura necesaria:

python database_setup.py

Uso
Iniciar el Bot

Para poner el bot en línea, ejecuta:

python main.py

La primera persona que envíe el comando /start será designada automáticamente como el administrador principal.
Comandos Disponibles

El bot responde a una serie de comandos para gestionar y consultar la información. Usa el comando /help dentro del bot para ver la lista completa y actualizada.