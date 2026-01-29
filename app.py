import streamlit as st
import pandas as pd
import pydeck as pdk
import re

# 1. Configuration
st.set_page_config(page_title="Mes spots", layout="wide")

def reset_filters():
    st.session_state.search_input = ""
    for key in list(st.session_state.keys()):
        if key.startswith("toggle_"):
            st.session_state[key] = False

# 2. Style CSS
st.markdown("""
    <style>
    .stApp { background-color: #efede1 !important; }
    header[data-testid="stHeader"], div[data-testid="stDecoration"] { display: none !important; }
    .main .block-container { padding-top: 2rem !important; }

    h1 { color: #d92644 !important; margin-top: -30px !important; }
    html, body, [class*="st-"], p, div, span, label, h3 { color: #202b24 !important; }

    /* TAGS FILTRES */
    div[data-testid="stCheckbox"] { margin-bottom: -18px !important; }

    /* RECHERCHE AVEC LOUPE À GAUCHE */
    div[data-testid="stTextInput"] div[data-baseweb="input"] { 
        background-color: #b6beb1 !important; border: none !important; border-radius: 4px !important;
    }
    div[data-testid="stTextInput"] input {
        padding-left: 40px !important;
        background-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="%23B6BEB1" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>');
        background-repeat: no-repeat;
        background-position: 12px center;
    }
    .stTextInput p { display: none !important; } 

    /* RESET TEXTE GRAS */
    div[data-testid="column"] button[kind="secondary"] {
        background: none !important; border: none !important; padding: 0 !important;
        color: #202b24 !important; font-weight: bold !important; box-shadow: none !important;
        display: block !important; margin-left: auto !important;
    }
    div[data-testid="column"] button[kind="secondary"]:hover { color: #d92644 !important; }

    /* CARTES DE LA GRILLE */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #efede1 !important;
        border: 1px solid #b6beb1 !important;
        padding: 12px !important;
        border-radius: 8px !important;
    }
    .spot-title { color: #d92644; font-weight: bold; font-size: 0.9rem; line-height: 1.1; margin: 0; }
    .tag-container { margin: 6px 0 !important; line-height: 1; }
    .tag-label { 
        display: inline-block; background-color: #b6beb1; color: #202b24; padding: 1px 6px; 
        border-radius: 10px; margin-right: 3px; margin-bottom: 3px; font-size: 0.55rem; font-weight: bold; 
    }
    .spot-addr { font-size: 0.7rem; color: #202b24; margin-top: 4px; opacity: 0.8; }
    
    /* BOUTON GO */
    .stLinkButton a { 
        background-color: #7397a3 !important; color: #efede1 !important; border-radius: 4px !important; 
        font-weight: bold !important; padding: 0px 12px !important; font-size: 0.7rem !important;
        height: 18px !important; display: inline-flex !important; align-items: center !important;
        border: none !important; text-decoration: none !important;
    }
    .stLinkButton a:hover { background-color: #b6beb1 !important; color: #202b24 !important; }
    </style>
    """, unsafe_allow_html=True)

try:
    df = pd.read_csv("Spottable v3.csv", sep=None, engine='python')
    df.columns = df.columns.str.strip().str.lower()
    
    lat_c = next((c for c in df.columns if 'lat' in c), 'lat')
    lon_c = next((c for c in df.columns if 'lon' in c), 'lon')
    df[lat_c] = pd.to_numeric(df[lat_c].astype(str).str.replace(',', '.'), errors='coerce')
    df[lon_c] = pd.to_numeric(df[lon_c].astype(str).str.replace(',', '.'), errors='coerce')
    df = df.dropna(subset=[lat_c, lon_c]).reset_index(drop=True)

    c_name = next((c for c in df.columns if c in ['name', 'nom']), df.columns[0])
    c_addr = next((c for c in df.columns if c in ['address', 'adresse']), df.columns[1])
    c_link = next((c for c in df.columns if any(w in c for w in ['map', 'lien'])), None)
    col_tags = next((c for c in df.columns if 'tag' in c), None)

    st.title("Mes spots")

    col_map, col_filters = st.columns([1.6, 1.4])

    with col_filters:
        st.write("### Filtrer")
        search_query = st.text_input("Rechercher", placeholder="Nom du spot...", key="search_input", label_visibility="collapsed")
        st.button("TOUT RÉINITIALISER", on_click=reset_filters)

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
                get_position=[lon_c, lat_c], pickable=True, auto_highlight=True,
                highlight_color=[182, 190, 177, 200]
            )],
            tooltip={"html": f"<b>{{{c_name}}}</b>", "style": {"backgroundColor": "#efede1", "color": "#202b24"}}
        ))

    # --- GRILLE DE SPOTS 4 COLONNES (Méthode 100% stable) ---
    st.markdown("---")
    st.write(f"### {len(df_filtered)} spots trouvés")
    
    # On crée les colonnes une seule fois
    cols = st.columns(4)
    
    # On distribue les spots dans les 4 colonnes
    for index, row in df_filtered.head(100).iterrows():
        # L'opérateur % 4 permet de boucler sur les colonnes 0, 1, 2, 3
        with cols[index % 4]:
            with st.container(border=True):
                # Header : Titre + Go
                h1, h2 = st.columns([3, 1])
                h1.markdown(f"<div class='spot-title'>{row[c_name]}</div>", unsafe_allow_html=True)
                if c_link and pd.notna(row[c_link]):
                    h2.link_button("Go", row[c_link])
                
                # Tags remontés
                if col_tags and pd.notna(row[col_tags]):
                    t_html = "".join([f'<span class="tag-label">{t.strip()}</span>' for t in str(row[col_tags]).split(',')])
                    st.markdown(f"<div class='tag-container'>{t_html}</div>", unsafe_allow_html=True)
                
                # Adresse
                st.markdown(f"<div class='spot-addr'>📍 {row[c_addr]}</div>", unsafe_allow_html=True)

except Exception as e:
    st.error(f"Erreur : {e}")
