import streamlit as st
import pandas as pd
import pydeck as pdk

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

# 2. Style CSS (Design et alignement horizontal)
st.markdown("""
    <style>
    .stApp { background-color: #efede1 !important; }
    header[data-testid="stHeader"], div[data-testid="stDecoration"] { display: none !important; }
    .main .block-container { padding-top: 2rem !important; }

    h1 { color: #d92644 !important; margin-bottom: 20px !important; }
    html, body, [class*="st-"], p, div, span, label, h3 { color: #202b24 !important; }

    /* FILTRES TAGS */
    div[data-testid="stCheckbox"] { margin-bottom: -15px !important; }
    
    /* STYLE ACCORDÉONS */
    .stExpander { border: none !important; background-color: transparent !important; }
    .stExpander summary p { font-weight: bold !important; color: #202b24 !important; font-size: 0.85rem !important; }

    /* BARRE DE RECHERCHE */
    div[data-testid="stTextInput"] div[data-baseweb="input"] { 
        background-color: #b6beb1 !important; border: none !important; border-radius: 4px !important;
    }
    div[data-testid="stTextInput"] input {
        padding-left: 40px !important;
        background-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="%23B6BEB1" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>');
        background-repeat: no-repeat; background-position: 12px center;
    }

    /* RESET LINK */
    .reset-link {
        font-family: inherit; font-weight: bold !important; color: #202b24 !important;
        text-decoration: none !important; font-size: 0.85rem !important; 
        display: block; text-align: right; margin-top: 10px; cursor: pointer;
    }
    .reset-link:hover { color: #7397a3 !important; }

    /* DESIGN DES CARTES - ÉGALISATION DU BAS */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #efede1 !important; border: 1px solid #b6beb1 !important;
        border-radius: 8px !important; padding: 15px !important;
        min-height: 160px !important; /* Force l'alignement horizontal sur la ligne */
        display: flex !important; flex-direction: column !important;
        justify-content: space-between !important;
    }

    .spot-title { color: #d92644; font-weight: bold; font-size: 0.95rem; line-height: 1.1; margin-bottom: 4px; }
    .spot-addr { font-size: 0.72rem; color: #202b24; opacity: 0.8; line-height: 1.2; }
    .tag-label { display: inline-block; background-color: #b6beb1; color: #202b24; padding: 1px 6px; border-radius: 10px; font-size: 0.58rem; font-weight: bold; margin-right: 3px; margin-bottom: 3px; }

    /* BOUTON GO */
    .stLinkButton a { background-color: #7397a3 !important; color: #efede1 !important; border-radius: 4px !important; font-weight: bold !important; padding: 0px 10px !important; font-size: 0.65rem !important; height: 18px !important; display: inline-flex !important; align-items: center !important; text-decoration: none !important; }
    
    /* Centrage vertical colonne bouton */
    [data-testid="column"] { display: flex; flex-direction: column; justify-content: center; }
    </style>
    """, unsafe_allow_html=True)

st.title("Mes spots")

