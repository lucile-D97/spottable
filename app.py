import streamlit as st
import pandas as pd
import pydeck as pdk
import re

# 1. Configuration de la page
st.set_page_config(page_title="Mes spots", layout="wide")

# 2. Style CSS
st.markdown(f"""
    <style>
    .stApp {{ background-color: #efede1 !important; }}
    header[data-testid="stHeader"] {{ display: none !important; }}
    div[data-testid="stDecoration"] {{ display: none !important; }}
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
        border-radius: 8px !important; 
        font-weight: bold !important; 
        display: flex !important;
        justify-content: center !important;
    }}
    
    .tag-label {{ display: inline-block; background-color: #b6beb1; color: #202b24; padding: 2px 10px; border-radius: 15px; margin-right: 5px; font-size: 0.75rem; font-weight: bold; }}
    
    div[data-testid="stTextInput"] div[data-baseweb="input"] {{ background-color: #b6beb1 !important; border: none !important; }}
    div[role="switch"] {{ background-color: #b6beb1 !important; }}
    div[aria-checked="true"][role="switch"] {{ background-color: #d92644 !important; }}
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
    c_name = next((c for c in df.columns if c in ['name', 'nom']), df.columns[0])
    c_addr = next((c for c in df.columns if c in ['address', 'adresse']), df.columns[1])

    # --- RECHERCHE ET FILTRES ---
    col_search, _ = st.columns([1, 2])
    with col_search:
        search_query = st.text_input("Rechercher", placeholder="Rechercher un spot", label_visibility="collapsed")
    
    df_filtered = df[df[c_name].str.contains(search_query, case=False, na=False)].copy()

    st.write("### Filtrer")
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

    # --- AFFICHAGE ---
    col1, col2 = st.columns([2, 1])

    with col1:
        # Retour à l'IconLayer pour les pins
        layer = pdk.Layer(
            "IconLayer",
            data=df_filtered,
            get_icon="""{
                "url": "https://img.icons8.com/ios-filled/100/d92644/marker.png",
                "width": 100,
                "height": 100,
                "anchorY": 100
            }""",
            get_size=4,
            size_scale=10,
            get_position=["lon", "lat"],
            pickable=True,
            auto_highlight=True # Effet de survol foncé
        )

        st.pydeck_chart(pdk.Deck(
            map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
            initial_view_state=pdk.ViewState(latitude=48.8566, longitude=2.3522, zoom=12),
            layers=[layer],
            tooltip={
                "html": f"<div style='color: #202b24;'><b>{{{c_name}}}</b></div>",
                "style": {"backgroundColor": "#efede1", "color": "#202b24", "fontSize": "14px", "padding": "10px", "borderRadius": "8px"}
            }
        ))

    with col2:
        st.write(f"*{len(df_filtered)} spots trouvés*")
        # Affichage simple des expanders sans logique de clic bloquante
        for _, row in df_filtered.head(50).iterrows():
            with st.expander(f"**{row[c_name]}**"):
                st.write(f"📍 {row[c_addr]}")
                if col_tags and pd.notna(row[col_tags]):
                    tags_html = "".join([f'<span class="tag-label">{t.strip()}</span>' for t in str(row[col_tags]).split(',')])
                    st.markdown(tags_html, unsafe_allow_html=True)
                if c_link and pd.notna(row[c_link]):
                    st.write("")
                    st.link_button("**Y aller**", row[c_link], use_container_width=True)

except Exception as e:
    st.error(f"Erreur : {e}")
