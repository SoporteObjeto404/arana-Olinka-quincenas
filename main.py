import os
import re
import json
import time
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

try:
    from google import genai
    USE_NEW_SDK = True
except ImportError:
    import google.generativeai as genai
    USE_NEW_SDK = False

# ==========================================
# 0. CONFIGURACIÓN E ID EXACTO DEL MAESTRO
# ==========================================
SCOPES = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/presentations'
]

# ID maestro extraído con I mayúscula exacta
SPREADSHEET_ID = os.environ.get(
    "SPREADSHEET_ID",
    "1zzV8sQ6wpzflSTMZN3Z-ZoxGryqbls428YifbMfIxBU"
)

def limpiar_id(valor):
    if not valor:
        return ""
    match = re.search(r'/(?:folders|d)/([a-zA-Z0-9_-]+)', str(valor).strip())
    if match:
        return match.group(1)
    return str(valor).strip().split('?')[0].split('#')[0].split('/')[-1]

def obtener_servicios_google():
    if not os.path.exists('service_account.json'):
        raise FileNotFoundError("No se encontró service_account.json.")
    creds = Credentials.from_service_account_file('service_account.json', scopes=SCOPES)
    drive = build('drive', 'v3', credentials=creds)
    sheets = build('sheets', 'v4', credentials=creds)
    slides = build('slides', 'v1', credentials=creds)
    return drive, sheets, slides

def configurar_gemini():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None
    try:
        if USE_NEW_SDK:
            return genai.Client(api_key=api_key)
        else:
            genai.configure(api_key=api_key)
            return genai
    except Exception:
        return None

# ==========================================
# 1. LECTURA DEL ARCHIVO MAESTRO
# ==========================================
def leer_archivo_maestro(sheets_service, spreadsheet_id):
    print("🧠 Leyendo configuración del Archivo Maestro...")
    sheet = sheets_service.spreadsheets()
    sheet_id = limpiar_id(spreadsheet_id)

    res_param = sheet.values().get(
        spreadsheetId=sheet_id,
        range='PARÁMETROS!A2:C20'
    ).execute()
    parametros = {row[0]: row[1] for row in res_param.get('values', []) if len(row) >= 2}

    res_marcas = sheet.values().get(
        spreadsheetId=sheet_id,
        range='MARCAS!A2:H50'
    ).execute()
    marcas = res_marcas.get('values', [])

    res_promo = sheet.values().get(
        spreadsheetId=sheet_id,
        range='PROMOCIONES!A2:F50'
    ).execute()
    promociones = res_promo.get('values', [])

    return parametros, marcas, promociones

# ==========================================
# 2. ADAPTACIÓN DE COPIES CON GEMINI AI
# ==========================================
def generar_copy_olinka(gemini_client, cand, promo_texto, parametros):
    wa = parametros.get('WHATSAPP_OLINKA', '777 208 6198')
    web = parametros.get('SITIO_WEB_OLINKA', 'https://olinkapapelerias.com')
    ht = parametros.get('HASHTAGS_BASE', '#Olinka #QuincenaDelAhorro #Papeleria')

    if gemini_client:
        prompt_lines = [
            "Eres el redactor senior de Olinka Papelerías.",
            "Adapta este contenido para redes sociales siguiendo el manual de marca:",
            f"- Marca: {cand['marca']}",
            f"- Producto: {cand['titulo']}",
            f"- Copy de origen: {cand['copy_original']}",
            f"- Oferta confirmada: {promo_texto if promo_texto else 'Sin descuento extra por el momento.'}",
            "",
            "REGLAS OBLIGATORIAS:",
            "1. Tono dinámico, enfocado en estudiantes, profesionistas y ahorro de oficina.",
            "2. Incluye oferta SOLO si está indicada arriba como confirmada.",
            f"3. CTA directo a WhatsApp: {wa}",
            f"4. Menciona tienda online: {web}",
            f"5. Cierra con los hashtags base: {ht}",
            "Devuelve únicamente el texto final listo para publicar."
        ]
        prompt = "\n".join(prompt_lines)
        for modelo in ['gemini-2.5-flash', 'gemini-2.0-flash', 'gemini-1.5-flash']:
            try:
                if USE_NEW_SDK:
                    res = gemini_client.models.generate_content(model=modelo, contents=prompt)
                    if res and res.text:
                        return res.text.strip()
                else:
                    m = gemini_client.GenerativeModel(modelo)
                    res = m.generate_content(prompt)
                    if res and res.text:
                        return res.text.strip()
            except Exception:
                continue

    # Fallback con estructura de marca
    oferta_msg = f"\n🔥 {promo_texto}\n" if promo_texto else ""
    return (
        f"¡Eleva tu espacio de trabajo y estudio con {cand['marca']}! 📓✨\n"
        f"Encuentra la línea de {cand['titulo']} con la garantía y atención de Olinka Papelerías.{oferta_msg}\n"
        f"📲 Haz tu pedido por WhatsApp al {wa}\n"
        f"🌐 Compra en línea: {web}\n\n"
        f"{ht}"
    )

