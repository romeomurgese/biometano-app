import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from math import radians, cos, sin, asin, sqrt
import numpy as np
from PIL import Image
import requests
from io import BytesIO

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(layout="wide", page_title="Bioenerys Srl - Simulatore Gare")
st.title("🌱 Bioenerys Srl - Simulatore gara impianti trattamento rifiuti in Italia")

# =========================
# LOGO
# =========================
logo_url = "https://raw.githubusercontent.com/romeomurgese/biometano-app/main/bioenerys_logo.png"
try:
    response = requests.get(logo_url)
    if response.status_code == 200:
        logo_img = Image.open(BytesIO(response.content))
        st.image(logo_img, width=120)
    else:
        st.write("🔹 Logo Bioenerys non disponibile")
except:
    st.write("🔹 Logo Bioenerys non disponibile")

# =========================
# FUNZIONI
# =========================
def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1))*cos(radians(lat2))*sin(dlon/2)**2
    return 2 * R * asin(sqrt(a))

def circle_coords(lat, lon, r_km, n_points=100):
    lat_circle = []
    lon_circle = []
    for theta in np.linspace(0, 2*np.pi, n_points):
        dlat = (r_km/6371) * (180/np.pi) * np.sin(theta)
        dlon = (r_km/6371) * (180/np.pi) * np.cos(theta) / cos(radians(lat))
        lat_circle.append(lat + dlat)
        lon_circle.append(lon + dlon)
    return lat_circle, lon_circle

# =========================
# LOAD DATI IMPIANTI
# =========================
@st.cache_data
def load_data():
    df = pd.read_excel("impianti_geocodificati.xlsx")
    df.columns = df.columns.str.lower()
    df["totale (t)"] = pd.to_numeric(df["totale (t)"], errors='coerce').fillna(1)
    df["latitudine"] = pd.to_numeric(df["latitudine"], errors='coerce')
    df["longitudine"] = pd.to_numeric(df["longitudine"], errors='coerce')
    df = df.dropna(subset=["latitudine", "longitudine"])
    return df

df = load_data()

# =========================
# LOAD COMUNI
# =========================
@st.cache_data
def load_comuni():
    df_comuni = pd.read_csv("comuni.csv")
    df_comuni["nome"] = df_comuni["name"].str.lower().str.strip()
    return df_comuni

df_comuni = load_comuni()
lista_comuni = df_comuni["nome"].sort_values().unique()

# =========================
# SIDEBAR
# =========================
st.sidebar.header("⚙️ Parametri gara")
comune_sel = st.sidebar.selectbox("📍 Comune di gara", lista_comuni)
raggio_km = st.sidebar.slider("📏 Raggio impianti (km)", 1, 200, 50)
tariffa_base = st.sidebar.number_input("💰 Tariffa base gara (€ / t)", min_value=0.0, value=50.0, step=1.0)

# Input manuale di impianti extra
impianti_nomi = df["comune"].str.lower().sort_values().unique()
impianto_extra = st.sidebar.text_input(
    "🔹 Aggiungi impianto manualmente (fuori dal raggio)", 
    "", 
    help="Scrivi il nome di un impianto e premi invio"
)

# Attiva color map
color_map_on = st.sidebar.checkbox("🎨 Color map secondo totale (t)")

# =========================
# TROVA COMUNE SELEZIONATO
# =========================
comune_sel_clean = str(comune_sel).strip().lower()
match = df_comuni[df_comuni["nome"] == comune_sel_clean]
if match.empty:
    st.error("❌ Comune non trovato")
    st.stop()

row_comune = match.iloc[0]
lat_centro = row_comune["lat"]
lon_centro = row_comune["lng"]

# =========================
# CALCOLO DISTANZE
# =========================
df["distanza_km"] = df.apply(
    lambda r: haversine(lat_centro, lon_centro, r["latitudine"], r["longitudine"]), axis=1
).round(1)
df_filtrato = df[df["distanza_km"] <= raggio_km]

# Aggiungi impianto extra se valido
if impianto_extra.strip() != "":
    imp_sel = df[df["comune"].str.lower() == impianto_extra.strip().lower()]
    if not imp_sel.empty:
        df_filtrato = pd.concat([df_filtrato, imp_sel]).drop_duplicates()

