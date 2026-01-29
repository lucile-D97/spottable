import streamlit as st
import pandas as pd
import pydeck as pdk
import re

# 1. Configuration de la page
st.set_page_config(page_title="Mes spots", layout="wide")

# Initialisation des variables d'état (Session State)
if 'view_state' not in st.session_state:
    st.session_state.view_state = pdk.ViewState(latitude=48.8566, longitude=2.3522, zoom=12, pitch=0)

# 2. Style CSS
st.markdown(f"""
    <style>
    .stApp {{ background-color: #efede1 !important; }}
    header[data-testid="stHeader"] {{ display: none !important; }}
    .main .block-container {{ padding-top: 2rem !important; }}
    .deckgl-wrapper {{ cursor: pointer !important; }}
    h1 {{ color: #d92644 !important; margin-top: -30px !important; }}
    html, body, [class*="st-"], p, div, span, label, h3 {{ color: #202b24 !important; }}
    div[data-testid="stExpander"] {{ background-color: #efede1 !important; border: 0.5px solid #b6beb1 !important; border-radius: 8px !important; margin-bottom: 10px !important; }}
    .stLinkButton a {{ background-color: #7397a3 !important; color: #efede1 !important; border-radius: 8px !important; font-weight: bold !important; display: flex !important; justify-content: center !important; }}
    .tag-label {{ display: inline-block; background-color: #b6beb1; color: #202b24; padding: 2px 10px; border-radius: 15px; margin-right: 5px; font-size: 0.75rem; font-weight: bold; }}
    </style>
    """, unsafe_allow_html=True)

def get_precise_coords(url):
    if pd.isna(url): return None, None
    match = re.search(r'@(-?\d+\.\d+),(-?\d+\.\d+)', str(url))
    if match: return float(match.group(1)), float(match.group(2))
    return None, None

st.title("Mes spots")

try:
    df = pd.read_csv("Spottable v3.csv", sep=None, engine='python')
    df.columns = df.columns.str.strip().str.lower()
    
    lat_col = next((c for c in df.columns if c in ['latitude', 'lat']), None)
    lon_col = next((c for c in df.columns if c in ['longitude', 'lon']), None)
    c_link = next((c for c in df.columns if any(w in c for w in ['map', 'lien', 'geo'])), None)
    col_tags = next((c for c in df.columns if c == 'tags'), None)

    if lat_col and lon_col:
        df['lat'] = pd.to_numeric(df[lat_col].astype(str).str.replace(',', '.'), errors='coerce')
        df['lon'] = pd.to_numeric(df[lon_col].astype(str).str.replace(',', '.'), errors='coerce')

    if c_link:
        df['precise_tuple'] = df[c_link].apply(get_precise_coords)
        df['lat'] = df.apply(lambda r: r['precise_tuple'][0] if r['precise_tuple'][0] else r['lat'], axis=1)
        df['lon'] = df.apply(lambda r: r['precise_tuple'][1] if r['precise_tuple'][1] else r['lon'], axis=1)

    df = df.dropna(subset=['lat', 'lon']).reset_index(drop=True)
    c_name = next((c for c in df.columns if c in ['name', 'nom']), df.columns[0])
    c_addr = next((c for c in df.columns if c in ['address', 'adresse']), df.columns[1])

    # --- RECHERCHE ET FILTRES ---
    col_search, _ = st.columns([1, 2])
    with col_search:
        search_query = st.text_input("Rechercher", placeholder="Rechercher un spot", label_visibility="collapsed")
    df_filtered = df[df[c_name].str.contains(search_query, case=False, na=False)].copy()

    # --- AFFICHAGE ---
    col1, col2 = st.columns([2, 1])

    with col1:
        layer = pdk.Layer(
            "ScatterplotLayer",
            data=df_filtered,
            get_position=["lon", "lat"],
            get_color=[217, 38, 68, 200], 
            get_radius=80, 
            pickable=True,
            auto_highlight=True, 
            highlight_color=[0, 0, 0, 255]
        )

        # On capture la sélection
        map_widget = st.pydeck_chart(pdk.Deck(
            map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
            initial_view_state=st.session_state.view_state,
            layers=[layer],
            tooltip={"html": f"<b>{{{c_name}}}</b>"}
        ), on_select="rerun", selection_mode="single-object")

    with col2:
        # TEST ACTION : Est-ce qu'on récupère quelque chose au clic ?
        selection = map_widget.selection.get("objects", [])
        
        if selection:
            # ACTION VISIBLE DE TEST
            st.success(f"📍 Spot sélectionné : {selection[0][c_name]}")
            
            clicked_spot = selection[0]
            df_display = df_filtered[df_filtered[c_name] == clicked_spot[c_name]]
            
            if st.button("Tout réafficher ↺", use_container_width=True):
                st.rerun()
        else:
            df_display = df_filtered.head(50)
            st.write(f"*{len(df_filtered)} spots trouvés (Top 50)*")

        for _, row in df_display.iterrows():
            with st.expander(f"**{row[c_name]}**", expanded=len(selection) > 0):
                st.write(f"📍 {row[c_addr]}")
                if c_link and pd.notna(row[col_tags] if col_tags else None):
                    tags_html = "".join([f'<span class="tag-label">{t.strip()}</span>' for t in str(row[col_tags]).split(',')])
                    st.markdown(tags_html, unsafe_allow_html=True)
                if c_link and pd.notna(row[c_link]):
                    st.link_button("**Y aller**", row[c_link], use_container_width=True)

except Exception as e:
    st.error(f"Erreur : {e}")
