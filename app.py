import streamlit as st
import pandas as pd
import pydeck as pdk
import re

# 1. Configuration de la page
st.set_page_config(page_title="Mes spots", layout="wide")

# --- LOGIQUE DE RÉINITIALISATION ---
if "reset" in st.query_params:
    st.query_params.clear()
    st.session_state.search_input = ""
    for key in list(st.session_state.keys()):
        if key.startswith("toggle_"):
            st.session_state[key] = False
    st.rerun()

# 2. Style CSS
st.markdown("""
    <style>
    .stApp { background-color: #efede1 !important; }
    header[data-testid="stHeader"], div[data-testid="stDecoration"] { display: none !important; }
    .main .block-container { padding-top: 2rem !important; }

    h1 { color: #d92644 !important; margin-bottom: 20px !important; }
    html, body, [class*="st-"], p, div, span, label, h3 { color: #202b24 !important; }

    /* BARRE DE RECHERCHE AVEC LOUPE */
    div[data-testid="stTextInput"] div[data-baseweb="input"] { 
        background-color: #b6beb1 !important; 
        border: none !important; 
        border-radius: 4px !important;
    }
    div[data-testid="stTextInput"] input {
        padding-left: 40px !important;
        background-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="%23B6BEB1" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>');
        background-repeat: no-repeat;
        background-position: 12px center;
    }
    .stTextInput p { display: none !important; } 

    /* TEXTE CLIQUABLE RESET */
    .reset-link {
        font-family: inherit;
        font-weight: bold !important;
        color: #202b24 !important;
        text-decoration: none !important;
        font-size: 0.85rem !important; 
        display: block;
        text-align: right;
        margin-top: 10px;
        transition: color 0.2s;
        cursor: pointer;
    }
    .reset-link:hover { color: #7397a3 !important; }

    /* DESIGN DES CARTES */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #efede1 !important;
        border: 1px solid #b6beb1 !important;
        border-radius: 8px !important;
        padding: 15px !important;
    }

    .spot-title { color: #d92644; font-weight: bold; font-size: 0.95rem; line-height: 1.1; margin-bottom: 4px; }
    .spot-addr { font-size: 0.72rem; color: #202b24; opacity: 0.8; line-height: 1.2; }
    
    .tag-label { 
        display: inline-block; background-color: #b6beb1; color: #202b24; padding: 1px 6px; 
        border-radius: 10px; margin-right: 3px; margin-bottom: 3px; font-size: 0.58rem; font-weight: bold; 
    }
    
    /* BOUTON GO */
    .stLinkButton a { 
        background-color: #7397a3 !important; 
        color: #efede1 !important; 
        border-radius: 4px !important; 
        font-weight: bold !important; 
        padding: 0px 10px !important; 
        font-size: 0.65rem !important;
        height: 18px !important;
        display: inline-flex !important;
        align-items: center !important;
        border: none !important;
        text-decoration: none !important;
        transition: background-color 0.2s !important;
    }
    .stLinkButton a:hover {
        background-color: #b6beb1 !important;
        color: #202b24 !important;
    }

    /* Centre verticalement le contenu de la colonne bouton */
    [data-testid="column"] {
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("Mes spots")

try:
    df = pd.read_csv("Spottable v3.csv", sep=None, engine='python')
    df.columns = df.columns.str.strip().str.lower()
    
    lat_col = next((cn for cn in df.columns if cn in ['latitude', 'lat']), None)
    lon_col = next((cn for cn in df.columns if cn in ['longitude', 'lon']), None)
    c_link = next((cn for cn in df.columns if any(w in cn for w in ['map', 'lien', 'geo'])), None)
    col_tags = next((cn for cn in df.columns if cn in ['tags', 'tag']), None)

    if lat_col and lon_col:
        df['lat'] = pd.to_numeric(df[lat_col].astype(str).str.replace(',', '.'), errors='coerce')
        df['lon'] = pd.to_numeric(df[lon_col].astype(str).str.replace(',', '.'), errors='coerce')

    df = df.dropna(subset=['lat', 'lon']).reset_index(drop=True)
    c_name = next((cn for cn in df.columns if cn in ['name', 'nom']), df.columns[0])
    c_addr = next((ca for ca in df.columns if ca in ['address', 'adresse']), df.columns[1])

    # --- LAYOUT DU HAUT ---
    col_map, col_filters = st.columns([1.6, 1.4])

    with col_filters:
        st.write("### Filtrer")
        c_search_ui, c_reset_ui = st.columns([1, 0.6])
        with c_search_ui:
            search_query = st.text_input("Rechercher", placeholder="Nom du spot...", key="search_input", label_visibility="collapsed")
        with c_reset_ui:
            st.markdown('<a href="/?reset=1" target="_self" class="reset-link">Tout réinitialiser</a>', unsafe_allow_html=True)

        df_filtered = df[df[c_name].str.contains(search_query, case=False, na=False)].copy()

        if col_tags:
            all_tags = sorted(list(set([t.strip() for val in df[col_tags].dropna() for t in str(val).split(',')])))
            t_subcols = st.columns(4)
            selected_tags = []
            for i, tag in enumerate(all_tags):
                with t_subcols[i % 4]:
                    if st.toggle(tag, key=f"toggle_{tag}"):
                        selected_tags.append(tag)
            
            if selected_tags:
                df_filtered = df_filtered[df_filtered[col_tags].apply(lambda x: any(t.strip() in selected_tags for t in str(x).split(',')) if pd.notna(x) else False)]

    with col_map:
        icon_data = {"url": "https://img.icons8.com/ios-filled/100/d92644/marker.png", "width": 100, "height": 100, "anchorY": 100}
        df_filtered['icon_data'] = [icon_data] * len(df_filtered)

        st.pydeck_chart(pdk.Deck(
            map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
            initial_view_state=pdk.ViewState(latitude=48.8566, longitude=2.3522, zoom=12),
            layers=[pdk.Layer(
                "IconLayer", data=df_filtered, get_icon="icon_data", get_size=4, size_scale=10,
                get_position=["lon", "lat"], pickable=True, auto_highlight=True,
                highlight_color=[182, 190, 177, 200]
            )],
            tooltip={"html": f"<b>{{{c_name}}}</b>", "style": {"backgroundColor": "#efede1", "color": "#202b24"}}
        ))

    # --- GRILLE DE SPOTS ---
    st.markdown("---")
    st.write(f"### {len(df_filtered)} spots trouvés")
    
    n_cols = 4
    for i in range(0, len(df_filtered.head(100)), n_cols):
        grid_cols = st.columns(n_cols)
        for j, (idx, row) in enumerate(df_filtered.iloc[i:i+n_cols].iterrows()):
            with grid_cols[j]:
                with st.container(border=True):
                    # DEUX COLONNES DANS LA CARTE : Texte à gauche (4), Bouton à droite (1)
                    txt_col, btn_col = st.columns([4, 1])
                    
                    with txt_col:
                        # 1. Nom
                        st.markdown(f"<div class='spot-title'>{row[c_name]}</div>", unsafe_allow_html=True)
                        # 2. Adresse (resserrée sous le nom)
                        st.markdown(f"<div class='spot-addr'>📍 {row[c_addr]}</div>", unsafe_allow_html=True)
                        # 3. Tags (en bas du bloc texte)
                        if col_tags and pd.notna(row[col_tags]):
                            st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
                            t_html = "".join([f'<span class="tag-label">{t.strip()}</span>' for t in str(row[col_tags]).split(',')])
                            st.markdown(f"<div>{t_html}</div>", unsafe_allow_html=True)
                    
                    with btn_col:
                        # Bouton Go centré verticalement par le CSS
                        if c_link and pd.notna(row[c_link]):
                            st.link_button("Go", row[c_link])

except Exception as e:
    st.error(f"Erreur : {e}")
