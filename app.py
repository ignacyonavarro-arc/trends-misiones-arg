import streamlit as st
import feedparser
import json
import os
import re
from datetime import datetime
import pandas as pd
from google import genai

# Configuración de página minimalista
st.set_page_config(page_title="trends misiones", page_icon="📈", layout="centered")

# Estilo visual Plus Jakarta Sans + Mosaico Balanceado en Tonos de Amarillo
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');
    
    html, body, [class*="css"], .stApp {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        background-color: #FFFFFF !important;
        color: #0A0A0A !important;
    }
    
    #MainMenu, header, footer {visibility: hidden;}
    
    .trends-header {
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 28px;
        font-weight: 700;
        color: #000000;
        letter-spacing: -0.5px;
        text-transform: lowercase;
        margin-top: 5px;
        margin-bottom: 20px;
    }
    
    .mosaic-container {
        display: flex;
        flex-wrap: wrap;
        gap: 12px;
        width: 100%;
        margin-top: 10px;
    }
    
    .mosaic-card {
        border-radius: 12px;
        padding: 18px 20px;
        box-sizing: border-box;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        min-height: 125px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.03);
    }
    
    /* ESCALA CROMÁTICA EN TONOS DE AMARILLO */
    .card-yellow-dark {
        background-color: #EAB308; /* Dorado / Amarillo Intenso (▲ Creciente) */
        color: #000000;
        border: 1px solid #CA8A04;
    }
    
    .card-yellow-mid {
        background-color: #FEF08A; /* Amarillo Suave / Medio (= Estable) */
        color: #713F12;
        border: 1px solid #FDE047;
    }
    
    .card-yellow-light {
        background-color: #FEF9C3; /* Amarillo Pálido / Claro (▼ Decreciente) */
        color: #854D0E;
        border: 1px solid #FEF08A;
    }
    
    .card-title {
        font-size: 22px;
        font-weight: 800;
        letter-spacing: -0.5px;
        line-height: 1.1;
        text-transform: capitalize;
    }
    
    .card-meta {
        font-size: 14px;
        font-weight: 800;
        display: flex;
        align-items: center;
        gap: 6px;
        margin-top: 15px;
    }
    
    .oblicua-footer {
        text-align: center;
        margin-top: 35px;
        margin-bottom: 10px;
        font-size: 12px;
        color: #71717A;
        font-weight: 500;
        letter-spacing: 0.5px;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="trends-header">trends misiones</div>', unsafe_allow_html=True)

api_key = st.secrets.get("GEMINI_API_KEY") if "GEMINI_API_KEY" in st.secrets else st.sidebar.text_input("🔑 Gemini API Key", type="password")

FUENTES = [
    {"nombre": "Misiones Online", "url": "https://misionesonline.net/feed/"},
    {"nombre": "Primera Edición", "url": "https://www.primeraedicion.com.ar/feed/"},
    {"nombre": "Canal 12 Misiones", "url": "https://canal12misiones.com/feed/"},
    {"nombre": "El Territorio", "url": "https://news.google.com/rss/search?q=site:elterritorio.com.ar&hl=es-419&gl=AR&ceid=AR:es-419"},
    {"nombre": "Noticias de la Calle", "url": "https://news.google.com/rss/search?q=site:noticiasdelacalle.com.ar+OR+%22Noticias+de+la+Calle%22+Misiones&hl=es-419&gl=AR&ceid=AR:es-419"},
    {"nombre": "El Show de los Impactos", "url": "https://news.google.com/rss/search?q=%22El+Show+de+los+Impactos%22+Misiones&hl=es-419&gl=AR&ceid=AR:es-419"},
    {"nombre": "La Voz de Misiones", "url": "https://news.google.com/rss/search?q=site:lavozdemisiones.com&hl=es-419&gl=AR&ceid=AR:es-419"},
    {"nombre": "Economis", "url": "https://news.google.com/rss/search?q=site:economis.com.ar&hl=es-419&gl=AR&ceid=AR:es-419"},
    {"nombre": "La Voz de Cataratas", "url": "https://news.google.com/rss/search?q=site:lavozdecataratas.com&hl=es-419&gl=AR&ceid=AR:es-419"},
    {"nombre": "Norte Misionero", "url": "https://news.google.com/rss/search?q=site:nortemisionero.com.ar&hl=es-419&gl=AR&ceid=AR:es-419"},
    {"nombre": "Oberá Online", "url": "https://news.google.com/rss/search?q=site:oberaonline.com.ar&hl=es-419&gl=AR&ceid=AR:es-419"},
    {"nombre": "La Misión Digital", "url": "https://news.google.com/rss/search?q=site:lamisiondigital.com&hl=es-419&gl=AR&ceid=AR:es-419"},
    {"nombre": "Revista Códigos", "url": "https://news.google.com/rss/search?q=site:revistacodigos.com&hl=es-419&gl=AR&ceid=AR:es-419"},
    {"nombre": "Misiones Cuatro", "url": "https://news.google.com/rss/search?q=site:misionescuatro.com&hl=es-419&gl=AR&ceid=AR:es-419"},
    {"nombre": "Plan B Misiones", "url": "https://news.google.com/rss/search?q=site:planbmisiones.com&hl=es-419&gl=AR&ceid=AR:es-419"}
]

ARCH_HISTORIAL = "historial_tendencias.json"

def cargar_historial():
    if os.path.exists(ARCH_HISTORIAL):
        try:
            with open(ARCH_HISTORIAL, "r") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
                elif isinstance(data, dict):
                    return [{"timestamp": "anterior", "palabras": data}]
        except:
            return []
    return []

def guardar_historial(historial_lista):
    try:
        with open(ARCH_HISTORIAL, "w") as f:
            json.dump(historial_lista, f)
    except:
        pass

@st.cache_data(ttl=1200)
def ejecutar_medicion_real(key):
    titulares_log = []
    hora_chequeo = datetime.now().strftime("%d/%m/%Y %H:%M hs")
    
    for f in FUENTES:
        try:
            feed = feedparser.parse(f["url"])
            for entry in feed.entries[:8]:
                if hasattr(entry, 'title') and entry.title:
                    # LIMPIEZA DE MARCAS DE AGUA DE DIARIOS (ej: " - Revista Códigos")
                    titulo_limpio = re.sub(r'\s*[\-\|]\s*.*$', '', entry.title).strip()
                    if titulo_limpio:
                        titulares_log.append({
                            "Fecha/Hora": hora_chequeo,
                            "Medio": f["nombre"],
                            "Titular Real": titulo_limpio
                        })
        except:
            pass
            
    if not titulares_log:
        return [], 0, []
        
    texto_titulares = "\n".join([item["Titular Real"] for item in titulares_log])
    
    client = genai.Client(api_key=key)
    prompt = f"""
    Analiza los siguientes {len(titulares_log)} titulares de la portada actual de medios de Misiones:
    {texto_titulares}

    Extrae exactamente las 5 PALABRAS O CONCEPTOS TEMÁTICOS MÁS MENCIONADOS Y RECURRENTES en la coyuntura informativa actual de la provincia.
    
    REGLAS DE FILTRADO EXTREMO (SÚPER IMPORTANTE):
    1. PROHIBIDO TOTALMENTE NOMBRES DE MEDIOS Y MARCAS: No incluyas "Revista", "Códigos", "Norte", "Misionero", "Digital", "Plan", "Misión", "Calle", "Impactos", "Cuatro", "Voz", "Canal", "Primera", "Edición", "Online", "Territorio".
    2. PROHIBIDO PALABRAS PAÍS / NACIONES GENÉRICAS / DÍAS: No incluyas "Argentina", "Misiones", "Posadas", "Provincia", "Nacional", "Nuevo", "Grande", "Hoy", "Día", "Jueves", "Viernes".
    3. SELECCIONA ÚNICAMENTE CONCEPTOS O TÉRMINOS CON VALOR COYUNTURAL REAL: Nombres propios de figuras (ej: Passalacqua, Rovira, Milei), temas o problemáticas (ej: Yerba, Cataratas, Crecida, Dengue, EMSA, Colectivo, Inundación, Ruta 12, Tarifa, Gabinete).
    
    Devuelve CADA RESULTADO EN UNA LÍNEA CON ESTE FORMATO EXACTO: Palabra, Menciones
    """
    
    modelos = ['gemini-2.5-flash', 'gemini-1.5-flash', 'gemini-2.0-flash']
    raw_text = ""
    for m in modelos:
        try:
            resp = client.models.generate_content(model=m, contents=prompt)
            if resp and resp.text:
                raw_text = resp.text
                break
        except:
            continue

    resultados = []
    prohibidas = {
        'revista', 'codigos', 'misionero', 'norte', 'digital', 'plan', 'mision', 
        'calle', 'impactos', 'cuatro', 'voz', 'canal', 'primera', 'edicion', 
        'online', 'territorio', 'misiones', 'posadas', 'provincia', 'nuevo', 
        'grande', 'diario', 'noticias', 'argentina', 'nacional', 'jueves', 'viernes', 'sabado', 'domingo'
    }
    
    if raw_text:
        for line in raw_text.strip().split("\n"):
            cleaned = re.sub(r'^[\*\-\d\.\s]+', '', line).replace('*', '').strip()
            p = ""
            cant = 1
            if ',' in cleaned:
                partes = cleaned.split(',')
                p = partes[0].strip()
                m_num = re.search(r'\d+', partes[1])
                cant = int(m_num.group()) if m_num else 1
            elif ':' in cleaned:
                partes = cleaned.split(':')
                p = partes[0].strip()
                m_num = re.search(r'\d+', partes[1])
                cant = int(m_num.group()) if m_num else 1
                
            if p and len(p) > 2 and p.lower() not in prohibidas:
                resultados.append((p.capitalize(), cant))

    # Respaldo seguro si faltan palabras
    if len(resultados) < 5:
        palabras_sueltas = re.findall(r'\b[A-ZÁÉÍÓÚÑ][a-záéíóúñ]{3,}\b', texto_titulares)
        conteo_py = {}
        for w in palabras_sueltas:
            if w.lower() not in prohibidas:
                conteo_py[w] = conteo_py.get(w, 0) + 1
        top_py = sorted(conteo_py.items(), key=lambda x: x[1], reverse=True)
        for p, c in top_py:
            if p.capitalize() not in [item[0] for item in resultados]:
                resultados.append((p.capitalize(), c))
                if len(resultados) >= 5:
                    break

    return resultados[:5], len(titulares_log), titulares_log

if api_key:
    try:
        datos_top, total_muestras, registro_titulares = ejecutar_medicion_real(api_key)
        
        if not datos_top:
            st.error("No se pudieron cargar titulares en este momento.")
        else:
            historial_lista = cargar_historial()
            
            medicion_anterior = {}
            if historial_lista and len(historial_lista) > 0:
                elem = historial_lista[-1]
                if isinstance(elem, dict):
                    medicion_anterior = elem.get("palabras", {})

            sum_menciones = sum(cant for _, cant in datos_top) if datos_top else 1
            medicion_actual_dict = {}
            
            # FORMATO DE MOSAICO BALANCEADO 2 FILAS (2 Cajas arriba, 3 Cajas abajo)
            flex_sizes = [
                "flex: 1 1 55%;",  # Caja #1 (Fila 1, Izquierda - Grande)
                "flex: 1 1 40%;",  # Caja #2 (Fila 1, Derecha - Mediana)
                "flex: 1 1 30%;",  # Caja #3 (Fila 2, Izquierda)
                "flex: 1 1 30%;",  # Caja #4 (Fila 2, Centro)
                "flex: 1 1 30%;"   # Caja #5 (Fila 2, Derecha)
            ]

            html_mosaico = '<div class="mosaic-container">'

            for i, (palabra, cant_actual) in enumerate(datos_top):
                p_key = palabra.lower()
                cant_previa = medicion_anterior.get(p_key, None)
                
                if cant_previa is None:
                    diferencia = 1
                else:
                    diferencia = cant_actual - cant_previa

                pct_participacion = int((cant_actual / sum_menciones) * 100)

                # ASIGNACIÓN DE COLOR Y FLECHAS SEGÚN VARIACIÓN Y POSICIÓN
                if diferencia > 0 or i < 2:
                    clase_color = "card-yellow-dark"  # Dorado Intenso ▲ (Top / Creciente)
                    icono = "▲"
                    var_texto = f"+{pct_participacion}%"
                elif diferencia < 0 or i == 4:
                    clase_color = "card-yellow-light" # Amarillo Claro ▼ (Decreciente)
                    icono = "▼"
                    var_texto = f"-{pct_participacion}%"
                else:
                    clase_color = "card-yellow-mid"   # Amarillo Medio = (Estable)
                    icono = "="
                    var_texto = f"{pct_participacion}%"

                flex_style = flex_sizes[i] if i < len(flex_sizes) else "flex: 1 1 30%;"
                medicion_actual_dict[p_key] = cant_actual

                card_html = f'<div class="mosaic-card {clase_color}" style="{flex_style}"><div class="card-title">{palabra}</div><div class="card-meta"><span>{var_texto}</span><span>{icono}</span></div></div>'
                html_mosaico += card_html

            html_mosaico += '</div>'

            st.markdown(html_mosaico, unsafe_allow_html=True)
            st.markdown('<div class="oblicua-footer">Impulsado por Oblicua Comunicación</div>', unsafe_allow_html=True)

            if not medicion_anterior or medicion_actual_dict != medicion_anterior:
                nueva_entrada = {
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "palabras": medicion_actual_dict
                }
                historial_lista.append(nueva_entrada)
                guardar_historial(historial_lista[-10:])

            with st.expander("🔍 Auditoría de Veracidad: Ver titulares y horarios consultados", expanded=False):
                st.caption(f"Medición realizada el **{datetime.now().strftime('%d/%m/%Y a las %H:%M hs')}** sobre **{total_muestras} titulares reales** de 15 medios periodísticos de Misiones.")
                st.dataframe(registro_titulares, use_container_width=True)

    except Exception as e:
        st.error(f"Actualizando tendencias... ({e})")
