import os
import re
import json
import time
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
# 0. HELPER PARA LIMPIAR IDS DE GOOGLE
# ==========================================
def limpiar_id(valor):
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

SPREADSHEET_ID = os.environ.get(
    "SPREADSHEET_ID",
    "1VqaYwfy1JkOpD9uupawNGm4htKlVh9Gq"
)

def obtener_servicios_google():
    if not os.path.exists('service_account.json'):
        raise FileNotFoundError("Falta service_account.json.")
    
    creds = Credentials.from_service_account_file(
        'service_account.json',
        scopes=SCOPES
    )
    drive = build('drive', 'v3', credentials=creds)
    sheets = build('sheets', 'v4', credentials=creds)
    slides = build('slides', 'v1', credentials=creds)
    return drive, sheets, slides

def configurar_gemini():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("No se encontro GEMINI_API_KEY")
    
    if USE_NEW_SDK:
        return genai.Client(api_key=api_key)
    else:
        genai.configure(api_key=api_key)
        return genai

# ==========================================
# 2. LECTURA DEL ARCHIVO MAESTRO
# ==========================================
def leer_archivo_maestro(sheets_service, spreadsheet_id):
    print("Leyendo configuracion del Archivo Maestro...")
    sheet = sheets_service.spreadsheets()
    sheet_id_limpio = limpiar_id(spreadsheet_id)
    
    res_param = sheet.values().get(
        spreadsheetId=sheet_id_limpio,
        range='PARÁMETROS!A2:C20'
    ).execute()
    rows_param = res_param.get('values', [])
    parametros = {
        row[0]: row[1]
        for row in rows_param
        if len(row) >= 2
    }
    
    res_marcas = sheet.values().get(
        spreadsheetId=sheet_id_limpio,
        range='MARCAS!A2:H50'
    ).execute()
    marcas = res_marcas.get('values', [])
    
    res_promo = sheet.values().get(
        spreadsheetId=sheet_id_limpio,
        range='PROMOCIONES!A2:F50'
    ).execute()
    promociones = res_promo.get('values', [])
    
    res_efe = sheet.values().get(
        spreadsheetId=sheet_id_limpio,
        range='EFEMÉRIDES!A2:E20'
    ).execute()
    efemerides = res_efe.get('values', [])
    
    return parametros, marcas, promociones, efemerides

# ==========================================
# 3. SCRAPING Y EXTRACCIÓN DE CONTENIDOS
# ==========================================
def extraer_productos_kyma(url_catalogo, skus_autorizados):
    print(f"Rastreando KYMA: {url_catalogo}...")
    candidatos = []
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    if url_catalogo:
        try:
            r = requests.get(url_catalogo, headers=headers, timeout=10)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, 'html.parser')
                items = soup.find_all(
                    ['article', 'div'],
                    class_=lambda c: c and ('product' in c or 'card' in c)
                )
                for idx, el in enumerate(items[:5]):
                    img = el.find('img')
                    tag = el.find(['h2', 'h3', 'a', 'span'])
                    src = img.get('src') or img.get('data-src') if img else ""
                    if src and src.startswith('//'):
                        src = 'https:' + src
                    title = tag.get_text(strip=True) if tag else f"Item {idx+1}"
                    if src:
                        candidatos.append({
                            'marca': 'KYMA',
                            'titulo': title,
                            'url_origen': url_catalogo,
                            'media_url': src,
                            'tipo_media': 'imagen',
                            'sku_relacionado': str(skus_autorizados)[:50]
                        })
        except Exception as e:
            print(f"Aviso scraping KYMA: {e}")
        
    if not candidatos:
        candidatos.append({
            'marca': 'KYMA',
            'titulo': 'Cuadernos KYMA Quincena',
            'url_origen': 'https://kyma.com.mx',
            'media_url': 'https://kyma.com.mx/cdn/shop/files/libretas-kyma.jpg',
            'tipo_media': 'imagen',
            'sku_relacionado': 'Cuadernos KYMA'
        })
        
    return candidatos

def extraer_contenidos_acco(skus_autorizados):
    print("Rastreando contenidos ACCO Brands...")
    return [{
        'marca': 'ACCO',
        'titulo': 'Engrapadoras y Accesorios ACCO',
        'url_origen': 'https://www.instagram.com/accobrandsmx',
        'media_url': 'https://www.accobrands.com.mx/media/swingline-office.jpg',
        'tipo_media': 'imagen',
        'sku_relacionado': 'Accesorios ACCO'
    }]

def extraer_efemerides_dia_muertos():
    print("Rastreando contenidos Dia de Muertos...")
    return [{
        'marca': 'Dia de Muertos',
        'titulo': 'Manualidades Dia de Muertos',
        'url_origen': 'https://olinkapapelerias.com',
        'media_url': 'https://olinkapapelerias.com/media/dia-de-muertos-papeleria.jpg',
        'tipo_media': 'imagen',
        'sku_relacionado': 'Materiales Dia de Muertos'
    }]

