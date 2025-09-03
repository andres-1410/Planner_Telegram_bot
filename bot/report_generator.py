# bot/report_generator.py
# Lógica para generar el reporte imprimible en HTML.

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
    """Genera un archivo HTML con formato de lista vertical imprimible."""

    # Estilos CSS para el formato de lista vertical
    styles = """
    <style>
        body { 
            font-family: Arial, sans-serif; 
            margin: 20px; 
            background-color: #f4f4f9; 
        }
        .page-title { 
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
            page-break-inside: avoid; /* Evita que la tarjeta se corte al imprimir */
        }
        .card-header { 
            border-bottom: 1px solid #eee; 
            padding-bottom: 10px; 
            margin-bottom: 10px;
        }
        .card-title { 
            font-size: 18px; 
            font-weight: bold; 
            color: #0056b3; 
        }
        .gerencia-block { 
            margin-top: 15px; 
            border-top: 1px dashed #ccc;
            padding-top: 15px;
        }
        .gerencia-block:first-child {
            border-top: none;
            margin-top: 0;
            padding-top: 0;
        }
        .gerencia-title { 
            font-weight: bold; 
            font-size: 16px; 
            color: #333; 
        }
        .task { 
            margin-top: 10px; 
            padding-left: 15px; 
            border-left: 3px solid #0056b3; 
        }
        .task p { 
            margin: 4px 0; 
            font-size: 14px;
        }
        
        @media print {
            body { margin: 1cm; background-color: white; }
            .page-title { display: none; }
            .card { box-shadow: none; border: 1px solid #aaa; }
        }
    </style>
    """

    # Construcción del cuerpo del HTML con la corrección de codificación
    body_html = f'<html><head><meta charset="UTF-8"><title>Reporte de Planificación</title>{styles}</head><body>'

    # Ordenar fechas
    for fecha_str in sorted(report_data.keys()):
        fecha_obj = datetime.strptime(fecha_str, "%Y-%m-%d").date()
        nombre_dia = get_weekday_in_spanish(fecha_obj)
        fecha_display = fecha_obj.strftime("%d/%m/%Y")

        body_html += '<h1 class="page-title">PLAZOS CUMPLIDOS DENTRO DEL PLAN DE CONTRATACIONES Y PROYECTOS DE INVERSIÓN</h1>'
        body_html += '<div class="card">'
        body_html += '<div class="card-header">'
        body_html += f'<h2 class="card-title">Fecha de Vencimiento: {nombre_dia}, {fecha_display}</h2>'
        body_html += "</div>"

        # Agrupar por gerencia
        for gerencia_resp, tareas in report_data[fecha_str].items():
            body_html += '<div class="gerencia-block">'
            body_html += f'<h3 class="gerencia-title">Gerencia Responsable: {html.escape(gerencia_resp)}</h3>'
            for tarea in tareas:
                body_html += '<div class="task">'
                body_html += f"<p><b>Fase:</b> {html.escape(tarea['nombre_hito'])}</p>"
                body_html += (
                    f"<p><b>Tarea a Cumplir:</b> {html.escape(tarea['tarea'])}</p>"
                )
                body_html += f"<p><b>Solicitud (ID {tarea['id']}):</b> {html.escape(tarea['nombre_solicitud'])}</p>"
                body_html += "</div>"
                body_html += "<br>"
            body_html += "</div>"

        body_html += "</div>"  # Cierre de la tarjeta

    body_html += "</body></html>"

    try:
        with open("reporte_imprimible.html", "w", encoding="utf-8") as f:
            f.write(body_html)
        return True
    except Exception:
        return False
