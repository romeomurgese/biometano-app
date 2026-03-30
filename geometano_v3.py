import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from math import radians, cos, sin, asin
import time
import unicodedata

st.set_page_config(layout="wide")
st.title("🌱 Bioenerys Srl - Simulatore gara")

# =========================
# SESSION STATE
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
    lat_circle, lon_circle = [], []
    for theta in np.linspace(0, 2*np.pi, n_points):
        dlat = (r_km/6371) * (180/np.pi) * np.sin(theta)
        dlon = (r_km/6371) * (180/np.pi) * np.cos(theta) / cos(radians(lat))
        lat_circle.append(lat + dlat)
        lon_circle.append(lon + dlon)
    return lat_circle, lon_circle

# Normalizza nomi colonna per evitare problemi con accenti/spazi
def normalize_cols(df):
    df.columns = (
        df.columns
        .str.lower()
        .str.replace(" ", "_")
        .map(lambda x: unicodedata.normalize('NFKD', str(x)).encode('ascii', errors='ignore').decode('utf-8'))
    )
    return df

# =========================
# LOAD DATI
# =========================
@st.cache_data
def load_data():
    df = pd.read_excel("impianti_geocodificati.xlsx")
    df = normalize_cols(df)
    df["totale_(t)"] = pd.to_numeric(df["totale_(t)"], errors='coerce').fillna(1)
    df["latitudine"] = pd.to_numeric(df["latitudine"], errors='coerce')
    df["longitudine"] = pd.to_numeric(df["longitudine"], errors='coerce')
    df["flag"] = True
    return df

# 🔄 Bottone refresh manuale
if st.button("🔄 Aggiorna database impianti"):
    st.cache_data.clear()

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

comune_sel = st.sidebar.selectbox("📍 Comune", lista_comuni)
raggio_km = st.sidebar.slider("📏 Raggio (km)", 1, 200, 50)
tariffa_base = st.sidebar.number_input("💰 Tariffa base (€)", value=100.0)
penale_km = st.sidebar.number_input("⚖️ Penalità €/km", value=0.5)

tipologie = df["tipologia"].dropna().unique()
tipologie_sel = st.sidebar.multiselect("🏭 Tipologie", tipologie, default=list(tipologie))

# Label impianti
df["label"] = (
    df["comune"] + " (" + df["provincia"].fillna("") + ")"
    + " - " + df["societa"].fillna("N/D")
)

extra_sel = st.sidebar.multiselect(
    "➕ Impianti extra",
    df["label"].unique()
)

# =========================
# CENTRO
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
# FILTRO
# =========================
df_filtrato = df[
    (df["tipologia"].isin(tipologie_sel)) &
    (df["distanza_km"] <= raggio_km)
]

if extra_sel:
    df_extra = df[df["label"].isin(extra_sel)]
    df_filtrato = pd.concat([df_filtrato, df_extra])

df_filtrato = df_filtrato.drop_duplicates()

# =========================
# OFFERTA SMART
# =========================
offerte = []
for _, r in df_filtrato.iterrows():
    key = r["label"]
    offerte.append(st.session_state.offerte_custom.get(key, tariffa_base))

df_filtrato["offerta"] = offerte

# =========================
# PULSANTE SIMULA IN ALTO
# =========================
simula = st.button("🚀 Simula gara")

# =========================
# FORMATTING
# =========================

df_filtrato["quantita_fmt"] = df_filtrato["totale_(t)"].apply(lambda x: f"{int(x):,}".replace(",", "."))

# =========================
# TABELLA INPUT
# =========================
st.subheader("📋 Impianti partecipanti")

df_table = df_filtrato[[
    "flag", "label", "tipologia", "quantita_fmt", "distanza_km","offerta"
]].rename(columns={
    "flag":"Seleziona",
    "label":"Impianto",
    "tipologia":"Tipologia",
    "quantita_fmt":"Quantità",
    "distanza_km":"Distanza",
    "offerta":"Offerta (€)"
})

row_height = 35
dynamic_height = min(600, 40 + len(df_table)*row_height)

edited = st.data_editor(
    df_table,
    use_container_width=True,
    height=dynamic_height,
    hide_index=True,
    column_config={
        "Seleziona": st.column_config.CheckboxColumn(),
        "Offerta (€)": st.column_config.NumberColumn(min_value=0),
        "Società": st.column_config.TextColumn(width="medium")
    },
    disabled=["Impianto","Tipologia","Quantità","Distanza"]
)

