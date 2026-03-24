# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import plotly.graph_objects as go
import io
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
from streamlit_plotly_events import plotly_events

st.set_page_config(layout="wide")
st.title("🌱 Impianti di trattamento rifiuti urbani in Italia")

# =========================
# LOAD DATA
@st.cache_data
def load_data():
    df = pd.read_excel("impianti.xlsx")
    df.columns = df.columns.str.lower()
    return df

df = load_data()
if "totale (t)" not in df.columns:
    st.error("Colonna 'totale (t)' mancante!")
    st.stop()
df["totale (t)"] = pd.to_numeric(df["totale (t)"], errors='coerce').fillna(0)

# =========================
# FILTRI ORIZZONTALI
tipologie = df["tipologia"].dropna().unique().tolist()
col1, col2, col3, col4 = st.columns([2,2,1,1])
with col1:
    tipologia_selezionata = st.multiselect("Tipologia impianti", options=tipologie, default=tipologie)
with col2:
    comune_input = st.text_input("Comune di riferimento", "Milano")
with col3:
    raggio_km = st.slider("Raggio (km)", 1, 100, 20)
with col4:
    if st.button("🔄 Reset selezione"):
        if "selected_comune" in st.session_state:
            del st.session_state["selected_comune"]
        st.experimental_rerun()

# =========================
# GEOLOCALIZZAZIONE
geolocator = Nominatim(user_agent="biometano_app")
location = geolocator.geocode(comune_input + ", Italia")
if location is None:
    st.error("Comune non trovato")
    st.stop()
lat_centro, lon_centro = location.latitude, location.longitude
lat_col, lon_col = "latitudine", "longitudine"
if lat_col not in df.columns or lon_col not in df.columns:
    st.error("Colonne lat/lon mancanti")
    st.stop()

# =========================
# CALCOLO DISTANZA
df["distanza_km"] = df.apply(lambda r: geodesic((lat_centro, lon_centro), (r[lat_col], r[lon_col])).km, axis=1).round(1)
df_filtrato = df[(df["distanza_km"] <= raggio_km) & (df["tipologia"].isin(tipologia_selezionata))].copy()
df_filtrato = df_filtrato.dropna(subset=[lat_col, lon_col])

# =========================
# KPI
col1, col2, col3 = st.columns(3)
col1.metric("Impianti trovati", len(df_filtrato))
col2.metric("Raggio selezionato", f"{raggio_km} km")
col3.metric("Distanza media", f"{df_filtrato['distanza_km'].mean():.1f} km" if len(df_filtrato) > 0 else "-")

# =========================
# COSTRUZIONE FIGURA CON GO.FIGURE
st.write("### 🗺️ Mappa interattiva")
fig = go.Figure()

for idx, row in df_filtrato.iterrows():
    marker_color = "red" if st.session_state.get("selected_comune") == row["comune"] else "orange"
    fig.add_trace(go.Scattermapbox(
        lat=[row[lat_col]],
        lon=[row[lon_col]],
        mode="markers+text",
        marker=go.scattermapbox.Marker(
            size=20,
            color=marker_color,
            line=dict(width=1, color="black")
        ),
        text=f"{row['totale (t)']:.0f} t\n{row['distanza_km']:.1f} km",
        textposition="top center",
        hoverinfo="text",
        name=row["comune"]
    ))

fig.update_layout(
    mapbox_style="open-street-map",
    mapbox_center={"lat": lat_centro, "lon": lon_centro},
    mapbox_zoom=7,
    margin=dict(r=0, t=0, l=0, b=0),
    showlegend=False
)

# =========================
# CLICK MAPPA
selected_points = plotly_events(fig, click_event=True, hover_event=False)
if selected_points:
    st.session_state["selected_comune"] = selected_points[0]["name"]

st.plotly_chart(fig, use_container_width=True)

# =========================
# TABELLA INTERATTIVA
st.write("### 📊 Tabella impianti")
df_tabella = df_filtrato.copy()
if st.session_state.get("selected_comune"):
    df_tabella = df_tabella[df_tabella["comune"] == st.session_state["selected_comune"]]

gb = GridOptionsBuilder.from_dataframe(df_tabella)
gb.configure_selection(selection_mode="single", use_checkbox=True)
grid_options = gb.build()
grid_response = AgGrid(
    df_tabella,
    gridOptions=grid_options,
    update_mode=GridUpdateMode.SELECTION_CHANGED,
    height=400,
    fit_columns_on_grid_load=True
)

# CLICK TABELLA
selected_rows = grid_response['selected_rows']
if selected_rows:
    st.session_state["selected_comune"] = selected_rows[0]['comune']
    st.experimental_rerun()

# =========================
# DOWNLOAD EXCEL
output = io.BytesIO()
df_tabella.to_excel(output, index=False, engine='openpyxl')
output.seek(0)
st.download_button(
    "💾 Scarica dati filtrati in Excel",
    data=output,
    file_name="dati_filtrati.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
