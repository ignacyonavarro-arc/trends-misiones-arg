import streamlit as st
import feedparser
import json
import os
import re
from google import genai

# Configuración de página minimalista
st.set_page_config(page_title="trends misiones", page_icon="📈", layout="centered")

# Estilo visual Plus Jakarta Sans + Mosaico Heatmap
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
        gap: 10px;
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
        min-height: 130px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.03);
    }
    
    .card-green {
        background-color: #16A34A;
        color: #FFFFFF;
    }
    
    .card-red {
        background-color: #DC2626;
        color: #FFFFFF;
    }
    
    .card-yellow {
        background-color: #FEF08A;
        color: #713F12;
        border: 1px solid #FDE047;
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
        margin-bottom: 15px;
        font-size: 12px;
        color: #71717A;
        font-weight: 500;
        letter-spacing: 0.5px;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="trends-header">trends misiones</div>', unsafe_allow_html=True)

api_key = st.secrets.get("GEMINI_API_KEY") if "GEMINI_API_KEY" in st.secrets else st.sidebar.text_input("🔑 Gemini API Key", type="password")

# LISTA COMPLETA DE 15 MEDIOS PERIODÍSTICOS DE MISIONES
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
                return json.load(f)
        except:
            return {}
    return {}

def guardar_historial(datos):
    try:
        with open(ARCH_HISTORIAL, "w") as f:
            json.dump(datos, f)
    except:
        pass

@st.cache_data(ttl=1200)
def obtener_tendencias(key):
    titulares = []
    for f in FUENTES:
        try:
            feed = feedparser.parse(f["url"])
            for entry in feed.entries[:6]:
                titulares.append(entry.title)
        except:
            pass
            
    if not titulares:
        return [], 0
        
    client = genai.Client(api_key=key)
    prompt = f"""
    Analiza los siguientes {len(titulares)} titulares de noticias actuales de Misiones:
    {'\n'.join(titulares)}

    Extrae exactamente las 5 PALABRAS O CONCEPTOS TEMÁTICOS MÁS MENCIONADOS Y SIGNIFICATIVOS en este momento y estima su cantidad de menciones.
    REGLAS:
    1. Palabras clave informativas de actualidad (ej: Yerba, Passalacqua, Dengue, Colectivo, Cataratas, EMSA, Inflación, Frontera).
    2. NO incluyas palabras vacías ni conectores (de, la, el, en, misiones, posadas, hoy, noticias).
    3. Devuelve la lista en este formato EXACTO por línea: Palabra, Menciones
    """
    resp = client.models.generate_content(model='gemini-3.5-flash', contents=prompt)
    
    resultados = []
    for linea in resp.text.strip().split("\n"):
        if "," in linea:
            partes = linea.split(",")
            p = partes[0].strip()
            try:
                cant = int(re.sub(r'\D', '', partes[1]))
            except:
                cant = 1
            if p:
                resultados.append((p, cant))
                
    return resultados[:5], len(titulares)

if api_key:
    try:
        datos_top, total_muestras = obtener_tendencias(api_key)
        historial = cargar_historial()
        
        umbral_10 = max(1, int(total_muestras * 0.10))
        sum_menciones = sum(cant for _, cant in datos_top) if datos_top else 1
        nuevo_historial = {}

        flex_sizes = ["flex: 2 1 58%;", "flex: 1 1 38%;", "flex: 1 1 30%;", "flex: 1 1 30%;", "flex: 1 1 30%;"]

        html_mosaico = '<div class="mosaic-container">'

        for i, (palabra, cant_actual) in enumerate(datos_top):
            cant_previa = historial.get(palabra.lower(), None)
            
            if cant_previa is None:
                diferencia = cant_actual
            else:
                diferencia = cant_actual - cant_previa

            pct_participacion = int((cant_actual / sum_menciones) * 100)

            if diferencia >= umbral_10:
                clase_color = "card-green"
                icono = "▲"
                var_texto = f"+{pct_participacion}%"
            elif diferencia <= -umbral_10:
                clase_color = "card-red"
                icono = "▼"
                var_texto = f"-{pct_participacion}%"
            else:
                clase_color = "card-yellow"
                icono = "="
                var_texto = f"{pct_participacion}%"

            flex_style = flex_sizes[i] if i < len(flex_sizes) else "flex: 1 1 30%;"

            nuevo_historial[palabra.lower()] = cant_actual

            # HTML en una sola línea limpia sin sangría
            card_html = f'<div class="mosaic-card {clase_color}" style="{flex_style}"><div class="card-title">{palabra}</div><div class="card-meta"><span>{var_texto}</span><span>{icono}</span></div></div>'
            html_mosaico += card_html

        html_mosaico += '</div>'
        
        # Renderizar Mosaico
        st.markdown(html_mosaico, unsafe_allow_html=True)
        
        # Pie de página OBLICUA
        st.markdown('<div class="oblicua-footer">Impulsado por Oblicua Comunicación</div>', unsafe_allow_html=True)

        guardar_historial(nuevo_historial)

    except Exception as e:
        st.error("Actualizando mosaico de tendencias...")
