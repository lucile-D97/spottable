import streamlit as st
import pandas as pd
import pydeck as pdk

# 1. Configuration
st.set_page_config(page_title="Mes spots", layout="wide")

# Logique Reset
if "reset" in st.query_params:
    st.query_params.clear()
    st.session_state.search_input = ""
    for key in list(st.session_state.keys()):
        if key.startswith("toggle_"):
            st.session_state[key] = False
    st.rerun()

# 2. Style CSS (Alignement forcé)
st.markdown("""
    <style>
    .stApp { background-color: #efede1 !important; }
    header[data-testid="stHeader"], div[data-testid="stDecoration"] { display: none !important; }
    
    /* GRILLE DE CARTES ALIGNÉES */
    .spot-grid {
        display: flex;
        flex-wrap: wrap;
        gap: 15px;
        margin-top: 20px;
    }

    .card-item {
        flex: 1 1 calc(25% - 15px); /* 4 cartes par ligne */
        min-width: 250px;
        background-color: #efede1;
        border: 1px solid #b6beb1;
        border-radius: 8px;
        padding: 15px;
        display: flex;
        flex-direction: row; /* Texte à gauche, bouton à droite */
        justify-content: space-between;
        align-items: center;
        /* C'est ici que l'alignement magique opère */
        align-self: stretch; 
    }

    .card-content { flex: 1; padding-right: 10px; }
    .card-title { color: #d92644; font-weight: bold; font-size: 0.95rem; line-height: 1.1; margin-bottom: 2px; }
    .card-addr { font-size: 0.72rem; color: #202b24; opacity: 0.8; margin-bottom: 6px; }
    
    .tag-container { margin-top: 4px; }
    .tag-pill {
        display: inline-block; background-color: #b6beb1; color: #202b24;
        padding: 1px 6px; border-radius: 10px; font-size: 0.58rem; font-weight: bold; margin-right: 3px;
    }

    .go-btn {
        background-color: #7397a3; color: #efede1 !important;
        padding: 4px 12px; border-radius: 4px; text-decoration: none !important;
        font-weight: bold; font-size: 0.65rem; height: 18px; line-height: 18px;
        display: inline-flex; align-items: center; transition: 0.2s;
    }
    .go-btn:hover { background-color: #b6beb1; color: #202b24 !important; }

    /* RECHERCHE & RESET */
    div[data-testid="stTextInput"] div[data-baseweb="input"] { background-color: #b6beb1 !important; border: none !important; }
    div[data-testid="stTextInput"] input {
        padding-left: 40px !important;
        background-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="%23B6BEB1" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>');
        background-repeat: no-repeat; background-position: 12px center;
    }
    .reset-link {
        font-weight: bold; color: #202b24 !important; text-decoration: none !important;
        font-size: 0.85rem; display: block; text-align: right; margin-top: 10px; cursor: pointer;
    }
    .reset-link:hover { color: #7397a3 !important; }
    </style>
    """, unsafe_allow_html=True)

try:
    df = pd.read_csv("Spottable v3.csv", sep=None, engine='python')
    df.columns = df.columns.str.strip().str.lower()
    
    # Coordonnées
    lat_c = next(c for c in df.columns if 'lat' in c)
    lon_c = next(c for c in df.columns if 'lon' in c)
    df['lat'] = pd.to_numeric(df[lat_c].astype(str).str.replace(',', '.'), errors='coerce')
    df['lon'] = pd.to_numeric(df[lon_c].astype(str).str.replace(',', '.'), errors='coerce')
    df = df.dropna(subset=['lat', 'lon']).reset_index(drop=True)

    c_name = next(c for c in df.columns if c in ['name', 'nom'])
    c_addr = next(c for c in df.columns if c in ['address', 'adresse'])
    c_link = next((c for c in df.columns if 'map' in c or 'lien' in c), None)
    c_tags = next((c for c in df.columns if 'tag' in c), None)

    st.title("Mes spots")

    col_map, col_filters = st.columns([1.6, 1.4])

    with col_filters:
        st.write("### Filtrer")
        c_search, c_reset = st.columns([1, 0.6])
        with c_search:
            search_query = st.text_input("Rechercher", key="search_input", label_visibility="collapsed")
        with c_reset:
            st.markdown('<a href="/?reset=1" target="_self" class="reset-link">Tout réinitialiser</a>', unsafe_allow_html=True)

        df_filtered = df[df[c_name].str.contains(search_query, case=False, na=False)].copy()

        if c_tags:
            all_tags = sorted(list(set([t.strip() for val in df[c_tags].dropna() for t in str(val).split(',')])))
            t_cols = st.columns(4)
            sel_tags = []
            for i, tag in enumerate(all_tags):
                with t_cols[i % 4]:
                    if st.toggle(tag, key=f"toggle_{tag}"): sel_tags.append(tag)
            if sel_tags:
                df_filtered = df_filtered[df_filtered[c_tags].apply(lambda x: any(t.strip() in sel_tags for t in str(x).split(',')))]

    with col_map:
        st.pydeck_chart(pdk.Deck(
            map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
            initial_view_state=pdk.ViewState(latitude=48.8566, longitude=2.3522, zoom=12),
            layers=[pdk.Layer("IconLayer", data=df_filtered, get_icon='{"url": "https://img.icons8.com/ios-filled/100/d92644/marker.png", "width": 100, "height": 100, "anchorY": 100}', get_position=["lon", "lat"], get_size=4, size_scale=10, pickable=True)]
        ))

    st.markdown("---")
    st.write(f"### {len(df_filtered)} spots trouvés")

    # GÉNÉRATION DE LA GRILLE HTML (Garantit l'alignement des bas de cartes)
    cards_html = "<div class='spot-grid'>"
    for _, row in df_filtered.head(100).iterrows():
        tags_html = "".join([f"<span class='tag-pill'>{t.strip()}</span>" for t in str(row[c_tags]).split(',')]) if c_tags and pd.notna(row[c_tags]) else ""
        link_url = row[c_link] if c_link and pd.notna(row[c_link]) else "#"
        
        cards_html += f"""
        <div class="card-item">
            <div class="card-content">
                <div class="card-title">{row[c_name]}</div>
                <div class="card-addr">📍 {row[c_addr]}</div>
                <div class="tag-container">{tags_html}</div>
            </div>
            <div class="card-btn">
                <a href="{link_url}" target="_blank" class="go-btn">Go</a>
            </div>
        </div>
        """
    cards_html += "</div>"
    st.markdown(cards_html, unsafe_allow_html=True)

except Exception as e:
    st.error(f"Erreur : {e}")
