import streamlit as st
import pandas as pd
import pydeck as pdk
import re

# 1. Configuration de la page
st.set_page_config(page_title="Mes spots", layout="wide")

# Fonction de réinitialisation
def reset_filters():
    st.session_state.search_input = ""
    for key in st.session_state.keys():
        if key.startswith("toggle_"):
            st.session_state[key] = False

# 2. Style CSS complet
st.markdown("""
    <style>
    .stApp { background-color: #efede1 !important; }
    header[data-testid="stHeader"], div[data-testid="stDecoration"] { display: none !important; }
    .main .block-container { padding-top: 2rem !important; }

    h1 { color: #d92644 !important; margin-top: -30px !important; }
    html, body, [class*="st-"], p, div, span, label, h3 { color: #202b24 !important; }

    /* FILTRES TAGS RESSERRÉS */
    div[data-testid="stCheckbox"] { margin-bottom: -18px !important; }

    /* BARRE DE RECHERCHE DANS COLONNE DROITE */
    div[data-testid="stTextInput"] div[data-baseweb="input"] { 
        background-color: #b6beb1 !important; 
        border: none !important; 
        border-radius: 4px !important;
    }
    .stTextInput p { display: none !important; } /* Supprime 'Press Enter' */

    /* RESET TEXTE */
    .reset-container { text-align: right; margin-top: -10px; margin-bottom: 10px; }
    .reset-text {
        font-weight: bold;
        color: #202b24;
        cursor: pointer;
        font-size: 0.8rem;
        text-decoration: none;
    }

    /* DESIGN DES CARTES (CARDS) */
    [data-testid="stMetricBorder"] {
        padding: 12px !important; /* Marges égales partout */
        background-color: #efede1 !important;
        border: 1px solid #b6beb1 !important;
    }

    .spot-title { 
        color: #d92644; 
        font-weight: bold; 
        font-size: 0.95rem; 
        line-height: 1.1;
        margin: 0 !important;
    }

    .tag-container { margin: 8px 0 !important; line-height: 1; }
    .tag-label { 
        display: inline-block; 
        background-color: #b6beb1; 
        color: #202b24; 
        padding: 2px 8px; 
        border-radius: 10px; 
        margin-right: 4px; 
        margin-bottom: 4px;
        font-size: 0.6rem; 
        font-weight: bold; 
    }

    .spot-addr { 
        font-size: 0.75rem; 
        color: #202b24; 
        margin: 8px 0 0 0 !important; 
        opacity: 0.8; 
        line-height: 1.2; 
    }
    
    /* BOUTON GO RECTANGLE HORIZONTAL */
    .stLinkButton a { 
        background-color: #7397a3 !important; 
        color: #efede1 !important; 
        border-radius: 4px !important; 
        font-weight: bold !important; 
        padding: 2px 15px !important; /* Rectangle horizontal */
        font-size: 0.7rem !important;
        height: 18px !important; /* Hauteur diminuée */
        display: inline-flex !important;
        align-items: center !important;
        border: none !important;
        text-decoration: none !important;
    }
    .stLinkButton a:hover {
        background-color: #b6beb1 !important;
        color: #202b24 !important;
    }
    </style>
    """, unsafe_allow_html=True)

