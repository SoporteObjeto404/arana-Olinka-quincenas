import os
import re
import time
from datetime import datetime
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# ==========================================
# 0. CONFIGURACIÓN E ID EXACTO (CORREGIDO)
# ==========================================
SCOPES = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/presentations'
]

# Aquí está el ID exacto extraído de tu URL con la "I" mayúscula.
SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID", "1zzV8sQ6wpzflSTMZN3Z-ZoxGryqbls428YifbMfIxBU")

def limpiar_id(valor):
    if not valor: return ""
    match = re.search(r'/(?:folders|d)/([a-zA-Z0-9_-]+)', str(valor))
    return match.group(1) if match else str(valor).split('?')[0].split('/')[-1]

def obtener_servicios_google():
    creds = Credentials.from_service_account_file('service_account.json', scopes=SCOPES)
    return build('drive', 'v3', credentials=creds), build('sheets', 'v4', credentials=creds), build('slides', 'v1', credentials=creds)

def leer_archivo_maestro(sheets_service, spreadsheet_id):
    print("🧠 Leyendo Archivo Maestro...")
    sheet = sheets_service.spreadsheets()
    sheet_id = limpiar_id(spreadsheet_id)
    res_param = sheet.values().get(spreadsheetId=sheet_id, range='PARÁMETROS!A2:C20').execute()
    return {row[0]: row[1] for row in res_param.get('values', []) if len(row) >= 2}

def extraer_candidatos(parametros):
    """Extrae los contenidos y adapta el copy según especificaciones (Simulado para demostración de Layout)."""
    return [{
        'marca': 'KYMA',
        'titulo': 'Cuadernos y Libretas Profesionales',
        'url_origen': 'https://www.instagram.com/p/DB123456789/',
        'fecha_origen': '28 de Octubre, 2026',
        'vistas': '14.5K', 'likes': '820', 'comentarios': '45',
        'sku': 'KYM-091',
        'motivo': 'Alta interacción orgánica y promoción del 15% OFF vigente confirmada en Maestro.',
        'copy_original': "¡Llegaron los nuevos cuadernos profesionales de pasta dura! Encuentra tu estilo en nuestra tienda en línea. #KymaStationery",
        'copy_olinka': f"¡Organiza tu regreso a clases o tus proyectos de oficina con la calidad de KYMA! 📓✨ Aprovecha hasta 15% OFF exclusivo durante esta Quincena del Ahorro en Olinka Papelerías.\n\n📲 Pide directamente por WhatsApp al {parametros.get('WHATSAPP_OLINKA', '777 208 6198')} con envío a domicilio.\n🌐 Visítanos en {parametros.get('SITIO_WEB_OLINKA', 'https://olinkapapelerias.com')}\n\n{parametros.get('HASHTAGS_BASE', '#Olinka #QuincenaDelAhorro #Papeleria #Kyma')}",
        'link_drive': 'https://drive.google.com/drive/folders/carpeta_video_ejemplo',
        'fecha_sugerida': '03 de Noviembre 2026'
    }]

