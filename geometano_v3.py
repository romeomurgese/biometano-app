import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from math import radians, cos, sin, asin
from io import BytesIO
from PIL import Image
import requests

st.set_page_config(layout="wide")
st.title("🌱 Bioenerys Srl - Simulatore gara")

# =========================
# FUNZIONI
# =========================
def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1))*cos(radians(lat2))*sin(dlon/2)**2
    return 2 * R * asin(np.sqrt(a))

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
# CARICA DATI IMPIANTI
# =========================
@st.cache_data
def load_data():
    df = pd.read_excel("impianti_geocodificati.xlsx")
    df.columns = df.columns.str.lower()
    df["totale (t)"] = pd.to_numeric(df["totale (t)"], errors='coerce').fillna(1)
    df["latitudine"] = pd.to_numeric(df["latitudine"], errors='coerce')
    df["longitudine"] = pd.to_numeric(df["longitudine"], errors='coerce')
    df["flag"] = True  # tutti selezionati di default
    df["offerta"] = np.nan  # input tariffa
    return df

df = load_data()

# =========================
# CARICA COMUNI
# =========================
@st.cache_data
def load_comuni():
    df_comuni = pd.read_csv("comuni.csv")
    df_comuni["nome"] = df_comuni["name"].str.lower().str.strip()
    return df_comuni

df_comuni = load_comuni()
lista_comuni = df_comuni["nome"].sort_values().unique()

# =========================
# SIDEBAR - PARAMETRI GENERALI
# =========================
st.sidebar.header("⚙️ Parametri generali")
comune_sel = st.sidebar.selectbox("📍 Comune di gara", lista_comuni)
raggio_km = st.sidebar.slider("📏 Raggio impianti (km)", 1, 200, 50)
tariffa_base = st.sidebar.number_input("💰 Tariffa base gara (€)", min_value=0.0, value=100.0)

# Filtra tipologie impianti
tipologie = df["tipologia"].sort_values().unique()
tipologie_sel = st.sidebar.multiselect("🏭 Filtra tipologie impianto", tipologie, default=list(tipologie))

# Input impianti extra (fuori raggio)
impianti_nomi = df["comune"].str.lower().sort_values().unique()
impianti_extra_input = st.sidebar.text_area(
    "🔹 Aggiungi impianti extra (uno per riga, fuori dal raggio)",
    placeholder="Scrivi un impianto per riga"
)
impianti_extra = [x.strip().lower() for x in impianti_extra_input.split("\n") if x.strip() != ""]

# Input penale chilometrica
penale_km = st.sidebar.number_input(
    "⚖️ Penalità €/km fuori raggio",
    min_value=0.0,
    value=0.5,
    step=0.1
)

# =========================
# FILTRAGGIO COMUNE
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
# CALCOLO DISTANZE E FILTRAGGI
# =========================
df["distanza_km"] = df.apply(lambda r: haversine(lat_centro, lon_centro, r["latitudine"], r["longitudine"]), axis=1).round(1)
df_filtrato = df[(df["distanza_km"] <= raggio_km) & (df["tipologia"].isin(tipologie_sel))]

# Aggiungi impianti extra validi
for imp in impianti_extra:
    extra_sel = df[(df["comune"].str.lower() == imp) & (df["tipologia"].isin(tipologie_sel))]
    if not extra_sel.empty:
        df_filtrato = pd.concat([df_filtrato, extra_sel])

# Assicurati di mostrare solo quelli flaggati
df_finale = df_filtrato[df_filtrato["flag"] == True].drop_duplicates()

# =========================
# TABELLA INTERATTIVA SOPRA MAPPA
# =========================
st.subheader("📋 Impianti partecipanti")

# Prepara tabella compatta
df_table = df_filtrato.copy()

df_table = df_table[[
    "flag",
    "comune",
    "tipologia",
    "totale (t)",
    "distanza_km",
    "offerta"
]]

df_table = df_table.rename(columns={
    "flag": "Seleziona",
    "comune": "Impianto",
    "tipologia": "Tipologia",
    "totale (t)": "Quantità (t)",
    "distanza_km": "Distanza (km)",
    "offerta": "Offerta (€)"
})

# Editor tabellare compatto
edited_df = st.data_editor(
    df_table,
    use_container_width=True,
    height=300,
    column_config={
        "Seleziona": st.column_config.CheckboxColumn(),
        "Offerta (€)": st.column_config.NumberColumn(min_value=0, step=1),
    },
    disabled=["Impianto", "Tipologia", "Quantità (t)", "Distanza (km)"]
)

# Riporta modifiche nel dataframe originale
df_filtrato["flag"] = edited_df["Seleziona"].values
df_filtrato["offerta"] = edited_df["Offerta (€)"].values

# Filtra finale
df_finale = df_filtrato[df_filtrato["flag"] == True].copy()
    
df_finale = df_filtrato[df_filtrato["flag"] == True].copy()

# =========================
# CALCOLO PENALITÀ GARA
# =========================
df_finale["km_fuori_raggio"] = (df_finale["distanza_km"] - raggio_km).clip(lower=0)

df_finale["penalita"] = df_finale["km_fuori_raggio"] * penale_km

df_finale["offerta_effettiva"] = df_finale["offerta"] - df_finale["penalita"]

# Ranking gara (più alto = migliore)
df_finale = df_finale.sort_values("offerta_effettiva", ascending=False)

df_finale["ranking"] = range(1, len(df_finale) + 1)

st.markdown("---")


st.subheader("🏆 Risultato gara")

df_gara = df_finale[[
    "ranking",
    "comune",
    "offerta",
    "km_fuori_raggio",
    "penalita",
    "offerta_effettiva"
]].rename(columns={
    "comune": "Impianto",
    "offerta": "Offerta (€)",
    "km_fuori_raggio": "Km fuori raggio",
    "penalita": "Penalità (€)",
    "offerta_effettiva": "Offerta finale (€)"
})

st.dataframe(df_gara, use_container_width=True)

# =========================
# MAPPA
# =========================
st.subheader("📍 Mappa impianti e raggio di gara")
lat_circle, lon_circle = circle_coords(lat_centro, lon_centro, raggio_km)

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

# Comune di gara
fig.add_trace(go.Scattermapbox(
    lat=[lat_centro],
    lon=[lon_centro],
    mode='markers+text',
    marker=dict(size=14, color='red'),
    text=[comune_sel],
    textposition="top right",
    name="Comune di gara"
))

# Impianti finali
if not df_finale.empty:
    fig.add_trace(go.Scattermapbox(
        lat=df_finale["latitudine"],
        lon=df_finale["longitudine"],
        mode='markers+text',
        marker=dict(size=10, color="black"),
        text=df_finale["comune"],
        textposition="top center",
        name="Impianti"
    ))

fig.update_layout(
    mapbox_style="open-street-map",
    mapbox=dict(center=dict(lat=lat_centro, lon=lon_centro), zoom=6),
    height=900,
    legend=dict(title="Legenda", yanchor="top", y=0.99, xanchor="left", x=0.01,
                bgcolor="rgba(50,50,50,0.7)", font=dict(color="white"))
)

st.plotly_chart(fig, use_container_width=True)