try:
    df = pd.read_csv("Spottable v4.csv", sep=None, engine='python')
    df.columns = df.columns.str.strip().str.lower()
    
    # Préparation données géo
    lat_col = next(cn for cn in df.columns if cn in ['latitude', 'lat'])
    lon_col = next(cn for cn in df.columns if cn in ['longitude', 'lon'])
    df['lat'] = pd.to_numeric(df[lat_col].astype(str).str.replace(',', '.'), errors='coerce')
    df['lon'] = pd.to_numeric(df[lon_col].astype(str).str.replace(',', '.'), errors='coerce')
    df = df.dropna(subset=['lat', 'lon']).reset_index(drop=True)

    c_name = next(cn for cn in df.columns if cn in ['name', 'nom'])
    c_addr = next(ca for ca in df.columns if ca in ['address', 'adresse'])
    c_link = next((cn for cn in df.columns if any(w in cn for w in ['map', 'lien'])), None)
    col_tags = next((cn for cn in df.columns if cn in ['tags', 'tag']), None)

    # --- FILTRES ---
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
            all_tags_list = sorted(list(set([t.strip() for val in df[col_tags].dropna() for t in str(val).split(',')])))
            
            c_status, c_logic = st.columns([1, 1])
            with c_status:
                col_a, col_b = st.columns(2)
                t_a_tester = col_a.toggle("À tester", key="toggle_a_tester")
                t_teste = col_b.toggle("Testé", key="toggle_teste")
            
            logic = c_logic.radio("Logique", ["Exclusif (ET)", "Cumulatif (OU)"], horizontal=True, label_visibility="collapsed")

            st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)

            selected_tags = []
            with st.expander("Type de lieu"):
                t_cols_lieu = st.columns(4)
                tag_lieu_list = ["Restaurant", "Bar", "Café", "Pâtisserie", "Boulangerie", "Glacier", "Marché", "Traiteur"]
                present_lieu = [t for t in tag_lieu_list if t in all_tags_list]
                for i, tag in enumerate(present_lieu):
                    if t_cols_lieu[i % 4].toggle(tag, key=f"toggle_{tag}"): selected_tags.append(tag)

            with st.expander("Type de cuisine"):
                t_cols_cuisine = st.columns(4)
                other_tags = [t for t in all_tags_list if t != "A tester" and t not in tag_lieu_list]
                for i, tag in enumerate(other_tags):
                    if t_cols_cuisine[i % 4].toggle(tag, key=f"toggle_{tag}"): selected_tags.append(tag)
            
            # Application filtres
            if t_a_tester and not t_teste:
                df_filtered = df_filtered[df_filtered[col_tags].str.contains("A tester", na=False)]
            elif t_teste and not t_a_tester:
                df_filtered = df_filtered[~df_filtered[col_tags].str.contains("A tester", na=False)]

            if selected_tags:
                def check_tags(x):
                    row_list = [t.strip() for t in str(x).split(',')]
                    return all(t in row_list for t in selected_tags) if "Exclusif" in logic else any(t in row_list for t in selected_tags)
                df_filtered = df_filtered[df_filtered[col_tags].apply(check_tags)]

    with col_map:
        # --- FIX BUG CARTE (Format icône stable) ---
        icon_data = {
            "url": "https://img.icons8.com/ios-filled/100/d92644/marker.png",
            "width": 100,
            "height": 100,
            "anchorY": 100
        }
        # On ne rajoute pas icon_data dans le dataframe pour éviter l'erreur "bad argument type"
        
        # CENTRAGE : Paris par défaut, sinon moyenne des points filtrés
        if search_query == "" and not any(st.session_state.get(f"toggle_{t}", False) for t in all_tags_list) and not t_a_tester and not t_teste:
            c_lat, c_lon, v_zoom = 48.8566, 2.3522, 12
        else:
            if not df_filtered.empty:
                c_lat = df_filtered['lat'].mean()
                c_lon = df_filtered['lon'].mean()
                v_zoom = 12 if len(df_filtered) > 1 else 14
            else:
                c_lat, c_lon, v_zoom = 48.8566, 2.3522, 11

        st.pydeck_chart(pdk.Deck(
            map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
            initial_view_state=pdk.ViewState(latitude=c_lat, longitude=c_lon, zoom=v_zoom, pitch=0),
            layers=[pdk.Layer(
                "IconLayer",
                data=df_filtered,
                get_icon=f"'{icon_data}'", # Fix technique pour Pydeck
                get_size=4,
                size_scale=10,
                get_position=["lon", "lat"],
                pickable=True
            )],
            tooltip={"html": f"<b>{{{c_name}}}</b>"}
        ))

    # --- GRILLE ---
    st.markdown("---")
    st.write(f"### {len(df_filtered)} spots trouvés")
    
    n_cols = 4
    for i in range(0, len(df_filtered.head(120)), n_cols):
        grid_cols = st.columns(n_cols)
        for j, (idx, row) in enumerate(df_filtered.iloc[i:i+n_cols].iterrows()):
            with grid_cols[j]:
                with st.container(border=True):
                    txt, btn = st.columns([4, 1])
                    with txt:
                        st.markdown(f"<div class='spot-title'>{row[c_name]}</div>", unsafe_allow_html=True)
                        st.markdown(f"<div class='spot-addr'>📍 {row[c_addr]}</div>", unsafe_allow_html=True)
                        if col_tags and pd.notna(row[col_tags]):
                            t_html = "".join([f'<span class="tag-label">{t.strip()}</span>' for t in str(row[col_tags]).split(',')])
                            st.markdown(f"<div style='margin-top:6px;'>{t_html}</div>", unsafe_allow_html=True)
                    with btn:
                        if c_link and pd.notna(row[c_link]): st.link_button("Go", row[c_link])

except Exception as e:
    st.error(f"Erreur système : {e}")
