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

# Punti impianti filtrati
df_finale = df_filtrato[df_filtrato["flag"] == True].copy()
if not df_finale.empty:
    hover_cols = [c for c in ["tipologia","totale (t)","distanza_km"] if c in df_finale.columns]
    
    if use_color_map:
        fig_imp = px.scatter_mapbox(
            df_finale,
            lat="latitudine",
            lon="longitudine",
            size="totale (t)",
            color="totale (t)",
            hover_name="comune",
            hover_data=hover_cols,
            size_max=40,
            color_continuous_scale="YlOrRd"
        )
    else:
        fig_imp = px.scatter_mapbox(
            df_finale,
            lat="latitudine",
            lon="longitudine",
            hover_name="comune",
            hover_data=hover_cols
        )
        fig_imp.update_traces(marker=dict(size=10, color="black"))
    
    for trace in fig_imp.data:
        fig.add_trace(trace)

fig.update_layout(
    mapbox_style="open-street-map",
    mapbox=dict(center=dict(lat=lat_centro, lon=lon_centro), zoom=6),
    legend=dict(title="Legenda", yanchor="top", y=0.99, xanchor="left", x=0.01,
                bgcolor="rgba(50,50,50,0.7)", font=dict(color="white"))
)

# ✅ Imposta mappa più alta
st.plotly_chart(fig, use_container_width=True, height=800)
