import streamlit as st
import pandas as pd
import pydeck as pdk
import re

st.set_page_config(page_title="Mes spots", layout="wide")

# Initialisation de la vue
if 'view_state' not in st.session_state:
    st.session_state.view_state = pdk.ViewState(latitude=48.8566, longitude=2.3522, zoom=12)

# CSS pour le curseur
st.markdown("""
    <style>
    .stApp { background-color: #efede1 !important; }
    header[data-testid="stHeader"] { display: none !important; }
    .main .block-container { padding-top: 2rem !important; }
    
    /* On force le pointeur sur TOUTE la carte pour être sûr */
    .deckgl-wrapper, .deckgl-overlay { cursor: pointer !important; }
    
    h1 { color: #d92644 !important; margin-top: -30px !important; }
    div[data-testid="stExpander"] { background-color: #efede1 !important; border: 0.5px solid #b6beb1 !important; border-radius: 8px !important; }
    .stLinkButton a { background-color: #7397a3 !important; color: #efede1 !important; border-radius: 8px !important; font-weight: bold !important; display: flex; justify-content: center; }
    </style>
    """, unsafe_allow_html=True)

try:
    df = pd.read_csv("Spottable v3.csv", sep=None, engine='python')
    df.columns = df.columns.str.strip().str.lower()
    
    # Nettoyage coordonnées (Latitude/Longitude)
    lat_col = next((c for c in df.columns if c in ['latitude', 'lat']), None)
    lon_col = next((c for c in df.columns if c in ['longitude', 'lon']), None)
    c_link = next((c for c in df.columns if any(w in c for w in ['map', 'lien', 'geo'])), None)
    
    if lat_col and lon_col:
        df['lat'] = pd.to_numeric(df[lat_col].astype(str).str.replace(',', '.'), errors='coerce')
        df['lon'] = pd.to_numeric(df[lon_col].astype(str).str.replace(',', '.'), errors='coerce')
    df = df.dropna(subset=['lat', 'lon']).reset_index(drop=True)
    c_name = next((c for c in df.columns if c in ['name', 'nom']), df.columns[0])
    c_addr = next((c for c in df.columns if c in ['address', 'adresse']), df.columns[1])

    # Barre de recherche
    search_query = st.text_input("Rechercher", placeholder="Nom du spot", label_visibility="collapsed")
    df_filtered = df[df[c_name].str.contains(search_query, case=False, na=False)].copy()

    col1, col2 = st.columns([2, 1])

    with col1:
        # 1. LA COUCHE VISUELLE (Les pins rouges)
        icon_data = {"url": "https://img.icons8.com/ios-filled/100/d92644/marker.png", "width": 100, "height": 100, "anchorY": 100}
        df_filtered["icon_data"] = [icon_data for _ in range(len(df_filtered))]
        
        icon_layer = pdk.Layer(
            "IconLayer",
            data=df_filtered,
            get_icon="icon_data",
            get_size=3,
            size_scale=10,
            get_position=["lon", "lat"],
            pickable=False # On laisse la couche invisible gérer le clic
        )

        # 2. LA COUCHE INVISIBLE MAIS CLIQUABLE (Plus sensible)
        click_layer = pdk.Layer(
            "ScatterplotLayer",
            data=df_filtered,
            get_position=["lon", "lat"],
            get_radius=30, # Rayon de clic généreux
            get_fill_color=[0, 0, 0, 0], # TOTALEMENT INVISIBLE
            pickable=True,
        )

        # Création de la carte
        deck = pdk.Deck(
            map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
            initial_view_state=st.session_state.view_state,
            layers=[icon_layer, click_layer],
            tooltip={
                "html": f"<div style='color: #202b24;'><b>{{{c_name}}}</b></div>",
                "style": {"backgroundColor": "#efede1", "color": "#202b24", "padding": "10px", "borderRadius": "8px", "boxShadow": "0px 2px 6px rgba(0,0,0,0.1)"}
            }
        )

        # Capture de l'évènement
        selection = st.pydeck_chart(deck, on_select="rerun", selection_mode="single-object")

    with col2:
        # Logique de clic et zoom
        selected = selection.selection.get("objects", [])
        
        if selected:
            clicked_spot = selected[0]
            # ON FORCE LE ZOOM DANS LE SESSION STATE
            st.session_state.view_state = pdk.ViewState(
                latitude=clicked_spot['lat'],
                longitude=clicked_spot['lon'],
                zoom=16,
                pitch=0
            )
            
            st.button("Afficher tous les spots ↺", on_click=lambda: st.session_state.update({"view_state": pdk.ViewState(latitude=48.8566, longitude=2.3522, zoom=12)}))
            
            # Affichage de l'expander unique
            with st.expander(f"**{clicked_spot[c_name]}**", expanded=True):
                st.write(f"📍 {clicked_spot[c_addr]}")
                if c_link and pd.notna(clicked_spot.get(c_link)):
                    st.link_button("**Y aller**", clicked_spot[c_link], use_container_width=True)
        else:
            st.write(f"*{len(df_filtered)} spots trouvés*")
            for _, row in df_filtered.head(30).iterrows():
                with st.expander(f"**{row[c_name]}**"):
                    st.write(f"📍 {row[c_addr]}")
                    if c_link and pd.notna(row[c_link]):
                        st.link_button("**Y aller**", row[c_link], use_container_width=True)

except Exception as e:
    st.error(f"Erreur : {e}")
