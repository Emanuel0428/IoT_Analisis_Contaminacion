# Dashboard - Examen 3 IoT
# Solo lee lo que dejó etl.py en data/, no recalcula indicadores.
# Correr con: streamlit run app.py
import folium
import numpy as np
import pandas as pd
import streamlit as st
from matplotlib.colors import LinearSegmentedColormap, to_hex
from streamlit_folium import st_folium

UMBRAL = -60  # dBm: por encima el canal está ocupado/contaminado (criterio del examen)
SUAVIZADO = 350  # m: ancho del suavizado gaussiano (las medidas están cada ~390 m)
BORDE = 400  # m: se pinta hasta esta distancia de la ruta; más lejos no hay datos
OPACIDAD = 0.55  # máxima: el mapa de calor es sutil para que se sigan viendo las calles
# Azul (bajo) -> claro (centro de la escala) -> rojo (alto). En los canales el centro es el umbral de -60 dBm
COLORES = LinearSegmentedColormap.from_list("rampa", [
    (0, "#1c5cab"), (0.25, "#6da7ec"), (0.5, "#f7f1dc"), (0.7, "#f5a524"), (0.85, "#e34948"), (1, "#9c2412")])
BANDAS = {"A": "840-845 MHz", "B": "845-850 MHz", "C": "850-855 MHz", "D": "855-860 MHz"}

st.set_page_config(page_title="Espectro 840-860 MHz", layout="wide")
info = pd.read_csv("data/mediciones.csv")
frec = pd.read_csv("data/indicadores_frecuencia.csv")
resumen = pd.read_csv("data/indicadores_canal.csv")
f_mas = frec.loc[frec.pct_ocupado.idxmax()]
f_menos = frec.loc[frec.pct_ocupado.idxmin()]

# metros por grado alrededor de la ruta
M_LAT = 110.5e3
M_LON = 111.3e3 * np.cos(np.radians(info.lat.mean()))

# capa -> columna de mediciones.csv que se pinta en el mapa de calor
heatmaps = {
    "Mapa de calor: canal A": "p_A",
    "Mapa de calor: canal B": "p_B",
    "Mapa de calor: canal C": "p_C",
    "Mapa de calor: canal D": "p_D",
    "Mapa de calor: temperatura del sensor": "temp",
    f"Mapa de calor: frecuencia más contaminada ({f_mas.freq_mhz:.3f} MHz)": "p_frec_max",
}


@st.cache_data
def mapa_de_calor(columna, vmin, vmax):
    # Cada píxel es el promedio de las medidas pesado por un kernel gaussiano de la distancia.
    # Solo se pinta cerca de la ruta: más lejos no hay medidas.
    # (folium.plugins.HeatMap suma los puntos que se enciman: mostraría densidad, no el valor.)
    margen = BORDE / M_LAT
    lats = np.linspace(info.lat.max() + margen, info.lat.min() - margen, 400)  # fila 0 = norte
    lons = np.linspace(info.lon.min() - margen, info.lon.max() + margen, 260)
    glon, glat = np.meshgrid(lons, lats)
    d = np.hypot((glon[..., None] - info.lon.values) * M_LON, (glat[..., None] - info.lat.values) * M_LAT)
    w = np.exp(-0.5 * (d / SUAVIZADO) ** 2)
    z = (w * info[columna].values).sum(axis=-1) / (w.sum(axis=-1) + 1e-12)
    t = np.clip((z - vmin) / (vmax - vmin), 0, 1)
    imagen = COLORES(t)
    # Transparencia:
    # - lo cercano al centro de la escala (el umbral) casi no se pinta; lo claramente libre o
    #   contaminado sí. Así el color solo aparece donde hay algo que decir y se sigue viendo el mapa.
    # - la zona pintada sigue la ruta (densidad de medidas cercanas), con un borde corto y suave.
    intensidad = 0.4 + 0.6 * np.abs(2 * t - 1)
    densidad = np.exp(-0.5 * (d / (BORDE / 2)) ** 2).sum(axis=-1)
    imagen[..., 3] = OPACIDAD * intensidad * np.clip((densidad - 0.3) / 0.5, 0, 1)
    return imagen, [[lats[-1], lons[0]], [lats[0], lons[-1]]]


def leyenda(titulo, vmin, vmax, unidad, clases):
    # recuadro dentro del mapa (abajo a la izquierda): barra de colores + rangos con nombre
    barra = ",".join(to_hex(COLORES(x)) for x in np.linspace(0, 1, 9))
    filas = "".join(
        f"<div style='margin-top:4px'><span style='display:inline-block;width:12px;height:12px;border-radius:2px;"
        f"vertical-align:middle;margin-right:6px;background:{to_hex(COLORES(np.clip((v - vmin) / (vmax - vmin), 0, 1)))}'></span>"
        f"<b>{nombre}</b> {rango}</div>" for nombre, rango, v in clases)
    html = (f"<div style='position:fixed;bottom:24px;left:12px;z-index:9999;background:rgba(20,24,33,.88);color:#fff;"
            f"padding:10px 12px;border-radius:8px;font:12px sans-serif;width:230px'>"
            f"<div style='font-weight:bold;letter-spacing:.5px'>{titulo}</div>"
            f"<div style='height:10px;border-radius:3px;margin:8px 0 2px;background:linear-gradient(to right,{barra})'></div>"
            f"<div style='display:flex;justify-content:space-between;opacity:.8'>"
            f"<span>{vmin:.0f} {unidad}</span><span>{vmax:.0f} {unidad}</span></div>{filas}</div>")
    return folium.Element(html)


