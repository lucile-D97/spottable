import streamlit as st
import pandas as pd
import pydeck as pdk
import re

st.set_page_config(page_title="Mes spots", layout="wide")

# CSS : Styles, Tags et Mini-bouton +
st.markdown(f"""
    <style>
    .stApp {{ background-color: #efede1 !important; }}
    header[data-testid="stHeader"] {{ display: none !important; }}
    .main .block-container {{ padding-top: 2rem !important; }}
    
    h1 {{ color: #d92644 !important; margin-top: -30px !important; }}
    html, body, [class*="st-"], p, div, span, label, h3 {{ color: #202b24 !important; }}
    
    div[data-testid="stExpander"] {{
        background-color: #efede1 !important;
        border: 0.5px solid #b6beb1 !important;
        border-radius: 8px !important;
        margin-bottom: 10px !important;
    }}
    
    .stLinkButton a {{ 
        background-color: #7397a3 !important; 
        color: #efede1 !important; 
        border-radius: 50% !important;
        width: 32px !important;
        height: 32px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        font-size: 18px !important;
        font-weight: bold !important; 
        text-decoration: none !important;
    }}
    .stLinkButton a:hover {{ background-color: #d92644 !important; }}

    .tag-label {{ 
        display: inline-block; 
        background-color: #b6beb1; 
        color: #202b24; 
        padding: 2px 10px; 
        border-radius: 15px; 
        margin-right: 5px; 
        font-size: 0.75rem; 
        font-weight: bold; 
    }}
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

    # --- FILTRES TAGS ---
    st.write("### Filtrer par catégorie")
    df_filtered = df.copy()
    if col_tags:
        all_tags = sorted(list(set([t.strip() for val in df[col_tags].dropna() for t in str(val).split(',')])))
        t_cols = st.columns(6)
        selected_tags = []
        for i, tag in enumerate(all_tags):
            with t_cols[i % 6]:
                if st.toggle(tag, key=f"toggle_{tag}"):
                    selected_tags.append(tag)
        if selected_tags:
            df_filtered = df_filtered[df_filtered[col_tags].apply(lambda x: any(t.strip() in selected_tags for t in str(x).split(',')) if pd.notna(x) else False)]

    # --- RECHERCHE ET SÉLECTION PRÉCISE ---
    col_search, col_select = st.columns([1, 1])
    with col_search:
        search_query = st.text_input("Rechercher un nom", placeholder="Ex: Café de Flore", label_visibility="collapsed")
        if search_query:
            df_filtered = df_filtered[df_filtered[c_name].str.contains(search_query, case=False, na=False)]

    with col_select:
        # LISTE DÉROULANTE POUR SÉLECTIONNER UN PIN PRÉCIS
        options = ["Tous les spots visibles"] + sorted(df_filtered[c_name].tolist())
        selected_spot_name = st.selectbox("Sélectionner un spot sur la carte", options, label_visibility="collapsed")

    # --- AFFICHAGE ---
    col1, col2 = st.columns([2, 1])

    with col1:
        # Centrage dynamique : si un spot est choisi, on centre sur lui, sinon sur Paris
        if selected_spot_name != "Tous les spots visibles":
            row_sel = df_filtered[df_filtered[c_name] == selected_spot_name].iloc[0]
            v_lat, v_lon, v_zoom = row_sel['lat'], row_sel['lon'], 16
        else:
            v_lat, v_lon, v_zoom = 48.8566, 2.3522, 12

        view_state = pdk.ViewState(latitude=v_lat, longitude=v_lon, zoom=v_zoom, pitch=0)
        
        icon_config = {"url": "https://img.icons8.com/ios-filled/100/d92644/marker.png", "width": 100, "height": 100, "anchorY": 100}
        df_filtered["icon_data"] = [icon_config for _ in range(len(df_filtered))]

        layer = pdk.Layer(
            "IconLayer",
            data=df_filtered,
            get_icon="icon_data",
            get_size=3,
            size_scale=10,
            get_position=["lon", "lat"],
            pickable=True,
        )

        st.pydeck_chart(pdk.Deck(
            map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
            initial_view_state=view_state,
            layers=[layer],
            tooltip={"html": f"<b>{{{c_name}}}</b>", "style": {"backgroundColor": "#efede1", "color": "#202b24"}}
        ))

    with col2:
        # Affichage du résultat
        if selected_spot_name != "Tous les spots visibles":
            df_display = df_filtered[df_filtered[c_name] == selected_spot_name]
        else:
            df_display = df_filtered.head(50)
            st.write(f"*{len(df_filtered)} spots trouvés*")

        for _, row in df_display.iterrows():
            with st.expander(f"**{row[c_name]}**", expanded=True):
                st.write(f"📍 {row[c_addr]}")
                if col_tags and pd.notna(row[col_tags]):
                    tags_html = "".join([f'<span class="tag-label">{t.strip()}</span>' for t in str(row[col_tags]).split(',')])
                    st.markdown(tags_html, unsafe_allow_html=True)
                if c_link and pd.notna(row[c_link]):
                    st.write("")
                    st.link_button("+", row[c_link])

except Exception as e:
    st.error(f"Erreur : {e}")