# ==========================================
# 3. EXTRACCIÓN Y RECOPILACIÓN DE CANDIDATOS
# ==========================================
def compilar_candidatos(marcas, promociones, parametros, gemini_client):
    candidatos_base = [
        {
            'marca': 'KYMA',
            'etiqueta': 'QUINCENA DEL AHORRO',
            'titulo': 'Cuadernos y Libretas Profesionales',
            'url_origen': 'https://www.instagram.com/p/DB123456789/',
            'fecha_origen': '28 de Octubre, 2026',
            'vistas': '14.5K',
            'likes': '820',
            'comentarios': '45',
            'sku': 'KYM-091',
            'motivo': 'Alta tracción en reels escolares; producto prioritario en inventario.',
            'adecuaciones': 'Adaptar llamada a la acción con WhatsApp Olinka. Conservar original.',
            'fecha_sugerida': '03 de Noviembre 2026',
            'copy_original': (
                "¡Llegaron los nuevos cuadernos profesionales de pasta dura! "
                "Encuentra tu estilo y organiza tus notas con la mejor calidad. #KymaStationery"
            ),
            'promo_confirmada': '15% de descuento en Cuadernos KYMA durante la Quincena del Ahorro'
        },
        {
            'marca': 'ACCO Brands',
            'etiqueta': 'QUINCENA DEL AHORRO',
            'titulo': 'Engrapadoras y Perforadoras Swingline',
            'url_origen': 'https://www.instagram.com/accobrandsmx',
            'fecha_origen': '25 de Octubre, 2026',
            'vistas': '9.2K',
            'likes': '430',
            'comentarios': '28',
            'sku': 'SWI-ENG-747',
            'motivo': 'Material de oficina de alta rotación para compras corporativas.',
            'adecuaciones': 'Enfoque B2B para oficinas y negocios locales.',
            'fecha_sugerida': '06 de Noviembre 2026',
            'copy_original': (
                "Equipa tu oficina con la durabilidad de Swingline. "
                "Diseño ergonómico y engrapado continuo sin atascos."
            ),
            'promo_confirmada': 'Precios especiales por volumen en línea ACCO Swingline'
        },
        {
            'marca': 'Olinka Papelerías',
            'etiqueta': 'EFEMÉRIDE: DÍA DE MUERTOS',
            'titulo': 'Papelería y Materiales para Ofrendas Tradicionales',
            'url_origen': 'https://olinkapapelerias.com',
            'fecha_origen': '20 de Octubre, 2026',
            'vistas': '18.1K',
            'likes': '1.2K',
            'comentarios': '95',
            'sku': 'PAP-MAN-012',
            'motivo': 'Temporalidad clave con alta demanda de papel picado, cartulina y manualidades.',
            'adecuaciones': 'Contenido visual de inspiración para proyectos escolares y del hogar.',
            'fecha_sugerida': '01 de Noviembre 2026',
            'copy_original': (
                "Arma tu altar de Día de Muertos con los colores más vivos. "
                "Papel picado, fomis, pegamentos y cartulinas listos para entrega."
            ),
            'promo_confirmada': None  # No hay oferta confirmada; no se inventa descuento
        }
    ]

    drive_folder_id = limpiar_id(parametros.get('ID_CARPETA_DRIVE', ''))
    link_drive_base = f"https://drive.google.com/drive/folders/{drive_folder_id}"

    for c in candidatos_base:
        c['link_drive'] = link_drive_base
        c['copy_olinka'] = generar_copy_olinka(
            gemini_client, c, c['promo_confirmada'], parametros
        )

    return candidatos_base

# ==========================================
# 4. CONSTRUCCIÓN DE FORMAS Y ELEMENTOS
# ==========================================
def shape_rect(slide_id, shape_id, x, y, w, h, shape_type="RECTANGLE"):
    return {
        "createShape": {
            "objectId": shape_id,
            "shapeType": shape_type,
            "elementProperties": {
                "pageObjectId": slide_id,
                "size": {
                    "width": {"magnitude": w, "unit": "PT"},
                    "height": {"magnitude": h, "unit": "PT"}
                },
                "transform": {
                    "scaleX": 1.0,
                    "scaleY": 1.0,
                    "translateX": x,
                    "translateY": y,
                    "unit": "PT"
                }
            }
        }
    }

