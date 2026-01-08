import streamlit as st
import pandas as pd
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
import time

# Configuration de la page
st.set_page_config(page_title="Mes spots", layout="wide")

st.title("Mes spots")

# --- FONCTION DE GÉOCODAGE (Conversion Adresse -> GPS) ---
geolocator = Nominatim(user_agent="my-spots_app_v1")
geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)

@st.cache_data
def get_lat_lon(address):
    try:
        location = geolocator.geocode(address)
        if location:
            return location.latitude, location.longitude
        return None, None
    except:
        return None, None

# --- CHARGEMENT DES DONNÉES ---
try:
    # Lecture du CSV avec détection automatique du séparateur (virgule ou point-virgule)
    df = pd.read_csv("Spottable v1.csv", sep=None, engine='python')
    df.columns = df.columns.str.strip().str.lower() # Nettoyage des noms de colonnes

    # Si les colonnes lat/lon n'existent pas, on les crée
    if 'lat' not in df.columns or 'lon' not in df.columns:
        with st.spinner("Calcul des coordonnées GPS en cours... Merci de patienter."):
            coords = df['address'].apply(get_lat_lon)
            df[['lat', 'lon']] = pd.DataFrame(coords.tolist(), index=df.index)

    # --- FILTRES ---
    # On récupère tous les tags uniques
    all_tags = set()
    df['Tags'].str.split(',').apply(lambda x: [all_tags.add(t.strip()) for t in x if isinstance(x, list)])
    
    selected_tags = st.multiselect("Filtrer par tags :", sorted(list(all_tags)))

    # Logique de filtrage
    if selected_tags:
        mask = df['Tags'].apply(lambda x: any(t.strip() in selected_tags for t in str(x).split(',')))
        df_filtered = df[mask]
    else:
        df_filtered = df

    # --- AFFICHAGE ---
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("📍 Carte")
        # On enlève les lignes qui n'ont pas pu être géolocalisées pour la carte
        df_map = df_filtered.dropna(subset=['lat', 'lon'])
        if not df_map.empty:
            st.map(df_map)
        else:
            st.warning("Aucune coordonnée disponible pour la carte.")

    with col2:
        st.subheader("📋 Liste des établissements")
        if df_filtered.empty:
            st.info("Aucun résultat pour ces filtres.")
        for _, row in df_filtered.iterrows():
            with st.expander(f"**{row['name'].upper()}**"):
                st.write(f"📍 {row['address']}")
                st.caption(f"Tags : {row['tags']}")
                if 'google maps' in df.columns: # Si vous avez mis une colonne lien
                    st.link_button("Voir sur Google Maps", row['google maps'])

except FileNotFoundError:
    st.error("Erreur : Le fichier 'Spottable v1.csv' est introuvable sur GitHub.")
except Exception as e:
    st.error(f"Une erreur est survenue : {e}")
