import streamlit as st
import pandas as pd
import pydeck as pdk

# 1. Configuration de la page
st.set_page_config(page_title="Mes spots", layout="wide")

# 2. Style CSS (Nettoyé et mis à jour avec la couleur #202b24)
st.markdown(f"""
    <style>
    /* Fond de l'application */
    .stApp {{
        background-color: #efe6d8 !important;
    }}
    
    /* SUPPRESSION DU HEADER */
    header[data-testid="stHeader"] {{
        display: none !important;
    }}
    
    div[data-testid="stDecoration"] {{
        display: none !important;
    }}

    .main .block-container {{
        padding-top: 2rem !important;
    }}

    /* Titre */
    h1 {{
        color: #d92644 !important;
        margin-top: -30px !important;
    }}

    /* TEXTE GLOBAL : Application de votre couleur #202b24 */
    html, body, [class*="st-"], p, div, span, label, h3 {{
        color: #202b24 !important;
    }}

    /* Barre de recherche */
    div[data-testid="stTextInput"] div[data-baseweb="input"] {{
        background-color: #b6beb1 !important;
        border: none !important;
    }}
    
    div[data-testid="stTextInput"] input {{
        color: #202b24 !important;
        -webkit-text-fill-color: #202b24 !important;
    }}

    /* Expanders */
    div[data-testid="stExpander"] {{
        background-color: #f8e6d2 !important;
        border: none !important;
        border-radius: 8px !important;
    }}

    /* Bouton Y aller */
    .stLinkButton a {{
        background-color: #7397a3 !important;
        color: #202b24 !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: bold !important;
        text-decoration: none !important;
        display: flex !important;
        justify-content: center !important;
    }}
    
    /* Forcer la couleur du texte à l'intérieur du bouton */
    .stLinkButton a span, .stLinkButton a p {{
        color: #202b24 !important;
    }}

    /* Tags et Toggles */
    .tag-label {{
        display: inline-block;
        background-color: #b6beb1;
        color: #202b24; /* Texte des tags */
        padding: 2px 10px;
        border-radius: 15px;
        margin-right: 5px;
        font-size: 0.75rem;
        font-weight: bold;
    }}
    
    /* Rail du switch (Toggles) */
    div[data-testid="stWidgetLabel"] + div div[role="switch"] {{
        background-color: #91222c !important;
    }}
    /* Couleur quand activé */
    div[data-testid="stWidgetLabel"] + div div[aria-checked="true"] {{
        background-color: #d92644 !important;
    }}
    </style>
    """, unsafe_allow_html=True)

st.title("Mes spots")

# 3. Chargement et Traitement des Données
try:
    df = pd.read_csv("Spottable v2.csv", sep=None, engine='python')
    df.columns = df.columns.str.strip().str.lower()
    df = df.rename(columns={'latitude': 'lat', 'longitude': 'lon'})
    df['lat'] = pd.to_numeric(df['lat'], errors='coerce')
    df['lon'] = pd.to_numeric(df['lon'], errors='coerce')

    c_name = next((c for c in df.columns if c.lower() in ['name', 'nom']), df.columns[0])
    c_addr = next((c for c in df.columns if c.lower() in ['address', 'adresse']), df.columns[1])
    col_tags = next((c for c in df.columns if c.lower() == 'tags'), None)

    # --- RECHERCHE ---
    col_search, _ = st.columns([1, 2])
    with col_search:
        search_query = st.text_input("Rechercher", placeholder="Rechercher
