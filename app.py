import streamlit as st
import pandas as pd
import folium
from st_folium import st_folium

# Style et Données (identiques à votre code précédent)
# ... [Partie chargement CSV et filtres conservée] ...

with col1:
    # Création de la carte Folium
    m = folium.Map(location=[48.8566, 2.3522], zoom_start=12, tiles="cartodbpositron")

    # Ajout des marqueurs
    for _, row in df_filtered.iterrows():
        # On crée une popup HTML simple
        popup_content = f"<b>{row[c_name]}</b><br>{row[c_addr]}"
        
        folium.CircleMarker(
            location=[row['lat'], row['lon']],
            radius=6,
            popup=popup_content,
            color="#d92644",
            fill=True,
            fill_color="#d92644",
            fill_opacity=0.7,
        ).add_to(m)

    # L'action magique : capture du clic
    output = st_folium(m, width=700, height=500, key="ma_carte")

# 4. Action au clic détectée par Folium
if output["last_object_clicked"]:
    # Ici, on peut déclencher votre pop-up ou filtrer la colonne 2
    st.sidebar.success(f"Vous avez cliqué sur un point !")
    # Les coordonnées cliquées sont dans output["last_object_clicked"]
