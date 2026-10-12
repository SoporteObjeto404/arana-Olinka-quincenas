import os
import re
import json
import time
import requests
from bs4 import BeautifulSoup
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# Importación segura de Gemini API
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
    """Extrae el ID alfanumérico limpio de Google Drive/Sheets/Slides."""
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

SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID", "1VqaYwfy1JkOpD9uupawNGm4htKlVh9Gq")

def obtener_servicios_google():
    """Autentica la cuenta de servicio y retorna los clientes API."""
    if not os.path.exists('service_account.json'):
        raise FileNotFoundError("No se encontró service_account.json.")
    
    creds = Credentials.from_service_account_file('service_account.json', scopes=SCOPES)
    drive = build('drive', 'v3', credentials=creds)
    sheets = build('sheets', 'v4', credentials=creds)
    slides = build('slides', 'v1', credentials=creds)
    return drive, sheets, slides

def configurar_gemini():
    """Inicializa el cliente de Gemini."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("No se encontró la variable GEMINI_API_KEY")
    
    if USE_NEW_SDK:
        return genai.Client(api_key=api_key)
    else:
        genai.configure(api_key=api_key)
        return genai

# ==========================================
# 2. LECTURA DEL ARCHIVO MAESTRO
# ==========================================
def leer_archivo_maestro(sheets_service, spreadsheet_id):
    """Lee las pestañas de configuración del Google Sheets Archivo Maestro."""
    print("🧠 Leyendo configuración del Archivo Maestro...")
    sheet = sheets_service.spreadsheets()
    sheet_id_limpio = limpiar_id(spreadsheet_id)
    
    # 1. Parámetros
    res_param = sheet.values().get(spreadsheetId=sheet_id_limpio, range='PARÁMETROS!A2:C20').execute()
    rows_param = res_param.get('values', [])
    parametros = {row[0]: row[1] for row in rows_param if len(row) >= 2}
    
    # 2. Marcas
    res_marcas = sheet.values().get(spreadsheetId=sheet_id_limpio, range='MARCAS!A2:H50').execute()
    marcas = res_marcas.get('values', [])
    
    # 3. Promociones
    res_promo = sheet.values().get(spreadsheetId=sheet_id_limpio, range='PROMOCIONES!A2:F50').execute()
    promociones = res_promo.get('values', [])
    
    # 4. Efemérides
    res_efe = sheet.values().get(spreadsheetId=sheet_id_limpio, range='EFEMÉRIDES!A2:E20').execute()
    efemerides = res_efe.get('values', [])
    
    return parametros, marcas, promociones, efemerides

# ==========================================
# 3. SCRAPING Y EXTRACCIÓN DE CONTENIDOS
# ==========================================
def extraer_productos_kyma(url_catalogo, skus_autorizados):
    """Realiza web scraping en KYMA para extraer imágenes y títulos."""
    print(f"🌐 Extrayendo productos desde KYMA ({url_catalogo})...")
    candidatos = []
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    if url_catalogo:
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
            'titulo': 'Cuadernos y Libretas KYMA - Coleccion Quincena',
            'url_origen': 'https://kyma.com.mx',
            'media_url': 'https://kyma.com.mx/cdn/shop/files/libretas-kyma.jpg',
            'tipo_media': 'imagen',
            'sku_relacionado': 'Cuadernos Profesionales KYMA'
        })
        
    return candidatos

def extraer