def crear_presentacion_mensual(slides_service, drive_service, id_carpeta, candidatos):
    mes_actual = datetime.now().strftime("%B %Y").upper()
    print(f"📊 Generando Presentación Estructurada: PARRILLA {mes_actual}...")
    
    body = {'name': f'OLINKA - Parrilla de Contenidos - {mes_actual}', 'parents': [limpiar_id(id_carpeta)] if id_carpeta else []}
    pres = drive_service.files().create(body=body, fields='id', supportsAllDrives=True).execute()
    pres_id = pres.get('id')
    
    # 1. Crear diapositivas (1 Índice + Candidatos)
    req_crear = [{'createSlide': {'objectId': 'slide_indice', 'slideLayoutReference': {'predefinedLayout': 'TITLE_AND_BODY'}}}]
    for i in range(len(candidatos)):
        req_crear.append({'createSlide': {'objectId': f'slide_cand_{i}', 'slideLayoutReference': {'predefinedLayout': 'BLANK'}}})
    slides_service.presentations().batchUpdate(presentationId=pres_id, body={'requests': req_crear}).execute()
    
    # 2. Rescatar IDs de Notas del Orador
    pres_data = slides_service.presentations().get(presentationId=pres_id).execute()
    notas_ids = {}
    for slide in pres_data.get('slides', []):
        notes_page = slide.get('slideProperties', {}).get('notesPage', {})
        for element in notes_page.get('pageElements', []):
            if element.get('shape', {}).get('shapeType') == 'BODY':
                notas_ids[slide['objectId']] = element['objectId']

    # 3. Dibujar el esquema físico exacto
    req_dibujar = []
    
    # Índice
    try:
        titulo_indice_id = pres_data['slides'][0]['pageElements'][0]['objectId']
        req_dibujar.append({'insertText': {'objectId': titulo_indice_id, 'text': f"ÍNDICE GENERAL Y ESTADO DE REVISIÓN\nPARRILLA {mes_actual}"}})
    except (IndexError, KeyError):
        pass

    for i, cand in enumerate(candidatos):
        s_id = f'slide_cand_{i}'
        
        def add_shape(id_str, shape_type, x, y, w, h, text, bg_color=None):
            req = {'createShape': {'objectId': id_str, 'shapeType': shape_type, 'elementProperties': {
                'pageObjectId': s_id,
                'size': {'height': {'magnitude': h, 'unit': 'EMU'}, 'width': {'magnitude': w, 'unit': 'EMU'}},
                'transform': {'scaleX': 1, 'scaleY': 1, 'translateX': x, 'translateY': y, 'unit': 'EMU'}
            }}}
            if bg_color:
                req['createShape']['elementProperties']['shapeBackgroundFill'] = {'solidFill': {'color': {'rgbColor': bg_color}}}
            req_dibujar.append(req)
            if text:
                req_dibujar.append({'insertText': {'objectId': id_str, 'text': text}})

        # === COLUMNA IZQUIERDA ===
        add_shape(f'logo_{i}', 'TEXT_BOX', 400000, 300000, 2000000, 400000, "🏢 LOGO OLINKA")
        add_shape(f'etiq_{i}', 'ROUND_RECTANGLE', 400000, 800000, 2000000, 300000, "QUINCENA DEL AHORRO", {'red': 0.9, 'green': 0.9, 'blue': 0.9})
        add_shape(f'reel_{i}', 'RECTANGLE', 400000, 1200000, 2000000, 3200000, f"▶️ REEL VERTICAL (9:16)\n\n[Espacio para Video]\n{cand['titulo']}", {'red': 0.95, 'green': 0.95, 'blue': 0.95})
        add_shape(f'drive_{i}', 'TEXT_BOX', 400000, 4500000, 2000000, 400000, f"🔗 Enlace clicable al video en Drive:\n{cand['link_drive']}")

        # === COLUMNA DERECHA ARRIBA ===
        add_shape(f'franja_{i}', 'RECTANGLE', 3000000, 300000, 5500000, 400000, f"🔗 Enlace al post original: {cand['url_origen']}", {'red': 0.85, 'green': 0.9, 'blue': 1.0})
        add_shape(f'marca_{i}', 'TEXT_BOX', 3000000, 800000, 5500000, 300000, f"Marca Original: {cand['marca']}   |   Fecha de publicación de origen: {cand['fecha_origen']}")

        # === COLUMNA DERECHA RECUADROS SEPARADOS ===
        add_shape(f'corig_{i}', 'RECTANGLE', 3000000, 1200000, 5500000, 1500000, f"COPY ORIGINAL:\n\n{cand['copy_original']}", {'red': 1.0, 'green': 1.0, 'blue': 1.0})
        add_shape(f'colin_{i}', 'RECTANGLE', 3000000, 2900000, 5500000, 1900000, f"COPY NUEVO ADAPTADO A OLINKA:\n\n{cand['copy_olinka']}", {'red': 1.0, 'green': 1.0, 'blue': 1.0})

        # === NOTAS DEL ORADOR ===
        if s_id in notas_ids:
            notas = (
                f"--- MÉTRICAS Y DATOS DE ORIGEN ---\n"
                f"Vistas: {cand['vistas']} | Likes: {cand['likes']} | Comentarios: {cand['comentarios']}\n"
                f"Fecha de consulta: {datetime.now().strftime('%d/%m/%Y')}\n"
                f"Producto/SKU: {cand['titulo']} ({cand['sku']})\n"
                f"Motivo de selección: {cand['motivo']}\n\n"
                f"--- ADECUACIONES Y ESTADO ---\n"
                f"Fecha sugerida de publicación Olinka: {cand['fecha_sugerida']}\n"
                f"ESTADO DE REVISIÓN: Pendiente. Miguel decide la edición final del video."
            )
            req_dibujar.append({'insertText': {'objectId': notas_ids[s_id], 'text': notas}})

    slides_service.presentations().batchUpdate(presentationId=pres_id, body={'requests': req_dibujar}).execute()
    print("✅ Presentación estructurada correctamente.")
    return pres_id

def main():
    print("==================================================")
    print("🚀 INICIANDO EJECUCIÓN AUTÓNOMA - ARAÑA OLINKA 🚀")
    print("==================================================")
    
    drive_service, sheets_service, slides_service = obtener_servicios_google()
    parametros = leer_archivo_maestro(sheets_service, SPREADSHEET_ID)
    
    candidatos = extraer_candidatos(parametros)
    crear_presentacion_mensual(slides_service, drive_service, parametros.get('ID_CARPETA_DRIVE', ''), candidatos)
    print("✅ EJECUCIÓN CONCLUIDA CON ÉXITO. REVISA GOOGLE DRIVE.")

if __name__ == '__main__':
    main()
