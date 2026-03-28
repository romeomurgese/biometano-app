import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from math import radians, cos, sin, asin

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
# LOAD DATA
# =========================
@st.cache_data
def load_data():
    df = pd.read_excel("impianti_geocodificati.xlsx")
    df.columns = df.columns.str.lower()
    df["totale (t)"] = pd.to_numeric(df["totale (t)"], errors='coerce').fillna(1)
    df["latitudine"] = pd.to_numeric(df["latitudine"], errors='coerce')
    df["longitudine"] = pd.to_numeric(df["longitudine"], errors='coerce')
    df["flag"] = True
    df["offerta"] = 0.0
    df["label_impianto"] = df["comune"] + " (" + df["provincia"] + ")"
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
st.sidebar.header("⚙️ Parametri")

comune_sel = st.sidebar.selectbox("📍 Comune di gara", lista_comuni)
raggio_km = st.sidebar.slider("📏 Raggio (km)", 1, 200, 50)
tariffa_base = st.sidebar.number_input("💰 Tariffa base (€)", value=100.0)

penale_km = st.sidebar.number_input("⚖️ Penalità €/km", value=0.5)

tipologie = df["tipologia"].sort_values().unique()
tipologie_sel = st.sidebar.multiselect("🏭 Tipologie", tipologie, default=list(tipologie))

impianti_extra = st.sidebar.multiselect(
    "🔹 Impianti extra",
    options=df["label_impianto"].sort_values().unique()
)

# =========================
# CENTRO COMUNE
# =========================
match = df_comuni[df_comuni["nome"] == comune_sel]
if match.empty:
    st.error("Comune non trovato")
    st.stop()

lat_centro = match.iloc[0]["lat"]
lon_centro = match.iloc[0]["lng"]

# =========================
# DISTANZE
# =========================
df["distanza_km"] = df.apply(
    lambda r: haversine(lat_centro, lon_centro, r["latitudine"], r["longitudine"]), axis=1
).round(1)

df_filtrato = df[
    (df["distanza_km"] <= raggio_km) &
    (df["tipologia"].isin(tipologie_sel))
]

# Aggiunta extra
for imp in impianti_extra:
    extra = df[(df["label_impianto"] == imp) & (df["tipologia"].isin(tipologie_sel))]
    df_filtrato = pd.concat([df_filtrato, extra])

df_filtrato = df_filtrato.drop_duplicates()

# =========================
# TABELLA UNICA
# =========================
st.subheader("📊 Simulazione gara")

df_table = df_filtrato.copy()

df_table["km_fuori"] = (df_table["distanza_km"] - raggio_km).clip(lower=0)
df_table["penalita"] = df_table["km_fuori"] * penale_km
df_table["offerta_finale"] = df_table["offerta"] - df_table["penalita"]

df_table = df_table.rename(columns={
    "flag": "Seleziona",
    "comune": "Impianto",
    "tipologia": "Tipologia",
    "totale (t)": "Quantità",
    "distanza_km": "Distanza",
    "offerta": "Offerta"
})

df_table = df_table.sort_values("offerta_finale", ascending=False)
df_table["Ranking"] = range(1, len(df_table) + 1)

df_table = df_table[[
    "Seleziona", "Ranking", "Impianto", "Tipologia",
    "Quantità", "Distanza", "km_fuori",
    "Offerta", "penalita", "offerta_finale"
]]

edited = st.data_editor(
    df_table,
    use_container_width=True,
    height=400,
    column_config={
        "Seleziona": st.column_config.CheckboxColumn(),
        "Offerta": st.column_config.NumberColumn(min_value=0)
    },
    disabled=[
        "Ranking", "Impianto", "Tipologia",
        "Quantità", "Distanza", "km_fuori",
        "penalita", "offerta_finale"
    ]
)

# Aggiorna valori
df_filtrato["flag"] = edited["Seleziona"].values
df_filtrato["offerta"] = edited["Offerta"].values

df_finale = df_filtrato[df_filtrato["flag"] == True].copy()

# =========================
# VINCITORE
# =========================
if not df_table.empty:
    winner = df_table.iloc[0]
    st.success(
        f"🏆 Vincitore: {winner['Impianto']} | Offerta finale: {round(winner['offerta_finale'],2)} €"
    )

st.markdown("---")

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
    line=dict(color='green'),
    name=f"Raggio"
))

fig.add_trace(go.Scattermapbox(
    lat=[lat_centro],
    lon=[lon_centro],
    mode='markers+text',
    marker=dict(size=14, color='red'),
    text=[comune_sel],
    name="Comune"
))

if not df_finale.empty:
    fig.add_trace(go.Scattermapbox(
        lat=df_finale["latitudine"],
        lon=df_finale["longitudine"],
        mode='markers+text',
        marker=dict(size=10, color="black"),
        text=df_finale["comune"],
        name="Impianti"
    ))

fig.update_layout(
    mapbox_style="open-street-map",
    mapbox=dict(center=dict(lat=lat_centro, lon=lon_centro), zoom=6),
    height=900,
    legend=dict(title="Legenda")
)

st.plotly_chart(fig, use_container_width=True)