try:
    # 3. Données
    df = pd.read_csv("Spottable v3.csv", sep=None, engine='python')
    df.columns = df.columns.str.strip().str.lower()
    
    # Nettoyage coordonnées
    for col in ['lat', 'latitude', 'lon', 'longitude']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce')
    
    lat_col = next((c for c in df.columns if 'lat' in c), 'lat')
    lon_col = next((c for c in df.columns if 'lon' in c), 'lon')
    c_name = next((c for c in df.columns if c in ['name', 'nom']), df.columns[0])
    c_addr = next((c for c in df.columns if c in ['address', 'adresse']), df.columns[1])
    c_link = next((c for c in df.columns if any(w in c for w in ['map', 'lien'])), None)
    col_tags = next((c for c in df.columns if 'tag' in c), None)

    df = df.dropna(subset=[lat_col, lon_col]).reset_index(drop=True)

    st.title("Mes spots")

    # --- LAYOUT PRINCIPAL ---
    col_map, col_filters = st.columns([1.6, 1.4])

    with col_filters:
        # Barre de recherche avec icône monochrome B6BEB1
        st.write("### Filtrer")
        
        # Loupe monochrome en SVG
        st.markdown("""
            <div style="display:flex; align-items:center; margin-bottom:10px;">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#B6BEB1" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
                <span style="margin-left:10px; font-weight:bold; color:#202b24; font-size:0.9rem;">RECHERCHER</span>
            </div>
        """, unsafe_allow_html=True)
        
        search_query = st.text_input("Rechercher", placeholder="Nom du spot...", key="search_input", label_visibility="collapsed")
        
        # Bouton Reset texte
        st.markdown('<div class="reset-container">', unsafe_allow_html=True)
        if st.button("TOUT RÉINITIALISER", on_click=reset_filters, key="btn_reset", help="Effacer tous les filtres"):
            pass
        st.markdown('</div>', unsafe_allow_html=True)

        df_filtered = df[df[c_name].str.contains(search_query, case=False, na=False)].copy()

        # Tags en 4 colonnes resserrées
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
        # FONCTIONNALITÉ : Apparition des pins au zoom (Clustering visuel)
        # On définit une couche qui ne s'affiche que si le nombre de points est gérable
        view = pdk.ViewState(latitude=48.8566, longitude=2.3522, zoom=12)
        
        layer = pdk.Layer(
            "IconLayer",
            data=df_filtered,
            get_icon="{'url': 'https://img.icons8.com/ios-filled/100/d92644/marker.png', 'width': 100, 'height': 100, 'anchorY': 100}",
            get_size=4,
            size_scale=10,
            get_position=[lon_col, lat_col],
            pickable=True,
            auto_highlight=True,
            highlight_color=[182, 190, 177, 200], # B6BEB1 au survol
        )

        # Si trop de points, on utilise un ClusterLayer pour éviter l'effet brouillon
        cluster_layer = pdk.Layer(
            "ClusterLayer",
            data=df_filtered,
            get_position=[lon_col, lat_col],
            cluster_radius=50,
            get_fill_color=[217, 38, 68, 200],
            pickable=True,
        )

        st.pydeck_chart(pdk.Deck(
            map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
            initial_view_state=view,
            # On affiche les clusters quand c'est dézoomé (> 50 points), les pins quand on zoom
            layers=[cluster_layer if len(df_filtered) > 150 else layer],
            tooltip={"html": f"<b>{{{c_name}}}</b>", "style": {"backgroundColor": "#efede1", "color": "#202b24"}}
        ))

    # --- GRILLE DE CARTES EN BAS ---
    st.markdown("---")
    n_cols = 4
    for i in range(0, len(df_filtered.head(100)), n_cols):
        grid_cols = st.columns(n_cols)
        for j, (idx, row) in enumerate(df_filtered.iloc[i:i+n_cols].iterrows()):
            with grid_cols[j]:
                with st.container(border=True):
                    # Titre et Bouton Go alignés
                    h_col, b_col = st.columns([3, 1])
                    with h_col:
                        st.markdown(f"<p class='spot-title'>{row[c_name]}</p>", unsafe_allow_html=True)
                    with b_col:
                        if c_link and pd.notna(row[c_link]):
                            st.link_button("Go", row[c_link])
                    
                    # Tags remontés (entre nom et adresse)
                    if col_tags and pd.notna(row[col_tags]):
                        t_html = "".join([f'<span class="tag-label">{t.strip()}</span>' for t in str(row[col_tags]).split(',')])
                        st.markdown(f"<div class='tag-container'>{t_html}</div>", unsafe_allow_html=True)
                    
                    # Adresse
                    st.markdown(f"<p class='spot-addr'>📍 {row[c_addr]}</p>", unsafe_allow_html=True)

except Exception as e:
    st.error(f"Erreur : {e}")