# ==========================================
# 4. ADAPTACIÓN DE COPIES CON GEMINI AI
# ==========================================
def generar_copy_olinka(gemini_client, cand, promo, params):
    print(f"Generando copy para: {cand['titulo']}...")
    
    tel = params.get('WHATSAPP_OLINKA', '777 208 6198')
    web = params.get('SITIO_WEB_OLINKA', 'https://olinkapapelerias.com')
    ht = params.get('HASHTAGS_BASE', '#Olinka #QuincenaDelAhorro #Papeleria')
    
    prompt_lines = [
        "Eres redactor comercial de Olinka Papelerias.",
        f"Marca: {cand['marca']}",
        f"Producto: {cand['titulo']}",
        f"Promocion: {promo}",
        "Instrucciones:",
        "1. Redacta un copy de venta breve y dinamico para redes sociales.",
        f"2. Agrega CTA de WhatsApp: {tel}",
        f"3. Agrega enlace web: {web}",
        f"4. Cierra con los hashtags: {ht}"
    ]
    prompt = "\n".join(prompt_lines)
    
    modelos = ['gemini-2.5-flash', 'gemini-2.0-flash', 'gemini-1.5-flash']
    
    for mod in modelos:
        try:
            if USE_NEW_SDK:
                res = gemini_client.models.generate_content(
                    model=mod,
                    contents=prompt
                )
                return res.text.strip()
            else:
                m = gemini_client.GenerativeModel(mod)
                res = m.generate_content(prompt)
                return res.text.strip()
        except Exception:
            continue

    return (
        f"Promocion en Olinka: {cand['titulo']}\n"
        f"Aprovecha: {promo}\n\n"
        f"WhatsApp: {tel}\n"
        f"Tienda en linea: {web}\n"
        f"{ht}"
    )

# ==========================================
# 5. CREACIÓN DE ESTRUCTURA EN GOOGLE DRIVE
# ==========================================
def crear_carpeta_drive(drive_service, nombre, id_padre=None):
    metadata = {
        'name': nombre,
        'mimeType': 'application/vnd.google-apps.folder'
    }
    id_padre_limpio = limpiar_id(id_padre)
    if id_padre_limpio:
        metadata['parents'] = [id_padre_limpio]
        
    folder = drive_service.files().create(
        body=metadata,
        fields='id',
        supportsAllDrives=True
    ).execute()
    return folder.get('id')

# ==========================================
# 6. CONSTRUCCIÓN DE LA PRESENTACIÓN SLIDES
# ==========================================
def crear_presentacion_reporte(slides_service, drive_service, id_destino, id_plantilla, candidatos):
    print("Creando presentacion en Google Drive...")
    
    id_dest_limpio = limpiar_id(id_destino)
    id_plan_limpia = limpiar_id(id_plantilla)
    
    body = {
        'name': 'OLINKA - Parrilla de Contenidos Quincena',
        'parents': [id_dest_limpio] if id_dest_limpio else []
    }
    
    if id_plan_limpia:
        file_obj = drive_service.files().copy(
            fileId=id_plan_limpia,
            body=body,
            fields='id',
            supportsAllDrives=True
        ).execute()
        pres_id = file_obj.get('id')
    else:
        body['mimeType'] = 'application/vnd.google-apps.presentation'
        file_obj = drive_service.files().create(
            body=body,
            fields='id',
            supportsAllDrives=True
        ).execute()
        pres_id = file_obj.get('id')
    
    print(f"Presentacion lista con ID: {pres_id}")
    return pres_id

# ==========================================
# 7. EJECUCIÓN PRINCIPAL
# ==========================================
def main():
    print("==================================================")
    print("INICIANDO EJECUCION AUTONOMA - ARANA OLINKA")
    print("==================================================")
    
    drive_service, sheets_service, slides_service = obtener_servicios_google()
    gemini_client = configurar_gemini()
    
    parametros, marcas, promociones, efemerides = leer_archivo_maestro(
        sheets_service,
        SPREADSHEET_ID
    )
    
    raw_drive_id = parametros.get('ID_CARPETA_DRIVE', '')
    raw_slides_id = parametros.get('ID_PLANTILLA_SLIDES', '')
    id_carpeta_raiz = limpiar_id(raw_drive_id)
    
    print(f"Carpeta Raiz asociada: {id_carpeta_raiz}")
    
    id_carpeta_nov = crear_carpeta_drive(
        drive_service,
        "Parrilla_Noviembre_2026",
        id_carpeta_raiz
    )
    
    todos_candidatos = []
    
    for marca in marcas:
        if len(marca) >= 2 and marca[1] == 'Activo':
            nom = marca[0]
            url = marca[5] if len(marca) > 5 else ''
            skus = marca[7] if len(marca) > 7 else ''
            
            if nom == 'KYMA':
                todos_candidatos.extend(extraer_productos_kyma(url, skus))
            elif nom == 'ACCO':
                todos_candidatos.extend(extraer_contenidos_acco(skus))
                
    todos_candidatos.extend(extraer_efemerides_dia_muertos())
    
    print(f"Procesando {len(todos_candidatos)} candidatos con Gemini...")
    for cand in todos_candidatos:
        promo_text = "15% OFF en la Quincena del Ahorro"
        cand['copy_editado'] = generar_copy_olinka(
            gemini_client,
            cand,
            promo_text,
            parametros
        )
    
    id_slides = crear_presentacion_reporte(
        slides_service,
        drive_service,
        id_carpeta_nov,
        raw_slides_id,
        todos_candidatos
    )
    
    print("==================================================")
    print("EJECUCION CONCLUIDA CON EXITO")
    print("==================================================")

if __name__ == '__main__':
    main()