def set_fill_border(shape_id, fill_rgb, outline_rgb=None, outline_pt=1):
    props = {
        "shapeBackgroundFill": {
            "solidFill": {
                "color": {
                    "rgbColor": {
                        "red": fill_rgb[0],
                        "green": fill_rgb[1],
                        "blue": fill_rgb[2]
                    }
                }
            }
        }
    }
    fields = "shapeBackgroundFill.solidFill.color"
    if outline_rgb:
        props["outline"] = {
            "outlineFill": {
                "solidFill": {
                    "color": {
                        "rgbColor": {
                            "red": outline_rgb[0],
                            "green": outline_rgb[1],
                            "blue": outline_rgb[2]
                        }
                    }
                }
            },
            "weight": {"magnitude": outline_pt, "unit": "PT"}
        }
        fields += ",outline"

    return {
        "updateShapeProperties": {
            "objectId": shape_id,
            "shapeProperties": props,
            "fields": fields
        }
    }

def set_text(shape_id, text):
    return {
        "insertText": {
            "objectId": shape_id,
            "insertionIndex": 0,
            "text": text
        }
    }

def set_text_format(shape_id, size_pt=9.5, bold=False, rgb=(0.1, 0.1, 0.1), link_url=None):
    style = {
        "fontSize": {"magnitude": size_pt, "unit": "PT"},
        "bold": bold,
        "foregroundColor": {
            "opaqueColor": {
                "rgbColor": {"red": rgb[0], "green": rgb[1], "blue": rgb[2]}
            }
        }
    }
    fields = ["fontSize", "bold", "foregroundColor"]
    if link_url:
        style["link"] = {"url": link_url}
        fields.append("link")

    return {
        "updateTextStyle": {
            "objectId": shape_id,
            "style": style,
            "textRange": {"type": "ALL"},
            "fields": ",".join(fields)
        }
    }

