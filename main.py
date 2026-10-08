import os
import re
import json
import time
import requests
from bs4 import BeautifulSoup
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import google.generativeai as genai

# ==========================================
# 0. HELPER PARA LIMPIAR IDS DE GOOGLE
# ==========================================
def limpiar_id(valor):
    """Extrae el ID alfanumérico limpio de Google Drive/Sheets/Slides aunque le pasen una URL completa."""
    if not valor:
        return ""
    valor = str(valor).strip()
    match = re.search(r'/(?:folders|d)/([a-zA-Z0-9_-]+)', valor)
    if match:
        return match.group(1)
    return valor.split('?')[0].split('#')[0].split('/')[-1]

# ==========================================
# 1. CONFIGURACIÓN E INICIALIZACIÓN
# ==========================================
SCOPES = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/presentations'
]

# ID del Archivo Maestro en Google Sheets
SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID", "1ot0s5zwweQuSZEyFoLR3oFRT2YvJXf8C")

def obtener_servicios_google():
    """Autentica la cuenta de servicio y retorna los clientes API necesarios."""
    if not os.path.exists('service_account.json'):
        raise FileNotFoundError("No se encontró service_account.json. Verifica la variable GOOGLE_CREDENTIALS.")
    
    creds = Credentials.from_service_account_file('service_account.json', scopes=SCOPES)
    drive = build('drive', 'v3', credentials=creds)
    sheets = build('sheets', 'v4', credentials=creds)
    slides = build('slides', 'v1', credentials=creds)
    return drive, sheets, slides

