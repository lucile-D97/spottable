import streamlit as st
import pandas as pd
import pydeck as pdk
import re

# 1. Configuration de la page
st.set_page_config(page_title="Mes spots", layout="wide")

# 2. Style CSS (Nouveau : Design des cartes et grille)
st.markdown("""
    <style>
    .stApp { background-color: #efede1 !important; }
    header[data-testid="stHeader"] { display: none !important; }
    div[data-testid="stDecoration"] { display: none !important; }
    .main .block-container { padding-top: 2rem !important; }

    h1 { color: #d92644 !important; margin-top: -30px !important; }
    html, body, [class*="st-"], p, div, span, label, h3 { color: #202b24 !important; }

    /* DESIGN DES CARTES (Grid) */
    .spot-card {
        background-color: #efede1;
        border: 1px solid #b6beb1;
        border-radius: 8px;
        padding: 15px;
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        transition: transform 0.2s;
    }
    .spot-card:hover {
        border-color: #d92644;
        box-shadow: 0px 4px 10px rgba(0,0,0,0.05);
    }
    
    .spot-title { color: #d92644; font-weight: bold; font-size: 1.1rem; margin-bottom: 5px; }
    .spot-addr { font-size: 0.85rem; color: #202b24; margin-bottom: 10px; opacity: 0.8; }
    
    .tag-label { 
        display: inline-block; 
        background-color: #b6beb1; 
        color: #202b24; 
        padding: 1px 8px; 
        border-radius: 12px; 
        margin-right: 4px; 
        margin-bottom: 4px;
        font-size: 0.7rem; 
        font-weight: bold; 
    }
    
    /* Input & Toggles */
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
    
    lat_col = next((cn for cn in df.columns if cn in ['latitude', 'lat']), None)
    lon_col = next((cn for cn in df.columns if cn in ['longitude', 'lon']), None)
    c_link = next((cn for cn in df.columns if any(w in cn for w in ['map', 'lien', 'geo'])), None)
    col_tags = next((cn for cn in df.columns if cn == 'tags'), None)

    if lat_col and lon_col:
        df['lat'] = pd.to_numeric(df[lat_col].astype(str).str.replace(',', '.'), errors='coerce')
        df['lon'] = pd.to_numeric(df[lon_col].astype(str).str.replace(',', '.'), errors='coerce')

    df = df.dropna(subset=['lat', 'lon']).reset_index(drop=True)
    c_name = next((cn for cn in df.columns if cn in ['name', 'nom']), df.columns[0])
    c_addr = next((ca for ca in df.columns if ca in ['address', 'adresse']), df.columns[1])

    # --- DISPOSITION : CARTE (1.8) vs FILTRES (1.2) ---
    col_map, col_filters = st.columns([1.8, 1.2])

    with col_filters:
        st.write("### Filtrer")
        search_query = st.text_input("Rechercher", placeholder="Nom du spot...", label_visibility="collapsed")
        
        df_filtered = df[df[c_name].str.contains(search_query, case=False, na=False)].copy()

        if col_tags:
            all_tags = sorted(list(set([t.strip() for val in df[col_tags].dropna() for t in str(val).split(',')])))
            selected_tags = []
            # Affichage en 3 colonnes pour les tags
            t_subcols = st.columns(3)
            for i, tag in enumerate(all_tags):
                with t_subcols[i % 3]:
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
            highlight_color=[32, 43, 36, 180],
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

    # --- SECTION DU BAS : GRILLE DE CARTES ---
    st.markdown("---")
    st.write(f"### {len(df_filtered)} spots trouvés")
    
    # Création de la grille (4 colonnes sur PC)
    n_cols = 4
    rows = [df_filtered.iloc[i:i+n_cols] for i in range(0, len(df_filtered.head(100)), n_cols)]

    for row_df in rows:
        cols = st.columns(n_cols)
        for i, (idx, row) in enumerate(row_df.iterrows()):
            with cols[i]:
                # Construction de la carte en HTML/Markdown pour le style
                tags_html = ""
                if col_tags and pd.notna(row[col_tags]):
                    tags_html = "".join([f'<span class="tag-label">{t.strip()}</span>' for t in str(row[col_tags]).split(',')])
                
                # Encapsulation dans un container Streamlit pour garder les boutons fonctionnels
                with st.container(border=True):
                    st.markdown(f"<div class='spot-title'>{row[c_name]}</div>", unsafe_allow_html=True)
                    st.markdown(f"<div class='spot-addr'>📍 {row[c_addr]}</div>", unsafe_allow_html=True)
                    st.markdown(f"<div>{tags_html}</div>", unsafe_allow_html=True)
                    if c_link and pd.notna(row[c_link]):
                        st.link_button("Y aller", row[c_link], use_container_width=True)

except Exception as e:
    st.error(f"Erreur : {e}")
