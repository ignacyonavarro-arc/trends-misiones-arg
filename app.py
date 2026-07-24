import streamlit as st
import feedparser
from google import genai

# Configuración de página
st.set_page_config(page_title="trends misiones", page_icon="📈", layout="centered")

# Estilo visual minimalista (Plus Jakarta Sans + Fondo Blanco)
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
        margin-bottom: 25px;
    }
    
    .trend-card {
        background-color: #FAFAFA;
        border: 1px solid #F4F4F5;
        border-left: 4px solid #000000;
        padding: 16px 20px;
        margin-bottom: 12px;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    
    .trend-number {
        font-size: 13px;
        font-weight: 800;
        color: #EAB308;
        margin-right: 12px;
    }
    
    .trend-word {
        font-size: 18px;
        font-weight: 700;
        color: #09090B;
        text-transform: capitalize;
    }
    
    .trend-tag {
        font-size: 11px;
        font-weight: 600;
        color: #71717A;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="trends-header">trends misiones</div>', unsafe_allow_html=True)

# Lógica de obtención de clave segura
api_key = st.secrets.get("GEMINI_API_KEY") if "GEMINI_API_KEY" in st.secrets else st.sidebar.text_input("🔑 Gemini API Key", type="password")

FUENTES = [
    {"nombre": "Misiones Online", "url": "https://misionesonline.net/feed/"},
    {"nombre": "Primera Edición", "url": "https://www.primeraedicion.com.ar/feed/"},
    {"nombre": "Canal 12 Misiones", "url": "https://canal12misiones.com/feed/"},
    {"nombre": "El Territorio", "url": "https://news.google.com/rss/search?q=site:elterritorio.com.ar&hl=es-419&gl=AR&ceid=AR:es-419"},
    {"nombre": "Noticias de la Calle", "url": "https://news.google.com/rss/search?q=site:noticiasdelacalle.com.ar+OR+%22Noticias+de+la+Calle%22+Misiones&hl=es-419&gl=AR&ceid=AR:es-419"},
    {"nombre": "El Show de los Impactos", "url": "https://news.google.com/rss/search?q=%22El+Show+de+los+Impactos%22+Misiones&hl=es-419&gl=AR&ceid=AR:es-419"}
]

# Función de escaneo con caché inteligente de 30 minutos (ttl=1800)
@st.cache_data(ttl=1800)
def obtener_tendencias(key):
    titulares = []
    for f in FUENTES:
        try:
            feed = feedparser.parse(f["url"])
            for entry in feed.entries[:8]:
                titulares.append(entry.title)
        except:
            pass
            
    if not titulares:
        return []
        
    client = genai.Client(api_key=key)
    prompt = f"""
    Analiza los siguientes titulares de noticias actuales de la Provincia de Misiones:
    {'\n'.join(titulares)}

    Extrae exactamente las 5 PALABRAS O CONCEPTOS TEMÁTICOS MÁS MENCIONADOS Y SIGNIFICATIVOS en este momento.
    REGLAS:
    1. Palabras clave informativas (ej: Yerba, Passalacqua, Dengue, Colectivo, Cataratas, EMSA, Inflación, Frontera).
    2. NO incluyas palabras vacías ni conectores (como: de, la, el, en, misiones, posadas, hoy, noticias).
    3. Devuelve ÚNICAMENTE las 5 palabras, una por línea.
    """
    resp = client.models.generate_content(model='gemini-3.5-flash', contents=prompt)
    return [p.strip() for p in resp.text.strip().split("\n") if p.strip()][:5]

if api_key:
    try:
        palabras_top = obtener_tendencias(api_key)
        for i, palabra in enumerate(palabras_top, 1):
            st.markdown(f"""
                <div class="trend-card">
                    <div>
                        <span class="trend-number">0{i}</span>
                        <span class="trend-word">{palabra}</span>
                    </div>
                    <span class="trend-tag">en tendencia</span>
                </div>
            """, unsafe_allow_html=True)
    except Exception as e:
        st.error("Procesando tendencias...")
else:
    st.caption("Configurando servicio...")