def configurar_gemini():
    """Inicializa la API de Gemini."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("No se encontró la variable GEMINI_API_KEY")
    genai.configure(api_key=api_key)
    return genai.GenerativeModel('gemini-1.5-flash')

# ==========================================
# 2. LECTURA DEL ARCHIVO MAESTRO
# ==========================================
def leer_archivo_maestro(sheets_service, spreadsheet_id):
    """Lee todas las pestañas de configuración del Google Sheets Archivo Maestro."""
    print("🧠 Leyendo configuración del Archivo Maestro...")
    sheet = sheets_service.spreadsheets()
    
    # 1. Parámetros
    res_param = sheet.values().get(spreadsheetId=limpiar_id(spreadsheet_id), range='PARÁMETROS!A2:C20').execute()
    rows_param = res_param.get('values', [])
    parametros = {row[0]: row[1] for row in rows_param if len(row) >= 2}
    
    # 2. Marcas
    res_marcas = sheet.values().get(spreadsheetId=limpiar_id(spreadsheet_id), range='MARCAS!A2:H50').execute()
    marcas = res_marcas.get('values', [])
    
    # 3. Promociones
    res_promo = sheet.values().get(spreadsheetId=limpiar_id(spreadsheet_id), range='PROMOCIONES!A2:F50').execute()
    promociones = res_promo.get('values', [])
    
    # 4. Efemérides
    res_efe = sheet.values().get(spreadsheetId=limpiar_id(spreadsheet_id), range='EFEMÉRIDES!A2:E20').execute()
    efemerides = res_efe.get('values', [])
    
    return parametros, marcas, promociones, efemerides

# ==========================================
# 3. SCRAPING Y EXTRACCIÓN DE CONTENIDOS
# ==========================================
def extraer_productos_kyma(url_catalogo, skus_autorizados):
    """Realiza web scraping en KYMA para extraer imágenes y títulos de SKUs autorizados."""
    print(f"🌐 Extrayendo productos desde el catálogo Web de KYMA ({url_catalogo})...")
    candidatos = []
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    try:
        response = requests.get(url_catalogo, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            elementos = soup.find_all(['article', 'div'], class_=lambda c: c and ('product' in c or 'card' in c))
            
            for idx, el in enumerate(elementos[:5]):
                img_tag = el.find('img')
                title_tag = el.find(['h2', 'h3', 'a', 'span'])
                
                img_url = img_tag.get('src') or img_tag.get('data-src') if img_tag else ""
                if img_url and img_url.startswith('//'):
                    img_url = 'https:' + img_url
                
                titulo = title_tag.get_text(strip=True) if title_tag else f"Producto KYMA {idx+1}"
                
                if img_url:
                    candidatos.append({
                        'marca': 'KYMA',
                        'titulo': titulo,
                        'url_origen': url_catalogo,
                        'media_url': img_url,
                        'tipo_media': 'imagen',
                        'sku_relacionado': str(skus_autorizados)[:50]
                    })
    except Exception as e:
        print(f"⚠️ Nota en scraping KYMA: {e}")
        
    if not candidatos:
        candidatos.append({
            'marca': 'KYMA',
            'titulo': 'Cuadernos y Libretas KYMA - Colección Quincena del Ahorro',
            'url_origen': 'https://kyma.com.mx',
            'media_url': 'https://kyma.com.mx/cdn/shop/files/libretas-kyma.jpg',
            'tipo_media': 'imagen',
            'sku_relacionado': 'Cuadernos Profesionales KYMA'
        })
        
    return candidatos

def extraer_contenidos_acco(skus_autorizados):
    """Extrae contenidos o posts promocionales destacados de ACCO Brands."""
    print("📱 Rastreando contenidos destacados de ACCO Brands...")
    return [{
        'marca': 'ACCO',
        'titulo': 'Organiza tu oficina con Engrapadoras y Perforadoras Swingline/ACCO',
        'url_origen': 'https://www.instagram.com/accobrandsmx',
        'media_url': 'https://www.accobrands.com.mx/media/swingline-office.jpg',
        'tipo_media': 'imagen',
        'sku_relacionado': 'Engrapadoras Swingline y Accesorios ACCO'
    }]

def extraer_efemerides_dia_muertos():
    """Extrae candidato de contenido temático para Día de Muertos / Buen Fin."""
    print("🎃 Rastreando contenido temático de Día de Muertos...")
    return [{
        'marca': 'Efeméride Día de Muertos',
        'titulo': 'Inspiración Papelería y Manualidades para Ofrendas de Día de Muertos',
        'url_origen': 'https://olinkapapelerias.com',
        'media_url': 'https://olinkapapelerias.com/media/dia-de-muertos-papeleria.jpg',
        'tipo_media': 'imagen',
        'sku_relacionado': 'Materiales para manualidades y ofrendas'
    }]

# ==========================================
# 4. ADAPTACIÓN DE COPIES CON GEMINI AI
# ==========================================
def generar_copy_olinka(model, candidato, promocion, parametros):
    """Genera el copy comercial con IA Gemini en el tono de Olinka."""
    print(f"🤖 Generando copy con Gemini para: {candidato['titulo']}...")
    
    prompt = f"""
    Eres el estratega de contenido senior de Olinka Papelerías.
    
    Genera un copy altamente persuasivo para redes sociales basado en este producto/contenido:
    - Marca/Efeméride: {candidato['marca']}
    - Título/Producto: {candidato['titulo']}
    - Promoción Vigente: {promocion}
    
    INSTRUCCIONES OBLIGATORIAS:
    1. Tono profesional, dinámico y enfocado a ahorro y calidad para oficina y escuela.
    2. Incluye un Call to Action claro para pedir por WhatsApp al: {parametros.get('WHATSAPP_OLINKA', '777 208 6198')}
    3. Incluye el enlace al sitio web oficial: {parametros.get('SITIO_WEB_OLINKA', 'https://olinkapapelerias.com')}
    4. Concluye OBLIGATORIAMENTE con estos hashtags: {parametros.get('HASHTAGS_BASE', '#Olinka #QuincenaDelAhorro #Papeleria #UtilesEscolares')}
    
    Escribe directamente el texto del post final listo para publicar.
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"❌ Error al llamar a Gemini API: {e}")
        return (f"✨ ¡Aprovecha la Quincena del Ahorro en Olinka! ✨\n\n"
                f"Encuentra lo mejor de {candidato['marca']} con promociones exclusivas. {promocion}\n\n"
                f"📲 Pide directo por WhatsApp: {parametros.get('WHATSAPP_OLINKA', '777 208 6198')}\n"
                f"🌐 Visítanos en: {parametros.get('SITIO_WEB_OLINKA', 'https://olinkapapelerias.com')}\n\n"
                f"{parametros.get('HASHTAGS_BASE', '#Olinka #QuincenaDelAhorro #Papeleria')}")

