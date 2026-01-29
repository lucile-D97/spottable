import streamlit as st
import pandas as pd
import pydeck as pdk
import re

# 1. Configuration de la page
st.set_page_config(page_title="Mes spots", layout="wide")

# 2. Style CSS (Nouveau : suppression des espaces entre expanders)
st.markdown("""
    <style>
    .stApp { background-color: #efede1 !important; }
    header[data-testid="stHeader"] { display: none !important; }
    div[data-testid="stDecoration"] { display: none !important; }
    .main .block-container { padding-top: 2rem !important; }

    h1 { color: #d92644 !important; margin-top: -30px !important; }
    html, body, [class*="st-"], p, div, span, label, h3 { color: #202b24 !important; }

    /* RESSERRER LES EXPANDERS */
    div[data-testid="stExpander"] {
        background-color: #efede1 !important;
        border: 0.5px solid #b6beb1 !important;
        border-radius: 0px !important; /* Carré pour l'effet liste */
        margin-bottom: -1px !important; /* Supprime l'espace entre les bordures */
    }
    
    .stLinkButton a { 
        background-color: #7397a3 !important; 
        color: #efede1 !important; 
        border-radius: 8px !important; 
        font-weight: bold !important; 
        display: flex !important;
        justify-content: center !important;
        text-decoration: none !important;
    }
    
    .tag-label { display: inline-block; background-color: #b6beb1; color: #202b24; padding: 2px 10px; border-radius: 15px; margin-right: 5px; font-size: 0.75rem; font-weight: bold; }
    
    div[data-testid="stTextInput"] div[data-baseweb="input"] { background-color: #b6beb1 !important; border: none !important; }
    div[role="switch"] { background-color: #b6beb1 !important; }
    div[aria-checked="true"][role="switch"] { background-color: #d92644 !important; }
    </style>
    """, unsafe_allow_html=True)

def get_precise_coords(url):
    if pd.isna(url): return None, None
    match = re.search(r'@(-?\d+\.\d+),(-?\d+\.\d+)', str(url))
    if match: return float(match.group(1)), float(match.group(2))
    return None, None

st.title("Mes spots")

try:
    # 3. Données
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
    c_name = next((cn for cn in df.columns if cn in ['name', 'nom']), df.columns[0])
    c_addr = next((ca for ca in df.columns if ca in ['address', 'adresse']), df.columns[1])

    # --- NOUVELLE DISPOSITION : COLONNE 1 (CARTE) vs COLONNE 2 (FILTRES) ---
    col_map, col_filters = st.columns([2, 1])

    with col_filters:
        st.write("### Rechercher & Filtrer")
        search_query = st.text_input("Rechercher", placeholder="Nom du spot...", label_visibility="collapsed")
        
        df_filtered = df[df[c_name].str.contains(search_query, case=False, na=False)].copy()

        if col_tags:
            all_tags = sorted(list(set([t.strip() for val in df[col_tags].dropna() for t in str(val).split(',')])))
            selected_tags = []
            # On met les toggles sur 2 colonnes à l'intérieur de la zone filtre
            t_subcols = st.columns(2)
            for i, tag in enumerate(all_tags):
                with t_subcols[i % 2]:
                    if st.toggle(tag, key=f"toggle_{tag}"):
                        selected_tags.append(tag)
            
            if selected_tags:
                df_filtered = df_filtered[df_filtered[col_tags].apply(lambda x: any(t.strip() in selected_tags for t in str(x).split(',')) if pd.notna(x) else False)]

    with col_map:
        icon_data = {
            "url": "https://img.icons8.com/ios-filled/100/d92644/marker.png",
            "width": 100, "height": 100, "anchorY": 100
        }
        df_filtered['icon_data'] = [icon_data] * len(df_filtered)

        layer = pdk.Layer(
            "IconLayer",
            data=df_filtered,
            get_icon="icon_data",
            get_size=4,
            size_scale=10,
            get_position=["lon", "lat"],
            pickable=True,
            auto_highlight=True,
            highlight_color=[32, 43, 36, 180], # Couleur #202b24 au survol
        )

        st.pydeck_chart(pdk.Deck(
            map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
            initial_view_state=pdk.ViewState(latitude=48.8566, longitude=2.3522, zoom=12),
            layers=[layer],
            tooltip={
                "html": f"<b>{{{c_name}}}</b>",
                "style": {"backgroundColor": "#efede1", "color": "#202b24"}
            }
        ))

    # --- SECTION DU BAS : LISTE DES ADRESSES (SUR TOUTE LA LARGEUR) ---
    st.markdown("---")
    st.write(f"### Liste des spots ({len(df_filtered)})")
    
    for _, row in df_filtered.head(100).iterrows(): # Limité à 100 pour la performance fluide
        with st.expander(f"**{row[c_name]}** — {row[c_addr]}"):
            col_info, col_btn = st.columns([3, 1])
            with col_info:
                if col_tags and pd.notna(row[col_tags]):
                    tags_html = "".join([f'<span class="tag-label">{t.strip()}</span>' for t in str(row[col_tags]).split(',')])
                    st.markdown(tags_html, unsafe_allow_html=True)
            with col_btn:
                if c_link and pd.notna(row[c_link]):
                    st.link_button("**Y aller**", row[c_link], use_container_width=True)

except Exception as e:
    st.error(f"Erreur : {e}")
    
