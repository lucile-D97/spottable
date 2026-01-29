import streamlit as st
import pandas as pd
import pydeck as pdk
import re

# 1. Configuration de la page
st.set_page_config(page_title="Mes spots", layout="wide")

# 2. Style CSS (Bouton Go, Grille et Alignements)
st.markdown("""
    <style>
    .stApp { background-color: #efede1 !important; }
    header[data-testid="stHeader"] { display: none !important; }
    div[data-testid="stDecoration"] { display: none !important; }
    .main .block-container { padding-top: 2rem !important; }

    h1 { color: #d92644 !important; margin-top: -30px !important; }
    html, body, [class*="st-"], p, div, span, label, h3 { color: #202b24 !important; }

    /* DESIGN DES CARTES */
    [data-testid="stVerticalBlockBorderWrapper"] > div > [data-testid="stVerticalBlock"] {
        gap: 0.5rem !important;
    }
    
    .spot-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        gap: 10px;
        margin-bottom: 5px;
    }

    .spot-title { 
        color: #d92644; 
        font-weight: bold; 
        font-size: 1rem; 
        line-height: 1.2;
    }

    .spot-addr { font-size: 0.8rem; color: #202b24; margin-bottom: 8px; opacity: 0.8; }
    
    .tag-label { 
        display: inline-block; 
        background-color: #b6beb1; 
        color: #202b24; 
        padding: 1px 8px; 
        border-radius: 12px; 
        margin-right: 4px; 
        margin-bottom: 4px;
        font-size: 0.65rem; 
        font-weight: bold; 
    }
    
    /* STYLE BOUTON GO */
    .stLinkButton a { 
        background-color: #7397a3 !important; 
        color: #efede1 !important; 
        border-radius: 6px !important; 
        font-weight: bold !important; 
        padding: 2px 12px !important;
        font-size: 0.8rem !important;
        text-decoration: none !important;
        min-width: 45px !important;
        display: flex !important;
        justify-content: center !important;
        border: none !important;
    }
    .stLinkButton a:hover {
        background-color: #202b24 !important;
        color: #efede1 !important;
    }
    
    /* FORMULAIRES */
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

    # --- LAYOUT : CARTE (1.6) vs FILTRES (1.4) ---
    col_map, col_filters = st.columns([1.6, 1.4])

    with col_filters:
        st.write("### Filtrer")
        search_query = st.text_input("Rechercher", placeholder="Nom du spot...", label_visibility="collapsed")
        df_filtered = df[df[c_name].str.contains(search_query, case=False, na=False)].copy()

        if col_tags:
            all_tags = sorted(list(set([t.strip() for val in df[col_tags].dropna() for t in str(val).split(',')])))
            selected_tags = []
            # Tags en 4 colonnes pour compacité maximale
            t_subcols = st.columns(4)
            for i, tag in enumerate(all_tags):
                with t_subcols[i % 4]:
                    if st.toggle(tag, key=f"toggle_{tag}"):
                        selected_tags.append(tag)
            
            if selected_tags:
                df_filtered = df_filtered[df_filtered[col_tags].apply(lambda x: any(t.strip() in selected_tags for t in str(x).split(',')) if pd.notna(x) else False)]

    with col_map:
        icon_data = {"url": "https://img.icons8.com/ios-filled/100/d92644/marker.png", "width": 100, "height": 100, "anchorY": 100}
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
            tooltip={"html": f"<b>{{{c_name}}}</b>", "style": {"backgroundColor": "#efede1", "color": "#202b24"}}
        ))

    # --- SECTION DU BAS : GRILLE DE CARTES ---
    st.markdown("---")
    st.write(f"### {len(df_filtered)} spots trouvés")
    
    n_cols = 4
    rows = [df_filtered.iloc[i:i+n_cols] for i in range(0, len(df_filtered.head(100)), n_cols)]

    for row_df in rows:
        grid_cols = st.columns(n_cols)
        for i, (idx, row) in enumerate(row_df.iterrows()):
            with grid_cols[i]:
                with st.container(border=True):
                    # Header avec Titre et Bouton Go à droite
                    header_col, btn_col = st.columns([3, 1])
                    with header_col:
                        st.markdown(f"<div class='spot-title'>{row[c_name]}</div>", unsafe_allow_html=True)
                    with btn_col:
                        if c_link and pd.notna(row[c_link]):
                            st.link_button("Go", row[c_link])
                    
                    st.markdown(f"<div class='spot-addr'>📍 {row[c_addr]}</div>", unsafe_allow_html=True)
                    
                    if col_tags and pd.notna(row[col_tags]):
                        tags_html = "".join([f'<span class="tag-label">{t.strip()}</span>' for t in str(row[col_tags]).split(',')])
                        st.markdown(f"<div>{tags_html}</div>", unsafe_allow_html=True)

except Exception as e:
    st.error(f"Erreur : {e}")
