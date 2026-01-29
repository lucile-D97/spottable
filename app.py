import streamlit as st
import pandas as pd
import pydeck as pdk
import re

# 1. Configuration de la page
st.set_page_config(page_title="Mes spots", layout="wide")

# 2. Style CSS
st.markdown(f"""
    <style>
    .stApp {{ background-color: #efede1 !important; }}
    header[data-testid="stHeader"] {{ display: none !important; }}
    div[data-testid="stDecoration"] {{ display: none !important; }}
    .main .block-container {{ padding-top: 2rem !important; }}

    h1 {{ color: #d92644 !important; margin-top: -30px !important; }}
    html, body, [class*="st-"], p, div, span, label, h3 {{ color: #202b24 !important; }}

    div[data-testid="stExpander"] {{
        background-color: #efede1 !important;
        border: 0.5px solid #b6beb1 !important;
        border-radius: 8px !important;
        margin-bottom: 10px !important;
    }}
    div[data-testid="stExpander"] summary:hover {{ background-color: #b6beb1 !important; }}
    div[data-testid="stExpander"] details[open] summary {{
        background-color: #b6beb1 !important;
        border-bottom: 1px solid #b6beb1 !important;
    }}

    div[data-testid="stTextInput"] div[data-baseweb="input"] {{ background-color: #b6beb1 !important; border: none !important; }}
    div[data-testid="stTextInput"] input {{ color: #202b24 !important; -webkit-text-fill-color: #202b24 !important; }}

    .stLinkButton a {{ 
        background-color: #7397a3 !important; 
        color: #efede1 !important; 
        border: none !important; 
        border-radius: 8px !important; 
        font-weight: bold !important; 
        text-decoration: none !important;
        display: flex !important;
        justify-content: center !important;
    }}
    </style>
    """, unsafe_allow_html=True)

def get_precise_coords(url):
    if pd.isna(url): return None, None
    match = re.search(r'@(-?\d+\.\d+),(-?\d+\.\d+)', str(url))
    if match: return float(match.group(1)), float(match.group(2))
    return None, None

st.title("Mes spots")

try:
    # 3. Chargement des Données
    df = pd.read_csv("Spottable v3.csv", sep=None, engine='python')
    df.columns = df.columns.str.strip().str.lower()
    
    lat_col = next((c for c in df.columns if c in ['latitude', 'lat']), None)
    lon_col = next((c for c in df.columns if c in ['longitude', 'lon']), None)
    c_link = next((c for c in df.columns if any(w in c for w in ['map', 'lien', 'geo'])), None)

    if lat_col and lon_col:
        df['lat'] = pd.to_numeric(df[lat_col].astype(str).str.replace(',', '.'), errors='coerce')
        df['lon'] = pd.to_numeric(df[lon_col].astype(str).str.replace(',', '.'), errors='coerce')

    if c_link:
        df['precise_tuple'] = df[c_link].apply(get_precise_coords)
        df['lat'] = df.apply(lambda r: r['precise_tuple'][0] if r['precise_tuple'][0] else r['lat'], axis=1)
        df['lon'] = df.apply(lambda r: r['precise_tuple'][1] if r['precise_tuple'][1] else r['lon'], axis=1)

    df = df.dropna(subset=['lat', 'lon'])
    c_name = next((c for c in df.columns if c in ['name', 'nom']), df.columns[0])
    c_addr = next((c for c in df.columns if c in ['address', 'adresse']), df.columns[1])

    # Initialisation de l'état de recherche si non présent
    if "search_query" not in st.session_state:
        st.session_state.search_query = ""

    col_search, _ = st.columns([1, 2])
    with col_search:
        search_input = st.text_input("Rechercher", value=st.session_state.search_query, placeholder="Rechercher un spot", label_visibility="collapsed")
        st.session_state.search_query = search_input

    df_filtered = df[df[c_name].str.contains(st.session_state.search_query, case=False, na=False)].copy()

    # --- AFFICHAGE ---
    col1, col2 = st.columns([2, 1])

    with col1:
        view_state = pdk.ViewState(latitude=48.8566, longitude=2.3522, zoom=12, pitch=0)

        icon_config = {
            "url": "https://img.icons8.com/ios-filled/100/d92644/marker.png",
            "width": 100, "height": 100, "anchorY": 100
        }
        df_filtered["icon_data"] = [icon_config for _ in range(len(df_filtered))]

        layer = pdk.Layer(
            "IconLayer",
            data=df_filtered,
            get_icon="icon_data",
            get_size=2.5,
            size_scale=8,
            get_position=["lon", "lat"],
            pickable=True,
            collision_enabled=True,
            collision_group="spots"
        )

        # On capture la sélection de la carte
        map_selection = st.pydeck_chart(
            pdk.Deck(
                map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
                initial_view_state=view_state,
                layers=[layer],
                tooltip={
                    "html": f"<div style='color: #202b24;'><b>{{{c_name}}}</b></div>",
                    "style": {
                        "backgroundColor": "#efede1",
                        "color": "#202b24",
                        "fontFamily": "sans-serif",
                        "fontSize": "14px",
                        "padding": "10px",
                        "borderRadius": "8px",
                        "boxShadow": "0px 2px 6px rgba(0,0,0,0.1)" 
                    }
                }
            ),
            on_select="rerun", # Relance le script lors d'un clic
            selection_mode="single" # Un seul point à la fois
        )

    with col2:
        # Logique de filtrage par clic
        selected_indices = map_selection.get("selection", {}).get("indices", [])
        
        if selected_indices:
            # On ne garde que l'élément cliqué
            df_display = df_filtered.iloc[selected_indices]
            if st.button("Tout réafficher ↺", use_container_width=True):
                st.rerun()
        else:
            df_display = df_filtered.head(50)
            st.write(f"*{len(df_filtered)} spots trouvés (Top 50)*")

        for _, row in df_display.iterrows():
            with st.expander(f"**{row[c_name]}**", expanded=bool(selected_indices)):
                st.write(f"📍 {row[c_addr]}")
                if c_link and pd.notna(row[c_link]):
                    st.link_button("**Y aller**", row[c_link], use_container_width=True)

except Exception as e:
    st.error(f"Erreur : {e}")