st.write(f"🔎 Impianti trovati nel raggio o selezionati: {len(df_filtrato)}")
if df_filtrato.empty:
    st.warning("⚠️ Nessun impianto trovato")

# =========================
# MAPPA CON SCALING RAGIONEVOLE PER COLOR MAP
# =========================
st.subheader("📍 Mappa impianti e raggio di gara")
lat_circle, lon_circle = circle_coords(lat_centro, lon_centro, raggio_km)

map_center = {"lat": lat_centro, "lon": lon_centro}
default_zoom = 7  # zoom fisso per il comune + raggio

fig = go.Figure()

# Cerchio raggio
fig.add_trace(go.Scattermapbox(
    lat=lat_circle,
    lon=lon_circle,
    mode='lines',
    fill='toself',
    fillcolor='rgba(0,200,0,0.1)',
    line=dict(color='green', width=2),
    name=f"Raggio {raggio_km} km"
))

# Comune centrale
fig.add_trace(go.Scattermapbox(
    lat=[lat_centro],
    lon=[lon_centro],
    mode='markers+text',
    marker=dict(size=14, color='red'),
    text=[comune_sel.capitalize()],
    textposition="top right",
    name="Comune di gara"
))

if color_map_on and not df_filtrato.empty:
    # Scaling dimensioni cerchi
    min_size = 8
    max_size = 30
    tot_values = df_filtrato["totale (t)"].values
    sizes = np.interp(tot_values, (tot_values.min(), tot_values.max()), (min_size, max_size))

    fig.add_trace(go.Scattermapbox(
        lat=df_filtrato["latitudine"],
        lon=df_filtrato["longitudine"],
        mode='markers+text',
        marker=dict(
            size=sizes,
            sizemode='area',
            color=tot_values,
            colorscale="YlOrRd",
            showscale=True,
            colorbar=dict(title="Totale (t)")
        ),
        text=df_filtrato["comune"],
        textposition="top center",
        hovertemplate="%{text}<br>Totale: %{marker.color}<br>Distanza: %{customdata[0]} km",
        customdata=df_filtrato[["distanza_km"]]
    ))
else:
    fig.add_trace(go.Scattermapbox(
        lat=df_filtrato["latitudine"],
        lon=df_filtrato["longitudine"],
        mode='markers+text',
        marker=dict(size=10, color='black'),
        text=df_filtrato["comune"],
        textposition="top center",
        hovertemplate="%{text}<br>Totale: %{customdata[0]} t<br>Distanza: %{customdata[1]} km",
        customdata=df_filtrato[["totale (t)","distanza_km"]]
    ))

# Layout fisso e leggibile
fig.update_layout(
    mapbox_style="open-street-map",
    mapbox_center=map_center,
    mapbox_zoom=default_zoom,
    height=650,
    legend=dict(
        title="Legenda",
        yanchor="top",
        y=0.99,
        xanchor="left",
        x=0.01,
        bgcolor="rgba(0,0,0,0.5)",
        font=dict(color="white")
    ),
    margin=dict(l=10, r=10, t=10, b=10)
)

st.plotly_chart(fig, use_container_width=True)

# =========================
# TABELLA IMPIANTI
# =========================
# =========================
# TABELLA INTERATTIVA IMPiANTI
# =========================
st.subheader("📋 Impianti partecipanti")

# Aggiungi colonne per checkbox e tariffa
df_filtrato = df_filtrato.copy()
if "in_gara" not in df_filtrato.columns:
    df_filtrato["in_gara"] = True  # di default tutti selezionati
if "tariffa" not in df_filtrato.columns:
    df_filtrato["tariffa"] = raggio_km  # puoi mettere qui tariffa base di default o 0

# Colonne visibili
colonne_visibili = ["in_gara", "comune", "tipologia", "totale (t)", "distanza_km", "tariffa"]

# Editor interattivo
edited_df = st.data_editor(
    df_filtrato[colonne_visibili],
    column_config={
        "in_gara": st.column_config.CheckboxColumn("In gara"),
        "tariffa": st.column_config.NumberColumn(
            "Tariffa (€)", min_value=0.0, step=1.0, format="%0.2f"
        ),
    },
    hide_index=True,
    key="impianti_editor"
)

# Filtra solo impianti flaggati
df_finale = edited_df[edited_df["in_gara"] == True]

st.write(f"🔎 Impianti confermati in gara: {len(df_finale)}")
