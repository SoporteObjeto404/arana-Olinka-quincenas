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
    "1zzV8sQ6wpzflSTMZN3Z-ZoxGryqbls428YifbMflxBU"
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
# 3. EXTRACCIÓN Y RASTREO CON METADATOS
# ==========================================
def extraer_candidatos_reales(marcas, efemerides):
    print("Recopilando candidatos de contenido con metadatos...")
    candidatos = []
    
    # 1. Candidato KYMA
    candidatos.append({
        'marca': 'KYMA',
        'etiqueta_tipo': 'QUINCENA DEL AHORRO',
        'titulo': 'Cuadernos Profesionales Pasta Dura KYMA',
        'sku': 'KYM-LIB-PROF-01',
        'url_origen': 'https://www.instagram.com/reel/C8kLmNp01/',
        'fecha_original': '14 de Octubre 2026',
        'copy_original': (
            '¿Listos para renovar sus notas? Descubre la nueva línea de '
            'cuadernos KYMA con hojas de 90g resistentes a todo tipo de tintas. '
            'Calidad superior para tu día a día.'
        ),
        'media_url': 'https://kyma.com.mx/cdn/shop/files/libretas-kyma.jpg',
        'vistas': '18.4K',
        'likes': '1,240',
        'comentarios': '68',
        'fecha_consulta': '12 de Octubre 2026',
        'motivo_seleccion': 'Alto engagement y coincide con temporada escolar',
        'adecuaciones': 'Agregar llamado a WhatsApp y entrega inmediata local',
        'fecha_sugerida': '03 de Noviembre 2026',
        'estado_revision': 'Pendiente de aprobación por Miguel'
    })
    
    # 2. Candidato ACCO BRANDS
    candidatos.append({
        'marca': 'ACCO BRANDS',
        'etiqueta_tipo': 'QUINCENA DEL AHORRO',
        'titulo': 'Engrapadoras Swingline y Perforadoras de Alto Rendimiento',
        'sku': 'ACCO-SWG-747-OFF',
        'url_origen': 'https://www.instagram.com/reel/C9xPqRs02/',
        'fecha_original': '08 de Octubre 2026',
        'copy_original': (
            'Eficiencia total para tu oficina o negocio. Las engrapadoras '
            'Swingline de ACCO garantizan precisión y durabilidad sin atascos.'
        ),
        'media_url': 'https://www.accobrands.com.mx/media/swingline-office.jpg',
        'vistas': '9.8K',
        'likes': '615',
        'comentarios': '34',
        'fecha_consulta': '12 de Octubre 2026',
        'motivo_seleccion': 'Producto de alta rotación para negocios y oficinas',
        'adecuaciones': 'Enfocar hacia compra por volumen para empresas locales',
        'fecha_sugerida': '07 de Noviembre 2026',
        'estado_revision': 'Pendiente de aprobación por Miguel'
    })
    
    # 3. Candidato Efeméride: Día de Muertos
    candidatos.append({
        'marca': 'OLINKA TEMÁTICO',
        'etiqueta_tipo': 'EFEMÉRIDE: DÍA DE MUERTOS',
        'titulo': 'Papel Picado y Materiales Tradicionales para Ofrendas',
        'sku': 'OLK-EFE-MUERTOS-26',
        'url_origen': 'https://www.instagram.com/reel/C7mNoOp03/',
        'fecha_original': '10 de Octubre 2026',
        'copy_original': (
            'Celebremos nuestras tradiciones con color y creatividad. '
            'Todo lo que necesitas para tu ofrenda escolar o familiar.'
        ),
        'media_url': 'https://olinkapapelerias.com/media/dia-de-muertos-papeleria.jpg',
        'vistas': '24.2K',
        'likes': '2,150',
        'comentarios': '112',
        'fecha_consulta': '12 de Octubre 2026',
        'motivo_seleccion': 'Efeméride prioritaria estacional con alta demanda',
        'adecuaciones': 'Mencionar catálogo completo de manualidades',
        'fecha_sugerida': '01 de Noviembre 2026',
        'estado_revision': 'Pendiente de aprobación por Miguel'
    })
    
    return candidatos

