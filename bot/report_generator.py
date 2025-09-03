# bot/report_generator.py
# Lógica para generar el reporte imprimible en HTML, corregido para compatibilidad con Firefox.

import html
from datetime import datetime


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


def generate_printable_report_html(report_data):
    """
    Genera un archivo HTML con una estructura dual: una para la vista en pantalla
    y otra optimizada para impresión (con encabezados repetidos en cada página)
    que es compatible con Firefox y otros navegadores.
    """

    # --- INICIO DE CAMBIOS ---
    # CSS completamente reescrito para manejar la estructura dual (pantalla vs. impresión)
    styles = """
    <style>
        /* --- ESTILOS GENERALES PARA LA PANTALLA --- */
        body { 
            font-family: Arial, sans-serif; 
            margin: 20px; 
            background-color: #f4f4f9; 
        }

        /* 1. Ocultamos la estructura de tabla (solo para imprimir) en la vista de pantalla */
        #reporte-impresion {
            display: none;
        }

        /* Estilos normales para la vista en pantalla (no se cambian) */
        #vista-pantalla .page-title { 
            text-align: justify; 
            color: #333; 
            font-size: 24px; 
            margin-bottom: 20px;
        }
        .card { 
            background-color: white; 
            border: 1px solid #ddd; 
            border-radius: 8px; 
            padding: 15px; 
            margin-bottom: 20px; 
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .card-header { border-bottom: 1px solid #eee; padding-bottom: 10px; margin-bottom: 10px; }
        .card-title { font-size: 18px; font-weight: bold; color: #0056b3; }
        .gerencia-block { margin-top: 15px; border-top: 1px dashed #ccc; padding-top: 15px; }
        .gerencia-block:first-child { border-top: none; margin-top: 0; padding-top: 0; }
        .gerencia-title { font-weight: bold; font-size: 16px; color: #333; }
        .task { margin-top: 10px; padding-left: 15px; border-left: 3px solid #0056b3; }
        .task p { margin: 4px 0; font-size: 14px; }


        /* --- ESTILOS SOLO PARA IMPRIMIR / PDF --- */
        @media print {
            body { 
                margin: 0;
                padding: 0;
                background-color: white;
            }

            /* Ocultamos la vista de pantalla y mostramos la de impresión */
            #vista-pantalla {
                display: none;
            }
            #reporte-impresion {
                display: table; /* Hacemos visible la tabla */
                width: 100%;
                border-collapse: collapse;
            }
            
            /* 2. El navegador repetirá este thead en cada página automáticamente */
            #encabezado-impresion {
                display: table-header-group; /* Asegura que el navegador lo trate como un encabezado repetible */
            }

            #encabezado-impresion h1 {
                font-size: 16px; /* Tamaño del título en la impresión */
                text-align: center;
                color: #333;
                margin: 0;
                padding: 1cm; /* Espacio interno del encabezado */
                border-bottom: 1px solid #ccc;
            }

            #cuerpo-reporte {
                 padding: 1.5cm; /* Márgenes de la página para el contenido */
            }

            .card { 
                box-shadow: none; 
                border: 1px solid #aaa;
                page-break-inside: avoid; /* Evita que las tarjetas se corten entre páginas */
            }
            
            /* 3. REDUCIMOS EL TAMAÑO DE LAS FUENTES PARA AHORRAR HOJAS */
            .card, .task p, .gerencia-title {
                font-size: 11px !important; /* Letra más pequeña para el contenido */
            }
            .card-title {
                font-size: 13px !important; /* Letra un poco más grande para los títulos de las tarjetas */
            }
        }
    </style>
    """

    # Construcción del encabezado del HTML
    html_head = f'<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Reporte de Planificación</title>{styles}</head><body>'

    # Se inicializan dos strings vacíos para construir el contenido de ambas vistas por separado.
    screen_html_content = ""
    print_html_cards = ""

    # Título del reporte
    report_title = (
        "PLAZOS CUMPLIDOS DENTRO DEL PLAN DE CONTRATACIONES Y PROYECTOS DE INVERSIÓN"
    )

    # Se itera una sola vez sobre los datos para construir el contenido de las tarjetas
    for fecha_str in sorted(report_data.keys()):
        fecha_obj = datetime.strptime(fecha_str, "%Y-%m-%d").date()
        nombre_dia = get_weekday_in_spanish(fecha_obj)
        fecha_display = fecha_obj.strftime("%d/%m/%Y")

        # Construye el contenido de una tarjeta (sin el div.card exterior)
        card_inner_html = '<div class="card-header">'
        card_inner_html += f'<h2 class="card-title">Fecha de Vencimiento: {nombre_dia}, {fecha_display}</h2>'
        card_inner_html += "</div>"

        for gerencia_resp, tareas in report_data[fecha_str].items():
            card_inner_html += '<div class="gerencia-block">'
            card_inner_html += f'<h3 class="gerencia-title">Gerencia Responsable: {html.escape(gerencia_resp)}</h3>'
            for tarea in tareas:
                card_inner_html += '<div class="task">'
                card_inner_html += (
                    f"<p><b>Fase:</b> {html.escape(tarea['nombre_hito'])}</p>"
                )
                card_inner_html += (
                    f"<p><b>Tarea a Cumplir:</b> {html.escape(tarea['tarea'])}</p>"
                )
                card_inner_html += f"<p><b>Solicitud (ID {tarea['id']}):</b> {html.escape(tarea['nombre_solicitud'])}</p>"
                card_inner_html += "</div><br>"
            card_inner_html += "</div>"

        # Para la vista de pantalla, se añade el título repetitivo y la tarjeta.
        screen_html_content += f'<h1 class="page-title">{report_title}</h1>'
        screen_html_content += f'<div class="card">{card_inner_html}</div>'

        # Para la vista de impresión, solo se añade la tarjeta.
        print_html_cards += f'<div class="card">{card_inner_html}</div>'

    # Se ensambla la estructura final del HTML
    body_html = (
        f"{html_head}"
        # 1. Estructura para la impresión (basada en tabla)
        '<table id="reporte-impresion">'
        '<thead id="encabezado-impresion">'
        "<tr>"
        f"<td><h1>{report_title}</h1></td>"
        "</tr>"
        "</thead>"
        '<tbody id="cuerpo-reporte">'
        "<tr>"
        f"<td>{print_html_cards}</td>"
        "</tr>"
        "</tbody>"
        "</table>"
        # 2. Estructura para la vista en pantalla (la original)
        f'<div id="vista-pantalla">{screen_html_content}</div>'
        "</body></html>"
    )
    # --- FIN DE CAMBIOS ---

    try:
        with open("reporte_imprimible.html", "w", encoding="utf-8") as f:
            f.write(body_html)
        return True
    except Exception as e:
        print(f"Error al generar el reporte: {e}")  # Añadido para mejor depuración
        return False
