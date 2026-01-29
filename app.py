import streamlit as st
import pandas as pd
import pydeck as pdk
import re

# 1. Configuration de la page
st.set_page_config(page_title="Mes spots", layout="wide")
st.cache_data.clear() 

# 2. Style CSS
st.markdown(f"""
    <style>
    .stApp {{ background-color: #efede1 !important; }}
    header[data-testid="stHeader"] {{ display: none !important; }}
    div[data-testid="stDecoration"] {{ display: none !important; }}
    .main .block-container {{ padding-top: 2rem !important; }}

    h1 {{ color: #d92644 !important; margin-top: -30px !important; }}
    html, body, [class*="st-"], p, div, span, label, h3 {{ color: #202b24 !important; }}

    /* Expanders */
    div[data-testid="stExpander"] {{
        background-color: #efede1 !important;
        border: 0.25px solid #b6beb1 !important;
        border-radius: 8px !important;
        margin-bottom: 10px !important;
    }}
    div[data-testid="stExpander"] summary:hover {{ background-color: #b6beb1 !important; }}
    div[data-testid="stExpander"] details[open] summary {{
        background-color: #b6beb1 !important;
        border-bottom: 1px solid #b6beb1 !important;
    }}
    div[data-testid="stExpander"] details[open] > div[role="region"] {{
        background-color: #efede1 !important;
    }}

    /* Switch */
    div[role="switch"] {{ background-color: #b6beb1 !important; }}
    div[aria-checked="true"][role="switch"] {{ background-color: #d92644 !important; }}
    div[role="switch"] > div:last-child {{ background-color: #efede1 !important; box-shadow: none !important; }}

    /* Recherche */
    div[data-testid="stTextInput"] div[data-baseweb="input"] {{ background-color: #b6beb1 !important; border: none !important; }}
    div[data-testid="stTextInput"] input {{ color: #202b24 !important; -webkit-text-fill-color: #202b24 !important; }}

    /* Bouton Y aller */
    .stLinkButton a {{ 
        background-color: #7397a3 !important; 
        color: #efede1 !important; 
        border: none !important; 
        border-radius: 8px !important; 
        font-weight: bold !important; 
        text-decoration: none !important;
        display: flex !important;
        justify-content: center !important;
    }}
    .tag-label {{ display: inline-block; background-color: #b6beb1; color: #202b24; padding: 2px 10px; border-radius: 15px; margin-right: 5px; font-size: 0.75rem; font-weight: bold; }}
    </style>
    """, unsafe_allow_html=True)

def get_precise_coords(url):
    if pd.isna(url): return None, None
    match = re.search(r'@(-?\d+\.\d+),(-?\d+\.\d+)', str(url))
    if match: return float(match.group(1)), float(match.group(2))
    return None, None

st.title("Mes spots")

try:
    # 3. Chargement des Données
    df = pd.read_csv("Spottable v3.csv", sep=None, engine='python')
    df.columns = df.columns.str.strip().str.lower()
    
    lat_col = next((c for c in df.columns if c in ['latitude', 'lat']), None)
    lon_col = next((c for c in df.columns if c in ['longitude', 'lon']), None)
    c_link = next((c for c in df.columns if any(w in c for w in ['map', 'lien', 'geo'])), None)

    if lat_col and lon_col:
        df['lat'] = pd.to_numeric(df[lat_col].astype(str).str.replace(',', '.'), errors='coerce')
        df['lon'] = pd.to_numeric(df[lon_col].astype(str).str.replace(',', '.'), errors='coerce')

    if c_link:
        df['precise_tuple'] = df[c_link].apply(get_precise_coords)
        df['lat'] = df.apply(lambda r: r['precise_tuple'][0] if r['precise_tuple'][0] else r['lat'], axis=1)
        df['lon'] = df.apply(lambda r: r['precise_tuple'][1] if r['precise_tuple'][1] else r['lon'], axis=1)

    df = df.dropna(subset=['lat', 'lon'])
    c_name = next((c for c in df.columns if c in ['name', 'nom']), df.columns[0])
    c_addr = next((c for c in df.columns if c in ['address', 'adresse']), df.columns[1])
    col_tags = next((c for c in df.columns if c == 'tags'), None)

    # --- RECHERCHE ---
    col_search, _ = st.columns([1, 2])
    with col_search:
        search_query = st.text_input("Rechercher", placeholder="Rechercher un spot", label_visibility="collapsed")
    df_filtered = df[df[c_name].str.contains(search_query, case=False, na=False)].copy() if search_query else df.copy()

    # --- FILTRES ---
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
        # CENTRAGE FIXE SUR PARIS
        view_state = pdk.ViewState(latitude=48.8566, longitude=2.3522, zoom=12, pitch=0)

        # Correction de la couche IconLayer (Suppression de l'erreur JSON)
        icon_data = {
            "url": "https://img.icons8.com/ios-filled/100/d92644/marker.png",
            "width": 100,
            "height": 100,
            "anchorY": 100
        }
        df_filtered["icon_data"] = [icon_data for _ in range(len(df_filtered))]

        layer = pdk.Layer(
            "IconLayer",
            data=df_filtered,
            get_icon="icon_data",
            get_size=4,
            size_scale=10,
            get_position=["lon", "lat"],
            pickable=True,
            opacity=0.8
        )

        st.pydeck_chart(pdk.Deck(
            map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
            initial_view_state=view_state,
            layers=[layer],
            tooltip={"text": "{"+c_name+"}"}
        ))

    with col2:
        st.write(f"*{len(df_filtered)} spots trouvés (Top 50)*")
        for _, row in df_filtered.head(50).iterrows():
            with st.expander(f"**{row[c_name]}**"):
                st.write(f"📍 {row[c_addr]}")
                if col_tags and pd.notna(row[col_tags]):
                    tags = "".join([f'<span class="tag-label">{t.strip()}</span>' for t in str(row[col_tags]).split(',')])
                    st.markdown(tags, unsafe_allow_html=True)
                if c_link and pd.notna(row[row[c_link]]): # Petite sécurité sur le lien
                    st.link_button("**Y aller**", row[c_link], use_container_width=True)

except Exception as e:
    st.error(f"Erreur : {e}")