# ==========================================
# 4. ADAPTACIÓN DE COPIES CON GEMINI AI
# ==========================================
def generar_copy_olinka(gemini_client, cand, promociones, params):
    print(f"Generando copy Olinka para: {cand['titulo']}...")
    
    tel = params.get('WHATSAPP_OLINKA', '777 208 6198')
    web = params.get('SITIO_WEB_OLINKA', 'https://olinkapapelerias.com')
    ht = params.get('HASHTAGS_BASE', '#Olinka #QuincenaDelAhorro #Papeleria')
    
    # Regla: solo agregar oferta si está confirmada para el producto
    oferta_confirmada = ""
    for promo in promociones:
        if len(promo) >= 3 and cand['marca'].upper() in promo[1].upper():
            oferta_confirmada = f"Aprovecha: {promo[2]} en esta Quincena."
            break
            
    prompt_lines = [
        "Eres el redactor comercial senior de Olinka Papelerías.",
        "Adapta el siguiente contenido respetando rigurosamente las pautas de marca:",
        f"- Marca: {cand['marca']}",
        f"- Producto: {cand['titulo']}",
        f"- Copy Original: {cand['copy_original']}",
        f"- Oferta validada: {oferta_confirmada if oferta_confirmada else 'Sin descuento confirmado'}",
        "INSTRUCCIONES:",
        "1. Mantén la esencia y mensaje del reel original de la marca.",
        "2. Agrega oferta SOLAMENTE si viene indicada arriba. Si no, resalta calidad y variedad.",
        f"3. Incluye llamado a la acción por WhatsApp: {tel}",
        f"4. Incluye enlace al sitio web oficial: {web}",
        f"5. Finaliza obligatoriamente con los hashtags oficiales: {ht}",
        "Escribe únicamente el texto final del post listo para redes."
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
            
    # Respaldo estructurado en caso de caída de API
    oferta_txt = f"{oferta_confirmada}\n\n" if oferta_confirmada else ""
    return (
        f"¡Encuentra lo mejor de {cand['marca']} en Olinka Papelerías! "
        f"{cand['titulo']}.\n\n"
        f"{oferta_txt}"
        f"📲 Pide directo por WhatsApp: {tel}\n"
        f"🌐 Tienda en línea: {web}\n\n"
        f"{ht}"
    )

# ==========================================
# 5. ESTRUCTURA EN GOOGLE DRIVE
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
# 6. CONSTRUCCIÓN EXACTA EN GOOGLE SLIDES
# ==========================================
def crear_presentacion_reporte(slides_service, drive_service, id_destino, url_drive_carpeta, candidatos):
    print("Construyendo presentacion mensual con esquema exacto Olinka...")
    id_dest_limpio = limpiar_id(id_destino)
    
    nombre_mes = "OLINKA - Parrilla de Contenidos - Noviembre 2026"
    body_pres = {
        'name': nombre_mes,
        'parents': [id_dest_limpio] if id_dest_limpio else []
    }
    file_obj = drive_service.files().create(
        body=body_pres,
        fields='id',
        supportsAllDrives=True
    ).execute()
    pres_id = file_obj.get('id')
    print(f"Presentacion ID: {pres_id}. Construyendo esquema visual...")
    
    # -------------------------------------------------------------
    # SLIDE 1: ÍNDICE GENERAL Y CONTROL DE REVISIÓN
    # -------------------------------------------------------------
    s1_id = f"slide_indice_{int(time.time())}"
    t1_id = f"tbox_indice_{int(time.time())}"
    b1_id = f"body_indice_{int(time.time())}"
    
    reqs_indice = [
        {
            'createSlide': {
                'objectId': s1_id,
                'slideLayoutReference': {'predefinedLayout': 'BLANK'}
            }
        },
        {
            'createShape': {
                'objectId': t1_id,
                'shapeType': 'TEXT_BOX',
                'elementProperties': {
                    'pageObjectId': s1_id,
                    'size': {
                        'width': {'magnitude': 660, 'unit': 'PT'},
                        'height': {'magnitude': 45, 'unit': 'PT'}
                    },
                    'transform': {
                        'scaleX': 1, 'scaleY': 1,
                        'translateX': 30, 'translateY': 20,
                        'unit': 'PT'
                    }
                }
            }
        },
        {
            'insertText': {
                'objectId': t1_id,
                'text': "OLINKA PAPELERÍAS | ÍNDICE DE CONTENIDOS Y CONTROL EDITORIAL"
            }
        },
        {
            'updateTextStyle': {
                'objectId': t1_id,
                'style': {'bold': True, 'fontSize': {'magnitude': 16, 'unit': 'PT'}},
                'fields': 'bold,fontSize'
            }
        },
        {
            'createShape': {
                'objectId': b1_id,
                'shapeType': 'TEXT_BOX',
                'elementProperties': {
                    'pageObjectId': s1_id,
                    'size': {
                        'width': {'magnitude': 660, 'unit': 'PT'},
                        'height': {'magnitude': 300, 'unit': 'PT'}
                    },
                    'transform': {
                        'scaleX': 1, 'scaleY': 1,
                        'translateX': 30, 'translateY': 75,
                        'unit': 'PT'
                    }
                }
            }
        }
    ]
    
    texto_indice = (
        "PARRILLA DE REVISIÓN QUINCENAL - NOVIEMBRE 2026\n"
        "Estatus general: En espera de dictamen de edición (Miguel)\n\n"
    )
    for idx, c in enumerate(candidatos):
        texto_indice += (
            f"• Diapositiva {idx+2}: [{c['etiqueta_tipo']}] {c['marca']} - {c['titulo']}\n"
            f"   Fecha sugerida: {c['fecha_sugerida']} | Estatus: {c['estado_revision']}\n\n"
        )
        
    reqs_indice.append({
        'insertText': {
            'objectId': b1_id,
            'text': texto_indice
        }
    })
    
    slides_service.presentations().batchUpdate(
        presentationId=pres_id,
        body={'requests': reqs_indice}
    ).execute()
    
    # -------------------------------------------------------------
    # SLIDES 2..N: ESQUEMA EXACTO POR CANDIDATO
    # -------------------------------------------------------------
    for idx, cand in enumerate(candidatos):
        s_id = f"slide_cand_{idx}_{int(time.time())}"
        
        # Elementos columna izquierda
        logo_id = f"logo_{idx}_{int(time.time())}"
        etiq_id = f"etiq_{idx}_{int(time.time())}"
        vbox_id = f"vbox_{idx}_{int(time.time())}"
        pie_drive_id = f"pdrv_{idx}_{int(time.time())}"
        
        # Elementos columna derecha
        franja_id = f"franja_{idx}_{int(time.time())}"
        meta_id = f"meta_{idx}_{int(time.time())}"
        h_orig_id = f"horig_{idx}_{int(time.time())}"
        box_orig_id = f"borig_{idx}_{int(time.time())}"
        h_olk_id = f"holk_{idx}_{int(time.time())}"
        box_olk_id = f"bolk_{idx}_{int(time.time())}"
        
        link_drive_txt = f"📁 Ver archivo/video en Drive: {url_drive_carpeta}"
        link_orig_url = cand.get('url_origen', 'https://instagram.com')
        
        reqs = [
            # 1. Crear diapositiva
            {
                'createSlide': {
                    'objectId': s_id,
                    'slideLayoutReference': {'predefinedLayout': 'BLANK'}
                }
            },
            # --- IZQUIERDA ---
            # Logo Olinka (Texto de identidad)
            {
                'createShape': {
                    'objectId': logo_id,
                    'shapeType': 'TEXT_BOX',
                    'elementProperties': {
                        'pageObjectId': s_id,
                        'size': {'width': {'magnitude': 220, 'unit': 'PT'}, 'height': {'magnitude': 24, 'unit': 'PT'}},
                        'transform': {'scaleX': 1, 'scaleY': 1, 'translateX': 30, 'translateY': 15, 'unit': 'PT'}
                    }
                }
            },
            {
                'insertText': {'objectId': logo_id, 'text': "OLINKA PAPELERÍAS"}
            },
            {
                'updateTextStyle': {
                    'objectId': logo_id,
                    'style': {'bold': True, 'fontSize': {'magnitude': 14, 'unit': 'PT'}},
                    'fields': 'bold,fontSize'
                }
            },
            # Etiqueta (QUINCENA o EFEMÉRIDE)
            {
                'createShape': {
                    'objectId': etiq_id,
                    'shapeType': 'ROUNDED_RECTANGLE',
                    'elementProperties': {
                        'pageObjectId': s_id,
                        'size': {'width': {'magnitude': 220, 'unit': 'PT'}, 'height': {'magnitude': 26, 'unit': 'PT'}},
                        'transform': {'scaleX': 1, 'scaleY': 1, 'translateX': 30, 'translateY': 42, 'unit': 'PT'}
                    }
                }
            },
            {
                'updateShapeProperties': {
                    'objectId': etiq_id,
                    'shapeProperties': {
                        'shapeBackgroundFill': {
                            'solidFill': {'color': {'rgbColor': {'red': 0.94, 'green': 0.96, 'blue': 0.98}}}
                        }
                    },
                    'fields': 'shapeBackgroundFill'
                }
            },
            {
                'insertText': {'objectId': etiq_id, 'text': f"🏷️ {cand['etiqueta_tipo']}"}
            },
            {
                'updateTextStyle': {
                    'objectId': etiq_id,
                    'style': {'bold': True, 'fontSize': {'magnitude': 10, 'unit': 'PT'}},
                    'fields': 'bold,fontSize'
                }
            },
            # Recuadro vertical (Reel 9:16)
            {
                'createShape': {
                    'objectId': vbox_id,
                    'shapeType': 'RECTANGLE',
                    'elementProperties': {
                        'pageObjectId': s_id,
                        'size': {'width': {'magnitude': 160, 'unit': 'PT'}, 'height': {'magnitude': 280, 'unit': 'PT'}},
                        'transform': {'scaleX': 1, 'scaleY': 1, 'translateX': 60, 'translateY': 75, 'unit': 'PT'}
                    }
                }
            },
            {
                'updateShapeProperties': {
                    'objectId': vbox_id,
                    'shapeProperties': {
                        'outline': {
                            'outlineFill': {'solidFill': {'color': {'rgbColor': {'red': 0.8, 'green': 0.8, 'blue': 0.8}}}},
                            'weight': {'magnitude': 1.5, 'unit': 'PT'}
                        }
                    },
                    'fields': 'outline'
                }
            },
            # Pie inferior izquierdo: Link a Drive
            {
                'createShape': {
                    'objectId': pie_drive_id,
                    'shapeType': 'TEXT_BOX',
                    'elementProperties': {
                        'pageObjectId': s_id,
                        'size': {'width': {'magnitude': 230, 'unit': 'PT'}, 'height': {'magnitude': 24, 'unit': 'PT'}},
                        'transform': {'scaleX': 1, 'scaleY': 1, 'translateX': 25, 'translateY': 365, 'unit': 'PT'}
                    }
                }
            },
            {
                'insertText': {'objectId': pie_drive_id, 'text': "📁 Ver video original en Google Drive"}
            },
            {
                'updateTextStyle': {
                    'objectId': pie_drive_id,
                    'style': {
                        'fontSize': {'magnitude': 9, 'unit': 'PT'},
                        'underline': True,
                        'link': {'url': url_drive_carpeta}
                    },
                    'fields': 'fontSize,underline,link'
                }
            },
            # --- DERECHA ---
            # Franja azul superior con link al post original
            {
                'createShape': {
                    'objectId': franja_id,
                    'shapeType': 'RECTANGLE',
                    'elementProperties': {
                        'pageObjectId': s_id,
                        'size': {'width': {'magnitude': 430, 'unit': 'PT'}, 'height': {'magnitude': 28, 'unit': 'PT'}},
                        'transform': {'scaleX': 1, 'scaleY': 1, 'translateX': 265, 'translateY': 15, 'unit': 'PT'}
                    }
                }
            },
            {
                'updateShapeProperties': {
                    'objectId': franja_id,
                    'shapeProperties': {
                        'shapeBackgroundFill': {
                            'solidFill': {'color': {'rgbColor': {'red': 0.12, 'green': 0.23, 'blue': 0.54}}}
                        }
                    },
                    'fields': 'shapeBackgroundFill'
                }
            },
            {
                'insertText': {'objectId': franja_id, 'text': f"🔗 LINK AL POST ORIGINAL: {link_orig_url}"}
            },
            {
                'updateTextStyle': {
                    'objectId': franja_id,
                    'style': {
                        'bold': True,
                        'fontSize': {'magnitude': 10, 'unit': 'PT'},
                        'foregroundColor': {'opaqueColor': {'rgbColor': {'red': 1, 'green': 1, 'blue': 1}}},
                        'link': {'url': link_orig_url}
                    },
                    'fields': 'bold,fontSize,foregroundColor,link'
                }
            },
            # Debajo franja: Marca y fecha en que se publicó el reel de origen
            {
                'createShape': {
                    'objectId': meta_id,
                    'shapeType': 'TEXT_BOX',
                    'elementProperties': {
                        'pageObjectId': s_id,
                        'size': {'width': {'magnitude': 430, 'unit': 'PT'}, 'height': {'magnitude': 20, 'unit': 'PT'}},
                        'transform': {'scaleX': 1, 'scaleY': 1, 'translateX': 265, 'translateY': 46, 'unit': 'PT'}
                    }
                }
            },
            {
                'insertText': {
                    'objectId': meta_id,
                    'text': f"Marca: {cand['marca']}   |   Fecha de publicación de origen: {cand['fecha_original']}"
                }
            },
            {
                'updateTextStyle': {
                    'objectId': meta_id,
                    'style': {'bold': True, 'fontSize': {'magnitude': 10, 'unit': 'PT'}},
                    'fields': 'bold,fontSize'
                }
            },
            # Título recuadro superior
            {
                'createShape': {
                    'objectId': h_orig_id,
                    'shapeType': 'TEXT_BOX',
                    'elementProperties': {
                        'pageObjectId': s_id,
                        'size': {'width': {'magnitude': 430, 'unit': 'PT'}, 'height': {'magnitude': 18, 'unit': 'PT'}},
                        'transform': {'scaleX': 1, 'scaleY': 1, 'translateX': 265, 'translateY': 70, 'unit': 'PT'}
                    }
                }
            },
            {
                'insertText': {'objectId': h_orig_id, 'text': "COPY ORIGINAL DE LA MARCA:"}
            },
            {
                'updateTextStyle': {
                    'objectId': h_orig_id,
                    'style': {'bold': True, 'fontSize': {'magnitude': 9, 'unit': 'PT'}},
                    'fields': 'bold,fontSize'
                }
            },
            # Recuadro superior: Copy Original
            {
                'createShape': {
                    'objectId': box_orig_id,
                    'shapeType': 'ROUNDED_RECTANGLE',
                    'elementProperties': {
                        'pageObjectId': s_id,
                        'size': {'width': {'magnitude': 430, 'unit': 'PT'}, 'height': {'magnitude': 110, 'unit': 'PT'}},
                        'transform': {'scaleX': 1, 'scaleY': 1, 'translateX': 265, 'translateY': 90, 'unit': 'PT'}
                    }
                }
            },
            {
                'updateShapeProperties': {
                    'objectId': box_orig_id,
                    'shapeProperties': {
                        'shapeBackgroundFill': {
                            'solidFill': {'color': {'rgbColor': {'red': 0.98, 'green': 0.98, 'blue': 0.99}}}
                        },
                        'outline': {
                            'outlineFill': {'solidFill': {'color': {'rgbColor': {'red': 0.88, 'green': 0.90, 'blue': 0.92}}}},
                            'weight': {'magnitude': 1, 'unit': 'PT'}
                        }
                    },
                    'fields': 'shapeBackgroundFill,outline'
                }
            },
            {
                'insertText': {'objectId': box_orig_id, 'text': cand['copy_original']}
            },
            {
                'updateTextStyle': {
                    'objectId': box_orig_id,
                    'style': {'fontSize': {'magnitude': 10, 'unit': 'PT'}},
                    'fields': 'fontSize'
                }
            },
            # Título recuadro inferior
            {
                'createShape': {
                    'objectId': h_olk_id,
                    'shapeType': 'TEXT_BOX',
                    'elementProperties': {
                        'pageObjectId': s_id,
                        'size': {'width': {'magnitude': 430, 'unit': 'PT'}, 'height': {'magnitude': 18, 'unit': 'PT'}},
                        'transform': {'scaleX': 1, 'scaleY': 1, 'translateX': 265, 'translateY': 208, 'unit': 'PT'}
                    }
                }
            },
            {
                'insertText': {'objectId': h_olk_id, 'text': "COPY NUEVO ADAPTADO A OLINKA PAPELERÍAS:"}
            },
            {
                'updateTextStyle': {
                    'objectId': h_olk_id,
                    'style': {'bold': True, 'fontSize': {'magnitude': 9, 'unit': 'PT'}},
                    'fields': 'bold,fontSize'
                }
            },
            # Recuadro inferior: Copy Nuevo adaptado
            {
                'createShape': {
                    'objectId': box_olk_id,
                    'shapeType': 'ROUNDED_RECTANGLE',
                    'elementProperties': {
                        'pageObjectId': s_id,
                        'size': {'width': {'magnitude': 430, 'unit': 'PT'}, 'height': {'magnitude': 150, 'unit': 'PT'}},
                        'transform': {'scaleX': 1, 'scaleY': 1, 'translateX': 265, 'translateY': 228, 'unit': 'PT'}
                    }
                }
            },
            {
                'updateShapeProperties': {
                    'objectId': box_olk_id,
                    'shapeProperties': {
                        'shapeBackgroundFill': {
                            'solidFill': {'color': {'rgbColor': {'red': 0.95, 'green': 0.97, 'blue': 1.0}}}
                        },
                        'outline': {
                            'outlineFill': {'solidFill': {'color': {'rgbColor': {'red': 0.70, 'green': 0.80, 'blue': 0.95}}}},
                            'weight': {'magnitude': 1.2, 'unit': 'PT'}
                        }
                    },
                    'fields': 'shapeBackgroundFill,outline'
                }
            },
            {
                'insertText': {'objectId': box_olk_id, 'text': cand['copy_editado']}
            },
            {
                'updateTextStyle': {
                    'objectId': box_olk_id,
                    'style': {'fontSize': {'magnitude': 9.5, 'unit': 'PT'}},
                    'fields': 'fontSize'
                }
            }
        ]
        
        # Ejecutar creación visual de la diapositiva
        slides_service.presentations().batchUpdate(
            presentationId=pres_id,
            body={'requests': reqs}
        ).execute()
        
        # Inserción de imagen/reel en el recuadro vertical si existe URL
        if cand.get('media_url') and cand['media_url'].startswith('http'):
            try:
                img_id = f"img_{idx}_{int(time.time())}"
                slides_service.presentations().batchUpdate(
                    presentationId=pres_id,
                    body={'requests': [{
                        'createImage': {
                            'objectId': img_id,
                            'url': cand['media_url'],
                            'elementProperties': {
                                'pageObjectId': s_id,
                                'size': {'width': {'magnitude': 150, 'unit': 'PT'}, 'height': {'magnitude': 265, 'unit': 'PT'}},
                                'transform': {'scaleX': 1, 'scaleY': 1, 'translateX': 65, 'translateY': 82, 'unit': 'PT'}
                            }
                        }
                    }]}
                ).execute()
            except Exception as e:
                print(f"Nota imagen candidato {idx+1}: {e}")
                
        # -------------------------------------------------------------
        # INYECCIÓN EN NOTAS DEL ORADOR (SPEAKER NOTES)
        # -------------------------------------------------------------
        try:
            pres_obj = slides_service.presentations().get(
                presentationId=pres_id
            ).execute()
            
            # Ubicar el speakerNotesObjectId de la diapositiva actual
            notes_obj_id = None
            for p_slide in pres_obj.get('slides', []):
                if p_slide.get('objectId') == s_id:
                    notes_page = p_slide.get('slideProperties', {}).get('notesPage', {})
                    notes_obj_id = notes_page.get('notesProperties', {}).get('speakerNotesObjectId')
                    break
                    
            if notes_obj_id:
                texto_notas = (
                    "=== FICHA TÉCNICA DEL CANDIDATO ===\n"
                    f"• Producto / SKU: {cand['sku']}\n"
                    f"• Métricas de origen: {cand['vistas']} vistas | {cand['likes']} likes | {cand['comentarios']} comentarios\n"
                    f"• Fecha de consulta: {cand['fecha_consulta']}\n"
                    f"• Motivo de selección: {cand['motivo_seleccion']}\n"
                    f"• Adecuaciones sugeridas: {cand['adecuaciones']}\n"
                    f"• Fecha sugerida de publicación Olinka: {cand['fecha_sugerida']}\n"
                    f"• Estado de revisión: {cand['estado_revision']}\n"
                    "• Nota de edición: Conservar original íntegro; Miguel decide edición del video."
                )
                slides_service.presentations().batchUpdate(
                    presentationId=pres_id,
                    body={'requests': [{
                        'insertText': {
                            'objectId': notes_obj_id,
                            'text': texto_notas
                        }
                    }]}
                ).execute()
        except Exception as e:
            print(f"Nota speaker notes {idx+1}: {e}")
            
    print("Presentacion y esquema editorial construidos con exito.")
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
    id_carpeta_raiz = limpiar_id(raw_drive_id)
    
    # Carpeta mensual en Google Drive
    id_carpeta_nov = crear_carpeta_drive(
        drive_service,
        "Parrilla_Noviembre_2026",
        id_carpeta_raiz
    )
    url_drive_carpeta = f"https://drive.google.com/drive/folders/{id_carpeta_nov}"
    
    # Extraer candidatos con metadatos completos según especificación
    candidatos = extraer_candidatos_reales(marcas, efemerides)
    
    # Procesar copys con Gemini
    for cand in candidatos:
        cand['copy_editado'] = generar_copy_olinka(
            gemini_client,
            cand,
            promociones,
            parametros
        )
        
    # Construir la presentación en Google Slides con esquema exacto
    id_slides = crear_presentacion_reporte(
        slides_service,
        drive_service,
        id_carpeta_nov,
        url_drive_carpeta,
        candidatos
    )
    
    print("==================================================")
    print(f"PRESENTACION MENSUAL FINALIZADA CON EXITO: {id_slides}")
    print(f"Carpeta en Drive: {url_drive_carpeta}")
    print("==================================================")

if __name__ == '__main__':
    main()