st.title("Ocupación del espectro 840-860 MHz, occidente de Medellín")

# ---------------- Decisión para la ANE
mas = resumen.loc[resumen.pct_ocupado.idxmax()]
menos = resumen.loc[resumen.pct_ocupado.idxmin()]
c1, c2, c3, c4 = st.columns(4)
c1.metric("Canal más contaminado", f"{mas.canal} ({BANDAS[mas.canal]})")
c1.caption(f"Ocupado en el {mas.pct_ocupado}% de la ruta · {mas.recomendacion}")
c2.metric("Canal menos contaminado", f"{menos.canal} ({BANDAS[menos.canal]})")
c2.caption(f"Ocupado en el {menos.pct_ocupado}% de la ruta · {menos.recomendacion}")
c3.metric("Frecuencia más contaminada", f"{f_mas.freq_mhz:.3f} MHz")
c3.caption(f"Canal {f_mas.canal} · supera −60 dBm en el {f_mas.pct_ocupado:.0f}% de la ruta")
c4.metric("Frecuencia menos contaminada", f"{f_menos.freq_mhz:.3f} MHz")
c4.caption(f"Canal {f_menos.canal} · supera −60 dBm en el {f_menos.pct_ocupado:.0f}% de la ruta")

st.subheader("Recomendación para la ANE")
tabla = pd.DataFrame({
    "Canal": resumen.canal,
    "Banda": resumen.canal.map(BANDAS),
    "Potencia media típica (dBm, Parseval)": resumen.potencia_tipica,
    "% de la ruta ocupado (> −60 dBm)": resumen.pct_ocupado,
    "Recomendación": resumen.recomendacion,
})
st.dataframe(tabla, hide_index=True)
st.caption("Criterio: < 25 % de la ruta ocupado → usar · 25-50 % → con cuidado · > 50 % → no usar.")

# ---------------- Mapa
capa = st.sidebar.radio("Capa del mapa", ["Ubicación de las mediciones", "Ruta de las mediciones", *heatmaps])
st.subheader(capa)
mapa = folium.Map(location=[info.lat.mean(), info.lon.mean()], zoom_start=13)  # OpenStreetMap

if capa == "Ubicación de las mediciones":
    for _, m in info.iterrows():
        popup = (f"<b>{m.archivo}</b><br>Temp: {m.temp:.1f} °C<br>"
                 f"A: {m.p_A:.1f} · B: {m.p_B:.1f} · C: {m.p_C:.1f} · D: {m.p_D:.1f} dBm<br>"
                 f"GPS imputado: {'sí' if m.gps_imputado else 'no'}")
        color = "red" if m.gps_imputado else "blue"
        folium.CircleMarker([m.lat, m.lon], radius=6, color=color, fill=True, popup=popup).add_to(mapa)
    st.caption("Clic en un punto para ver sus datos. En rojo: 008 y 017, posición GPS imputada.")

elif capa == "Ruta de las mediciones":
    folium.PolyLine(info[["lat", "lon"]].values, color="blue").add_to(mapa)
    inicio, fin = info.iloc[0], info.iloc[-1]
    folium.Marker([inicio.lat, inicio.lon], tooltip="Inicio (001)", icon=folium.Icon(color="green")).add_to(mapa)
    folium.Marker([fin.lat, fin.lon], tooltip=f"Fin ({fin.archivo[:3]})", icon=folium.Icon(color="black")).add_to(mapa)
    for _, m in info[info.gps_imputado].iterrows():
        folium.CircleMarker([m.lat, m.lon], radius=7, color="red", fill=True,
                            tooltip=f"{m.archivo}: GPS imputado").add_to(mapa)

else:
    columna = heatmaps[capa]
    if columna == "temp":
        unidad = "°C"
        vmin, vmax = np.percentile(info.temp, [5, 95])
        t1, t2 = np.percentile(info.temp, [33, 67])
        clases = [("Fresco", f"< {t1:.1f} °C", vmin), ("Templado", f"{t1:.1f} a {t2:.1f} °C", (t1 + t2) / 2),
                  ("Caliente", f"> {t2:.1f} °C", vmax)]
    else:
        # misma escala para todos los canales (se pueden comparar), centrada en el umbral
        unidad = "dBm"
        vmin, vmax = UMBRAL - 25, UMBRAL + 25
        clases = [("Libre", f"< {UMBRAL - 10} dBm", UMBRAL - 20), ("Cerca del umbral", f"{UMBRAL - 10} a {UMBRAL} dBm", UMBRAL - 5),
                  ("Contaminado", f"> {UMBRAL} dBm", UMBRAL + 20)]
    imagen, limites = mapa_de_calor(columna, vmin, vmax)
    folium.raster_layers.ImageOverlay(imagen, bounds=limites).add_to(mapa)
    for _, m in info.iterrows():  # medidas reales encima, con su valor exacto
        folium.CircleMarker([m.lat, m.lon], radius=2, color="#222222", weight=1, fill=True, fill_color="#222222",
                            fill_opacity=0.8, tooltip=f"{m.archivo}: {m[columna]:.1f} {unidad}").add_to(mapa)
    mapa.get_root().html.add_child(leyenda(capa.replace("Mapa de calor: ", "").upper(), vmin, vmax, unidad, clases))
    st.caption("Los puntos son las medidas reales (pasa el mouse para ver el valor). "
               "Entre ellas el color es una interpolación; lo cercano al centro de la escala casi no se pinta.")

st_folium(mapa, height=550, use_container_width=True, returned_objects=[])
