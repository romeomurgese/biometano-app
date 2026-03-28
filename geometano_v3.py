import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from math import radians, cos, sin, asin

st.set_page_config(layout="wide")
st.title("🌱 Bioenerys Srl - Simulatore gara")

# =========================
# SESSION STATE INIT
# =========================
if "offerte_custom" not in st.session_state:
    st.session_state.offerte_custom = {}

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
# LOAD DATI
# =========================
@st.cache_data
def load_data():
    df = pd.read_excel("impianti_geocodificati.xlsx")
    df.columns = df.columns.str.lower()
    df["totale (t)"] = pd.to_numeric(df["totale (t)"], errors='coerce').fillna(1)
    df["latitudine"] = pd.to_numeric(df["latitudine"], errors='coerce')
    df["longitudine"] = pd.to_numeric(df["longitudine"], errors='coerce')
    df["flag"] = True
    return df

df = load_data()

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
st.sidebar.header("⚙️ Parametri generali")

comune_sel = st.sidebar.selectbox("📍 Comune di gara", lista_comuni)
raggio_km = st.sidebar.slider("📏 Raggio (km)", 1, 200, 50)
tariffa_base = st.sidebar.number_input("💰 Tariffa base (€)", value=100.0)

tipologie = df["tipologia"].dropna().unique()
tipologie_sel = st.sidebar.multiselect("🏭 Tipologie", tipologie, default=list(tipologie))

penale_km = st.sidebar.number_input("⚖️ Penalità €/km", value=0.5)

# EXTRA impianti (dropdown serio)
df["label"] = df["comune"] + " (" + df["provincia"].fillna("") + ")"
extra_sel = st.sidebar.multiselect(
    "➕ Aggiungi impianti extra",
    df["label"].unique()
)

# =========================
# CENTRO COMUNE
# =========================
row = df_comuni[df_comuni["nome"] == comune_sel].iloc[0]
lat_centro = row["lat"]
lon_centro = row["lng"]

# =========================
# DISTANZE
# =========================
df["distanza_km"] = df.apply(
    lambda r: haversine(lat_centro, lon_centro, r["latitudine"], r["longitudine"]),
    axis=1
).round(1)

# =========================
# FILTRI
# =========================
df_filtrato = df[
    (df["tipologia"].isin(tipologie_sel)) &
    (df["distanza_km"] <= raggio_km)
]

# aggiungi extra
if extra_sel:
    df_extra = df[df["label"].isin(extra_sel)]
    df_filtrato = pd.concat([df_filtrato, df_extra])

df_filtrato = df_filtrato.drop_duplicates()

# =========================
# OFFERTA INTELLIGENTE
# =========================
offerte = []
for idx, row in df_filtrato.iterrows():
    key = row["label"]

    if key in st.session_state.offerte_custom:
        offerte.append(st.session_state.offerte_custom[key])
    else:
        offerte.append(tariffa_base)

df_filtrato["offerta"] = offerte

# =========================
# TABELLA
# =========================
st.subheader("📋 Impianti partecipanti")

df_table = df_filtrato[[
    "flag", "label", "tipologia", "totale (t)", "distanza_km", "offerta"
]].rename(columns={
    "flag": "Seleziona",
    "label": "Impianto",
    "tipologia": "Tipologia",
    "totale (t)": "Quantità",
    "distanza_km": "Distanza",
    "offerta": "Offerta (€)"
})

# altezza dinamica
row_height = 35
dynamic_height = min(600, 40 + len(df_table) * row_height)

edited = st.data_editor(
    df_table,
    use_container_width=True,
    height=dynamic_height,
    column_config={
        "Seleziona": st.column_config.CheckboxColumn(),
        "Offerta (€)": st.column_config.NumberColumn(min_value=0)
    },
    disabled=["Impianto", "Tipologia", "Quantità", "Distanza"]
)

# salva modifiche utente
for i, r in edited.iterrows():
    key = r["Impianto"]
    st.session_state.offerte_custom[key] = r["Offerta (€)"]

df_filtrato["flag"] = edited["Seleziona"].values
df_filtrato["offerta"] = edited["Offerta (€)"].values

df_finale = df_filtrato[df_filtrato["flag"]].copy()

# =========================
# CALCOLO GARA
# =========================
df_finale["km_fuori"] = (df_finale["distanza_km"] - raggio_km).clip(lower=0)
df_finale["penalita"] = df_finale["km_fuori"] * penale_km
df_finale["offerta_finale"] = df_finale["offerta"] - df_finale["penalita"]

df_finale = df_finale.sort_values("offerta_finale", ascending=False)
df_finale["ranking"] = range(1, len(df_finale)+1)

# =========================
# TABELLA RISULTATI + COLORI
# =========================
st.subheader("🏆 Risultato gara")

def highlight(row):
    if row.ranking == 1:
        return ["background-color: #d4edda"] * len(row)
    elif row.ranking == len(df_finale):
        return ["background-color: #f8d7da"] * len(row)
    return [""] * len(row)

df_gara = df_finale[[
    "ranking", "label", "offerta", "penalita", "offerta_finale"
]].rename(columns={
    "label": "Impianto",
    "offerta": "Offerta",
    "penalita": "Penalità",
    "offerta_finale": "Finale"
})

st.dataframe(df_gara.style.apply(highlight, axis=1), use_container_width=True)

# =========================
# MAPPA
# =========================
st.subheader("📍 Mappa")

lat_circle, lon_circle = circle_coords(lat_centro, lon_centro, raggio_km)

fig = go.Figure()

fig.add_trace(go.Scattermapbox(
    lat=lat_circle,
    lon=lon_circle,
    mode='lines',
    fill='toself',
    fillcolor='rgba(0,200,0,0.1)',
    line=dict(color='green')
))

fig.add_trace(go.Scattermapbox(
    lat=[lat_centro],
    lon=[lon_centro],
    mode='markers',
    marker=dict(size=14, color='red'),
    name="Comune"
))

fig.add_trace(go.Scattermapbox(
    lat=df_finale["latitudine"],
    lon=df_finale["longitudine"],
    mode='markers+text',
    text=df_finale["label"],
    marker=dict(size=10, color='black')
))

fig.update_layout(
    mapbox_style="open-street-map",
    mapbox=dict(center=dict(lat=lat_centro, lon=lon_centro), zoom=6),
    height=900
)

st.plotly_chart(fig, use_container_width=True)