# salva stato
for _, r in edited.iterrows():
    st.session_state.offerte_custom[r["Impianto"]] = r["Offerta (€)"]

df_filtrato["flag"] = edited["Seleziona"].values
df_filtrato["offerta"] = edited["Offerta (€)"].values

# =========================
# MAPPA (sempre visibile)
# =========================
st.subheader("📍 Mappa")

lat_circle, lon_circle = circle_coords(lat_centro, lon_centro, raggio_km)

fig = go.Figure()

# Cerchio raggio
fig.add_trace(go.Scattermapbox(
    lat=lat_circle,
    lon=lon_circle,
    mode='lines',
    fill='toself',
    fillcolor='rgba(0,200,0,0.1)',
    line=dict(color='green'),
    name=f"Raggio {raggio_km} km"
))

# Comune centrale
fig.add_trace(go.Scattermapbox(
    lat=[lat_centro],
    lon=[lon_centro],
    mode='markers',
    marker=dict(size=14, color='red'),
    name="Comune"
))

# Impianti filtrati
fig.add_trace(go.Scattermapbox(
    lat=df_filtrato["latitudine"],
    lon=df_filtrato["longitudine"],
    mode='markers+text',
    text=df_filtrato["label"],
    marker=dict(size=10, color='black'),
    name="Impianti"
))

fig.update_layout(
    mapbox_style="open-street-map",
    mapbox=dict(center=dict(lat=lat_centro, lon=lon_centro), zoom=6),
    height=800
)

st.plotly_chart(fig, use_container_width=True)

# =========================
# COLORI TESTO
# =========================
def highlight_text(row):
    if row.ranking == 1:
        return ["color: green; font-weight: bold"] * len(row)
    elif row.ranking == len(df_finale):
        return ["color: red"] * len(row)
    return [""] * len(row)

# =========================
# SIMULAZIONE
# =========================
if simula:

    with st.spinner("⏳ Calcolo in corso..."):
        time.sleep(0.5)

        df_finale = df_filtrato[df_filtrato["flag"]].copy()

        df_finale["km_fuori"] = (df_finale["distanza_km"] - raggio_km).clip(lower=0)
        df_finale["penalita"] = df_finale["km_fuori"] * penale_km
        df_finale["offerta_finale"] = df_finale["offerta"] - df_finale["penalita"]

        df_finale = df_finale.sort_values("offerta_finale", ascending=False)
        df_finale["ranking"] = range(1, len(df_finale)+1)

    # =========================
    # KPI
    # =========================
    best = df_finale.iloc[0]
    worst = df_finale.iloc[-1]

    col1, col2, col3 = st.columns(3)
    col1.metric("🥇 Migliore offerta", f"{best['offerta_finale']:.1f} €")
    col2.metric("📉 Peggiore offerta", f"{worst['offerta_finale']:.1f} €")
    col3.metric("Δ Spread", f"{best['offerta_finale'] - worst['offerta_finale']:.1f} €")

    # =========================
    # TABELLA RISULTATI
    # =========================
    st.subheader("🏆 Risultato gara")

    df_gara = df_finale[[
        "ranking","label","offerta","penalita","offerta_finale"
    ]].rename(columns={
        "label":"Impianto",
        "offerta":"Offerta (€)",
        "penalita":"Penalità (€)",
        "offerta_finale":"Offerta finale (€)"
    })

    st.dataframe(
        df_gara.style.apply(highlight_text, axis=1),
        use_container_width=True
    )

    ddf_gara = df_finale[[
        "ranking","label","offerta","penalita","offerta_finale"
    ]].rename(columns={
        "ranking":"Posizione",
        "label":"Impianto",
        "offerta":"Offerta (€)",
        "penalita":"Penalità (€)",
        "offerta_finale":"Offerta finale (€)"
    })

    st.dataframe(
        df_gara.style.apply(highlight_text, axis=1),
        use_container_width=True,
        hide_index=True
    )

    # =========================
    # GRAFICO
    # =========================
    fig_bar = px.bar(
        df_finale,
        x="label",
        y="offerta_finale",
        title="📊 Ranking offerte",
    )
    st.plotly_chart(fig_bar, use_container_width=True)