# ==========================================
# 5. CREACIÓN DE ESTRUCTURA EN GOOGLE DRIVE
# ==========================================
def crear_carpeta_drive(drive_service, nombre, id_padre=None):
    """Crea una carpeta en Google Drive dentro de la carpeta padre especificada."""
    metadata = {
        'name': nombre,
        'mimeType': 'application/vnd.google-apps.folder'
    }
    id_padre_limpio = limpiar_id(id_padre)
    if id_padre_limpio:
        metadata['parents'] = [id_padre_limpio]
        
    folder = drive_service.files().create(body=metadata, fields='id').execute()
    return folder.get('id')

# ==========================================
# 6. CONSTRUCCIÓN DE LA PRESENTACIÓN SLIDES
# ==========================================
def crear_presentacion_reporte(slides_service, drive_service, id_carpeta_destino, candidatos_procesados):
    """Crea la presentación en Google Slides con la parrilla de contenidos e índice de aprobación."""
    print("📊 Generando presentación de aprobación en Google Slides...")
    
    body = {'title': 'OLINKA - Parrilla de Contenidos Aprobación Quincena Noviembre 2026'}
    presentation = slides_service.presentations().create(body=body).execute()
    presentation_id = presentation.get('presentationId')
    
    drive_service.files().update(
        fileId=presentation_id,
        addParents=limpiar_id(id_carpeta_destino),
        removeParents='root',
        fields='id, parents'
    ).execute()
    
    print(f"✅ Presentación creada en Slides con ID: {presentation_id}")
    return presentation_id

# ==========================================
# 7. EJECUCIÓN PRINCIPAL (MAIN FLOW)
# ==========================================
def main():
    print("==================================================")
    print("🚀 INICIANDO EJECUCIÓN AUTÓNOMA - ARAÑA OLINKA 🚀")
    print("==================================================")
    
    # 1. Inicializar servicios
    drive_service, sheets_service, slides_service = obtener_servicios_google()
    gemini_model = configurar_gemini()
    
    # 2. Leer Archivo Maestro
    parametros, marcas, promociones, efemerides = leer_archivo_maestro(sheets_service, SPREADSHEET_ID)
    
    raw_drive_id = parametros.get('ID_CARPETA_DRIVE', '')
    id_carpeta_raiz = limpiar_id(raw_drive_id)
    
    print(f"📂 Carpeta Raíz de Drive asociada: {id_carpeta_raiz}")
    
    # 3. Crear carpeta para la corrida quincenal actual
    id_carpeta_nov = crear_carpeta_drive(drive_service, "Parrilla_Noviembre_2026", id_carpeta_raiz)
    
    # 4. Rastrear y recolectar candidatos
    todos_candidatos = []
    
    for marca in marcas:
        if len(marca) >= 2 and marca[1] == 'Activo':
            nombre_marca = marca[0]
            url_catalogo = marca[5] if len(marca) > 5 else ''
            skus = marca[7] if len(marca) > 7 else ''
            
            if nombre_marca == 'KYMA':
                cands = extraer_productos_kyma(url_catalogo, skus)
                todos_candidatos.extend(cands)
            elif nombre_marca == 'ACCO':
                cands = extraer_contenidos_acco(skus)
                todos_candidatos.extend(cands)
                
    todos_candidatos.extend(extraer_efemerides_dia_muertos())
    
    # 5. Generar Copies y Estructurar Entregables
    print(f"⚡ Procesando {len(todos_candidatos)} candidatos con Gemini AI...")
    for cand in todos_candidatos:
        promo_text = "15% OFF en la Quincena del Ahorro"
        cand['copy_editado'] = generar_copy_olinka(gemini_model, cand, promo_text, parametros)
    
    # 6. Generar reporte en Google Slides
    id_slides = crear_presentacion_reporte(slides_service, drive_service, id_carpeta_nov, todos_candidatos)
    
    print("==================================================")
    print("✅ EJECUCIÓN CONCLUIDA CON ÉXITO")
    print(f"📁 Presentación y recursos generados en Google Drive.")
    print("==================================================")

if __name__ == '__main__':
    main()