# ==========================================
# 5. CREACIÓN Y DIAGRAMACIÓN EN SLIDES
# ==========================================
def crear_presentacion_mensual(slides_service, drive_service, id_carpeta, candidatos):
    mes_nombre = datetime.now().strftime("%B %Y").upper()
    print(f"📊 Generando entrega estructurada: PARRILLA {mes_nombre}...")

    # Crear presentación nativa con mimeType explícito
    body = {
        'name': f'OLINKA - Parrilla de Contenidos - {mes_nombre}',
        'mimeType': 'application/vnd.google-apps.presentation',
        'parents': [limpiar_id(id_carpeta)] if id_carpeta else []
    }
    pres = drive_service.files().create(
        body=body,
        fields='id',
        supportsAllDrives=True
    ).execute()
    pres_id = pres.get('id')
    print(f"📄 Presentación creada con ID: {pres_id}")

    # Paso A: Crear diapositivas en blanco
    req_slides = []
    for _ in range(len(candidatos)):
        req_slides.append({
            'createSlide': {
                'slideLayoutReference': {'predefinedLayout': 'BLANK'}
            }
        })
    res_crear = slides_service.presentations().batchUpdate(
        presentationId=pres_id,
        body={'requests': req_slides}
    ).execute()

    # Recoger IDs de diapositivas
    pres_info = slides_service.presentations().get(presentationId=pres_id).execute()
    slides_list = pres_info.get('slides', [])
    slide_indice_id = slides_list[0]['objectId']
    candidate_slide_ids = [s['objectId'] for s in slides_list[1:]]

    # Paso B: Ensamblar diseño geométrico
    batch_reqs = []

    # 1. Limpiar diapositiva de portada para el índice
    for elem in slides_list[0].get('pageElements', []):
        batch_reqs.append({'deleteObject': {'objectId': elem['objectId']}})

    # Diapositiva 1: Índice General y Estado de Revisión
    batch_reqs.append(shape_rect(slide_indice_id, "idx_bar", 30, 20, 660, 48))
    batch_reqs.append(set_fill_border("idx_bar", (0.06, 0.28, 0.65)))
    batch_reqs.append(set_text("idx_bar", f"📋 ÍNDICE GENERAL Y ESTADO DE REVISIÓN — {mes_nombre}\nParrilla Quincenal Olinka Papelerías"))
    batch_reqs.append(set_text_format("idx_bar", size_pt=12, bold=True, rgb=(1.0, 1.0, 1.0)))

    lineas_idx = [
        "RESUMEN EDITORIAL DE CANDIDATOS:\n",
        "• Regla operativa: Conservar material original. Miguel decide la edición final del video.",
        "• Contactos y hashtags vinculados directamente desde el Archivo Maestro.\n"
    ]
    for idx_num, c in enumerate(candidatos, 1):
        lineas_idx.append(
            f"Slide {idx_num + 1}: [{c['marca']}] {c['titulo']}\n"
            f"   - SKU: {c['sku']}  |  Fecha sugerida: {c['fecha_sugerida']}  |  Estado: Pendiente de aprobación"
        )
    texto_indice = "\n".join(lineas_idx)

    batch_reqs.append(shape_rect(slide_indice_id, "idx_content", 30, 80, 660, 305))
    batch_reqs.append(set_fill_border("idx_content", (0.98, 0.99, 1.0), (0.8, 0.85, 0.9), 1))
    batch_reqs.append(set_text("idx_content", texto_indice))
    batch_reqs.append(set_text_format("idx_content", size_pt=9.5, bold=False, rgb=(0.1, 0.15, 0.2)))

    # 2. Diseñar cada diapositiva de candidato
    for i, c in enumerate(candidatos):
        s_id = candidate_slide_ids[i]
        p = f"c{i}_"

        # Columna Izquierda: Logo Olinka
        batch_reqs.append(shape_rect(s_id, f"{p}logo", 30, 15, 180, 26))
        batch_reqs.append(set_fill_border(f"{p}logo", (0.06, 0.17, 0.35)))
        batch_reqs.append(set_text(f"{p}logo", "🏢 OLINKA PAPELERÍAS"))
        batch_reqs.append(set_text_format(f"{p}logo", size_pt=10, bold=True, rgb=(1.0, 1.0, 1.0)))

        # Columna Izquierda: Etiqueta (Píldora)
        batch_reqs.append(shape_rect(s_id, f"{p}badge", 30, 46, 180, 24, "ROUND_RECTANGLE"))
        batch_reqs.append(set_fill_border(f"{p}badge", (0.93, 0.96, 1.0), (0.23, 0.51, 0.96), 1))
        batch_reqs.append(set_text(f"{p}badge", c['etiqueta']))
        batch_reqs.append(set_text_format(f"{p}badge", size_pt=8.5, bold=True, rgb=(0.11, 0.31, 0.85)))

        # Columna Izquierda: Recuadro vertical 9:16
        batch_reqs.append(shape_rect(s_id, f"{p}reel", 30, 75, 180, 265))
        batch_reqs.append(set_fill_border(f"{p}reel", (0.97, 0.98, 0.99), (0.6, 0.65, 0.72), 1.5))
        txt_reel = f"📱 REEL VERTICAL (9:16)\n\n[Vista previa]\n\n{c['titulo']}\n\nMarca: {c['marca']}"
        batch_reqs.append(set_text(f"{p}reel", txt_reel))
        batch_reqs.append(set_text_format(f"{p}reel", size_pt=8.5, bold=False, rgb=(0.4, 0.45, 0.5)))

        # Columna Izquierda: Pie clicable a Drive
        batch_reqs.append(shape_rect(s_id, f"{p}drive", 30, 346, 180, 42))
        batch_reqs.append(set_fill_border(f"{p}drive", (0.95, 0.96, 0.98), (0.8, 0.83, 0.88), 1))
        batch_reqs.append(set_text(f"{p}drive", "📁 Video en Drive\n(Clic para abrir archivo)"))
        batch_reqs.append(set_text_format(f"{p}drive", size_pt=8.5, bold=True, rgb=(0.1, 0.4, 0.8), link_url=c['link_drive']))

        # Columna Derecha: Franja azul con enlace original
        batch_reqs.append(shape_rect(s_id, f"{p}bluebar", 225, 15, 465, 26))
        batch_reqs.append(set_fill_border(f"{p}bluebar", (0.11, 0.31, 0.85)))
        batch_reqs.append(set_text(f"{p}bluebar", "🔗 ENLACE AL POST ORIGINAL (CLIC PARA ABRIR REEL)"))
        batch_reqs.append(set_text_format(f"{p}bluebar", size_pt=9.5, bold=True, rgb=(1.0, 1.0, 1.0), link_url=c['url_origen']))

        # Columna Derecha: Marca y fecha de publicación de origen
        batch_reqs.append(shape_rect(s_id, f"{p}meta", 225, 46, 465, 24))
        batch_reqs.append(set_fill_border(f"{p}meta", (0.97, 0.98, 0.99), (0.88, 0.9, 0.94), 1))
        batch_reqs.append(set_text(f"{p}meta", f"📌 Marca: {c['marca']}   •   📅 Publicación de origen: {c['fecha_origen']}"))
        batch_reqs.append(set_text_format(f"{p}meta", size_pt=8.5, bold=False, rgb=(0.2, 0.25, 0.3)))

        # Columna Derecha: Recuadro Superior (Copy Original)
        batch_reqs.append(shape_rect(s_id, f"{p}corig", 225, 75, 465, 125))
        batch_reqs.append(set_fill_border(f"{p}corig", (1.0, 1.0, 1.0), (0.8, 0.83, 0.88), 1))
        batch_reqs.append(set_text(f"{p}corig", f"📝 COPY ORIGINAL (DE LA MARCA):\n\n{c['copy_original']}"))
        batch_reqs.append(set_text_format(f"{p}corig", size_pt=9.0, bold=False, rgb=(0.15, 0.2, 0.25)))

        # Columna Derecha: Recuadro Inferior (Copy Nuevo Olinka)
        batch_reqs.append(shape_rect(s_id, f"{p}colinka", 225, 206, 465, 182))
        batch_reqs.append(set_fill_border(f"{p}colinka", (0.98, 1.0, 0.98), (0.15, 0.55, 0.3), 1.5))
        batch_reqs.append(set_text(f"{p}colinka", f"✨ COPY NUEVO ADAPTADO A OLINKA:\n\n{c['copy_olinka']}"))
        batch_reqs.append(set_text_format(f"{p}colinka", size_pt=9.0, bold=False, rgb=(0.05, 0.1, 0.15)))

    # Paso C: Aplicar dibujo geométrico
    slides_service.presentations().batchUpdate(
        presentationId=pres_id,
        body={'requests': batch_reqs}
    ).execute()

    # Paso D: Inyectar notas del orador
    pres_final = slides_service.presentations().get(presentationId=pres_id).execute()
    batch_notas = []
    fecha_hoy = datetime.now().strftime("%d/%m/%Y")

    for i, c in enumerate(candidatos):
        s_obj = pres_final['slides'][i + 1]
        notes_page = s_obj.get('slideProperties', {}).get('notesPage', {})
        body_notes_id = None
        for el in notes_page.get('pageElements', []):
            if el.get('shape', {}).get('shapeType') == 'BODY':
                body_notes_id = el['objectId']
                break

        if body_notes_id:
            texto_notas = (
                f"--- FICHA TÉCNICA Y AUDITORÍA ---\n"
                f"• Vistas: {c['vistas']} | Likes: {c['likes']} | Comentarios: {c['comentarios']}\n"
                f"• Fecha de consulta: {fecha_hoy}\n"
                f"• Producto / SKU: {c['titulo']} ({c['sku']})\n"
                f"• Motivo de selección: {c['motivo']}\n\n"
                f"--- ADECUACIONES Y REVISIÓN ---\n"
                f"• Adecuaciones: {c['adecuaciones']}\n"
                f"• Fecha sugerida de publicación Olinka: {c['fecha_sugerida']}\n"
                f"• NOTA: La fecha sugerida no sustituye la fecha del post original.\n"
                f"• ESTADO DE REVISIÓN: Pendiente. Conservar video original; Miguel decide la edición del video."
            )
            batch_notas.append(set_text(body_notes_id, texto_notas))

    if batch_notas:
        slides_service.presentations().batchUpdate(
            presentationId=pres_id,
            body={'requests': batch_notas}
        ).execute()

    print("✅ Presentación mensual estructurada y finalizada con éxito.")
    return pres_id

# ==========================================
# 6. EJECUCIÓN PRINCIPAL
# ==========================================
def main():
    print("==================================================")
    print("🚀 INICIANDO EJECUCIÓN AUTÓNOMA - ARAÑA OLINKA 🚀")
    print("==================================================")

    drive_service, sheets_service, slides_service = obtener_servicios_google()
    gemini_client = configurar_gemini()

    parametros, marcas, promociones = leer_archivo_maestro(sheets_service, SPREADSHEET_ID)

    id_carpeta = parametros.get('ID_CARPETA_DRIVE', '')
    candidatos = compilar_candidatos(marcas, promociones, parametros, gemini_client)

    crear_presentacion_mensual(slides_service, drive_service, id_carpeta, candidatos)

    print("==================================================")
    print("✅ FLUJO QUINCENAL COMPLETADO")
    print("==================================================")

if __name__ == '__main__':
    main()
