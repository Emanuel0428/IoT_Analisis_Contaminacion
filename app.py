# Dashboard - Examen 3 IoT
# Solo lee lo que dejaron etl.py (data/) y analisis.py (figs/), no recalcula indicadores.
# El tema oscuro está en .streamlit/config.toml. Correr con: streamlit run app.py
import folium
import numpy as np
import pandas as pd
import streamlit as st
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm, to_hex
from scipy import stats
from streamlit_folium import st_folium

UMBRAL = -60  # dBm: por encima el canal está ocupado/contaminado (criterio del examen)
SUAVIZADO = 350  # m: ancho del suavizado gaussiano (las medidas están cada ~390 m)
BORDE = 400  # m: se pinta hasta esta distancia de la ruta; más lejos no hay datos
OPACIDAD = 0.85  # máxima: deja ver un poco las calles debajo
# Azul (bajo) -> claro (centro de la escala) -> rojo (alto). En los canales el centro es el umbral de -60 dBm
COLORES = LinearSegmentedColormap.from_list("rampa", [
    (0, "#1c5cab"), (0.25, "#6da7ec"), (0.5, "#f7f1dc"), (0.7, "#f5a524"), (0.85, "#e34948"), (1, "#9c2412")])
BANDAS = {"A": "840–845 MHz", "B": "845–850 MHz", "C": "850–855 MHz", "D": "855–860 MHz"}
# recomendación -> (color de estado, icono, texto corto). El color nunca va solo: siempre con icono y texto
ESTADO = {"se recomienda usar": ("#0ca30c", "✓", "Usar"),
          "usar con cuidado": ("#fab219", "!", "Con cuidado"),
          "no se recomienda": ("#d03b3b", "✕", "No usar")}

st.set_page_config(page_title="Espectro 840–860 MHz · Medellín", page_icon="📡", layout="wide")
info = pd.read_csv("data/mediciones.csv")
frec = pd.read_csv("data/indicadores_frecuencia.csv")
resumen = pd.read_csv("data/indicadores_canal.csv")
f_mas = frec.loc[frec.pct_ocupado.idxmax()]
f_menos = frec.loc[frec.pct_ocupado.idxmin()]

# metros por grado alrededor de la ruta
M_LAT = 110.5e3
M_LON = 111.3e3 * np.cos(np.radians(info.lat.mean()))
largo_km = np.hypot(np.diff(info.lon) * M_LON, np.diff(info.lat) * M_LAT).sum() / 1000

# capa del mapa -> columna de mediciones.csv que se pinta en el mapa de calor
heatmaps = {"Canal A": "p_A", "Canal B": "p_B", "Canal C": "p_C", "Canal D": "p_D",
            "Temperatura": "temp", f"{f_mas.freq_mhz:.3f} MHz": "p_frec_max"}


@st.cache_data
def mapa_de_calor(columna, vmin, vcentro, vmax):
    # Cada píxel es el promedio de las medidas pesado por un kernel gaussiano de la distancia.
    # Solo se pinta cerca de la ruta: más lejos no hay medidas.
    # (folium.plugins.HeatMap suma los puntos que se enciman: mostraría densidad, no el valor.)
    datos = info
    margen = BORDE / M_LAT
    lats = np.linspace(info.lat.max() + margen, info.lat.min() - margen, 400)  # fila 0 = norte
    lons = np.linspace(info.lon.min() - margen, info.lon.max() + margen, 260)
    glon, glat = np.meshgrid(lons, lats)
    d = np.hypot((glon[..., None] - datos.lon.values) * M_LON, (glat[..., None] - datos.lat.values) * M_LAT)
    w = np.exp(-0.5 * (d / SUAVIZADO) ** 2)
    z = (w * datos[columna].values).sum(axis=-1) / (w.sum(axis=-1) + 1e-12)
    # escala de dos tramos: vmin..vcentro ocupa la mitad azul y vcentro..vmax la mitad cálida
    t = np.clip(TwoSlopeNorm(vcentro, vmin, vmax)(z), 0, 1)
    imagen = COLORES(t)
    # Transparencia:
    # - lo cercano al centro de la escala (el umbral) casi no se pinta; lo claramente libre o
    #   contaminado sí. Así el color solo aparece donde hay algo que decir y se sigue viendo el mapa.
    # - la zona pintada sigue la ruta (densidad de medidas cercanas), con un borde corto y suave.
    intensidad = 0.4 + 0.6 * np.abs(2 * t - 1)
    densidad = np.exp(-0.5 * (d / (BORDE / 2)) ** 2).sum(axis=-1)
    imagen[..., 3] = OPACIDAD * intensidad * np.clip((densidad - 0.3) / 0.5, 0, 1)
    # Se entrega en uint8: si recibe decimales, folium estira cada canal de color hasta su propio máximo
    # y los colores se deforman (un canal casi todo rojo salía magenta).
    return (imagen * 255).round().astype(np.uint8), [[lats[-1], lons[0]], [lats[0], lons[-1]]]


def leyenda(titulo, vmin, vcentro, vmax, unidad, clases):
    # recuadro dentro del mapa (abajo a la izquierda): barra de colores + rangos con nombre
    escala = TwoSlopeNorm(vcentro, vmin, vmax)
    barra = ",".join(to_hex(COLORES(x)) for x in np.linspace(0, 1, 9))
    filas = "".join(
        f"<div style='margin-top:4px'><span style='display:inline-block;width:12px;height:12px;border-radius:2px;"
        f"vertical-align:middle;margin-right:6px;background:{to_hex(COLORES(np.clip(escala(v), 0, 1)))}'></span>"
        f"<b>{nombre}</b> {rango}</div>" for nombre, rango, v in clases)
    html = (f"<div style='position:fixed;bottom:24px;left:12px;z-index:9999;background:rgba(17,24,39,.92);color:#e5e7eb;"
            f"padding:10px 12px;border-radius:8px;border:1px solid #1f2937;font:12px sans-serif;width:230px'>"
            f"<div style='font-weight:bold;letter-spacing:.5px'>{titulo}</div>"
            f"<div style='height:10px;border-radius:3px;margin:8px 0 2px;background:linear-gradient(to right,{barra})'></div>"
            f"<div style='display:flex;justify-content:space-between;opacity:.8'>"
            f"<span>{vmin:.0f}</span><span>{vcentro:.0f}</span><span>{vmax:.0f} {unidad}</span></div>{filas}</div>")
    return folium.Element(html)


# ---------------- Piezas de interfaz (HTML + CSS propio)
st.html("""<style>
:root { --card:#111827; --line:#1f2937; --ink:#e5e7eb; --ink2:#9ca3af; --accent:#22d3ee;
        --mono:'JetBrains Mono', ui-monospace, monospace; }
.block-container { padding-top: 3.2rem; max-width: 1400px; }
header[data-testid='stHeader'] { background: transparent; }
.hero { border-top: 2px solid var(--accent); padding: 18px 0 6px; margin-bottom: 8px; }
.overline { font: 600 .72rem var(--mono); letter-spacing: .14em; text-transform: uppercase; color: var(--accent); }
.hero h1 { font-size: clamp(1.6rem, 3.2vw, 2.4rem); line-height: 1.15; margin: 6px 0 8px; padding: 0; }
.hero p { color: var(--ink2); margin: 0; }
.kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 12px; margin: 14px 0 8px; }
.kpi { background: var(--card); border: 1px solid var(--line); border-radius: 10px; padding: 14px 16px; }
.kpi .lbl { font-size: .78rem; color: var(--ink2); }
.kpi .val { font: 600 1.55rem var(--mono); color: var(--ink); margin: 4px 0 2px; white-space: nowrap; }
.kpi .sub { font-size: .8rem; color: var(--ink2); }
.panel { background: var(--card); border: 1px solid var(--line); border-radius: 10px; padding: 16px 18px; }
.panel h3 { font-size: 1rem; margin: 0 0 4px; padding: 0; }
.panel .nota { font-size: .8rem; color: var(--ink2); margin: 0; }
.rec { border-top: 1px solid var(--line); padding: 12px 0 10px; }
.rec .fila { display: flex; justify-content: space-between; align-items: center; gap: 8px; }
.rec .canal { font-weight: 600; }
.rec .canal span { font: .78rem var(--mono); color: var(--ink2); font-weight: 400; margin-left: 6px; }
.chip { display: inline-flex; align-items: center; gap: 6px; font-size: .78rem; font-weight: 600; color: var(--ink);
        padding: 3px 10px; border-radius: 999px; border: 1px solid; white-space: nowrap; }
.chip b { font-size: .8rem; }
.barra { height: 6px; background: var(--line); border-radius: 3px; margin: 8px 0 4px; overflow: hidden; }
.barra div { height: 100%; border-radius: 3px; }
.rec .dato { font-size: .8rem; color: var(--ink2); font-variant-numeric: tabular-nums; }
.ficha h3 { font-size: 1.05rem; margin: 0 0 6px; padding: 0; }
.ficha p { color: var(--ink2); font-size: .9rem; }
.marca { display: inline-block; width: 11px; height: 11px; border-radius: 50%; margin-right: 8px; vertical-align: middle; }
</style>""")


def kpis(tarjetas):
    # fila de tarjetas: (etiqueta, valor, detalle). Se acomodan solas al ancho de la pantalla
    html = "".join(f"<div class='kpi'><div class='lbl'>{a}</div><div class='val'>{b}</div><div class='sub'>{c}</div></div>"
                   for a, b, c in tarjetas)
    st.html(f"<div class='kpis'>{html}</div>")


def chip(recomendacion):
    color, icono, texto = ESTADO[recomendacion]
    return f"<span class='chip' style='border-color:{color};background:{color}26'><b style='color:{color}'>{icono}</b>{texto}</span>"


def recomendacion_html():
    # un renglón por canal, del más libre al más contaminado
    filas = ""
    for _, c in resumen.sort_values("pct_bins").iterrows():
        color = ESTADO[c.recomendacion][0]
        filas += (f"<div class='rec'><div class='fila'><div class='canal'>Canal {c.canal}<span>{BANDAS[c.canal]}</span></div>"
                  f"{chip(c.recomendacion)}</div>"
                  f"<div class='barra'><div style='width:{c.pct_bins}%;background:{color}'></div></div>"
                  f"<div class='dato'>{c.pct_bins:.1f} % de sus frecuencias &gt; −60 dBm · típica {c.potencia_tipica:.1f} dBm</div></div>")
    return (f"<div class='panel'><h3>Recomendación para la ANE</h3>"
            f"<p class='nota'>Los 4 canales superan −60 dBm (suma de Parseval) en el "
            f"{resumen.pct_ocupado.min():.0f}–{resumen.pct_ocupado.max():.0f} % de la ruta: todos están contaminados. "
            f"Se ordenan por la parte del canal que está ocupada.</p>{filas}"
            f"<p class='nota' style='margin-top:6px'>Criterio: &lt; 25 % → usar · 25–50 % → con cuidado · &gt; 50 % → no usar.</p></div>")


def ficha(titulo, texto, imagen=None):
    st.html(f"<div class='ficha'><h3>{titulo}</h3><p>{texto}</p></div>")
    if imagen:
        st.image(imagen, width="stretch")


# ---------------- Encabezado
st.html(f"""<div class='hero'><div class='overline'>Estudio técnico para la ANE · ocupación del espectro</div>
<h1>Banda 840–860 MHz · occidente de Medellín</h1>
<p>{len(info)} medidas con estación móvil · {largo_km:.1f} km de recorrido ·
umbral de contaminación −60 dBm</p></div>""")

seccion = st.segmented_control("Sección", ["Resumen", "Mapas", "Calidad de datos", "Metodología"],
                               default="Resumen", key="seccion", label_visibility="collapsed") or "Resumen"

# ---------------- Resumen
if seccion == "Resumen":
    mas = resumen.loc[resumen.pct_bins.idxmax()]
    menos = resumen.loc[resumen.pct_bins.idxmin()]
    kpis([("Canal más contaminado", f"Canal {mas.canal}", f"{BANDAS[mas.canal]} · {mas.pct_bins:.1f} % ocupado"),
          ("Canal menos contaminado", f"Canal {menos.canal}", f"{BANDAS[menos.canal]} · {menos.pct_bins:.1f} % ocupado"),
          ("Frecuencia más contaminada", f"{f_mas.freq_mhz:.3f} MHz",
           f"Canal {f_mas.canal} · > −60 dBm en el {f_mas.pct_ocupado:.0f} % de la ruta"),
          ("Frecuencia menos contaminada", f"{f_menos.freq_mhz:.3f} MHz",
           f"Canal {f_menos.canal} · > −60 dBm en el {f_menos.pct_ocupado:.0f} % de la ruta")])
    izq, der = st.columns([3, 2], gap="medium")
    with izq:
        st.image("figs/espectro.png", width="stretch")
        st.caption("Arriba: nivel típico de cada frecuencia en la ruta. Abajo: en qué parte de la ruta cada frecuencia "
                   "supera −60 dBm. El canal C concentra la ocupación; A y D son los más libres.")
    with der:
        st.html(recomendacion_html())

# ---------------- Mapas
elif seccion == "Mapas":
    capa = st.segmented_control("Capa", ["Ubicación", "Ruta", *heatmaps], default="Canal C", key="capa",
                                label_visibility="collapsed") or "Canal C"
    col_mapa, col_ficha = st.columns([3, 2], gap="medium")
    mapa = folium.Map(location=[info.lat.mean(), info.lon.mean()], zoom_start=13)  # OpenStreetMap

    if capa == "Ubicación":
        for _, m in info.iterrows():
            popup = (f"<b>{m.archivo}</b><br>Temp: {m.temp:.1f} °C<br>"
                     f"A: {m.p_A:.1f} · B: {m.p_B:.1f} · C: {m.p_C:.1f} · D: {m.p_D:.1f} dBm<br>"
                     f"GPS imputado: {'sí' if m.gps_imputado else 'no'}<br>"
                     f"Junto a una antena: {'sí' if m.antena else 'no'}")
            color = "#d95926" if m.gps_imputado else "#e66767" if m.antena else "#3987e5"
            folium.CircleMarker([m.lat, m.lon], radius=6, color=color, fill=True, fill_opacity=0.9,
                                popup=popup).add_to(mapa)
        with col_ficha:
            ficha("Ubicación de las mediciones",
                  f"{len(info)} puntos, uno cada ~390 m. Haz clic en uno para ver su temperatura y la potencia de cada canal.")
            st.html("<div class='panel'>"
                    "<p><span class='marca' style='background:#3987e5'></span>Medida normal</p>"
                    f"<p><span class='marca' style='background:#d95926'></span>Posición GPS imputada ({int(info.gps_imputado.sum())})</p>"
                    f"<p style='margin:0'><span class='marca' style='background:#e66767'></span>Junto a una antena ({int(info.antena.sum())})</p></div>")

    elif capa == "Ruta":
        folium.PolyLine(info[["lat", "lon"]].values, color="#22d3ee", weight=4).add_to(mapa)
        inicio, fin = info.iloc[0], info.iloc[-1]
        folium.Marker([inicio.lat, inicio.lon], tooltip="Inicio (001)", icon=folium.Icon(color="green")).add_to(mapa)
        folium.Marker([fin.lat, fin.lon], tooltip=f"Fin ({fin.archivo[:3]})", icon=folium.Icon(color="black")).add_to(mapa)
        for _, m in info[info.gps_imputado].iterrows():
            folium.CircleMarker([m.lat, m.lon], radius=7, color="#d95926", fill=True,
                                tooltip=f"{m.archivo}: GPS imputado").add_to(mapa)
        sur = info.loc[info.lat.idxmin()]
        with col_ficha:
            ficha("Ruta de la estación móvil",
                  f"Lazo de {largo_km:.1f} km: sale por el norte (001), baja hasta el punto más al sur ({sur.archivo[:3]}) "
                  f"y regresa por el oriente hasta {fin.archivo[:3]}. En naranja, las posiciones GPS imputadas.",
                  "figs/ruta.png")

    else:
        columna = heatmaps[capa]
        if columna == "temp":
            unidad = "°C"
            vmin, vmax = np.percentile(info.temp, [5, 95])
            vcentro = (vmin + vmax) / 2
            t1, t2 = np.percentile(info.temp, [33, 67])
            clases = [("Fresco", f"< {t1:.1f} °C", vmin), ("Templado", f"{t1:.1f} a {t2:.1f} °C", (t1 + t2) / 2),
                      ("Caliente", f"> {t2:.1f} °C", vmax)]
        else:
            # misma escala para todos los canales (se pueden comparar), centrada en el umbral
            unidad = "dBm"
            # Misma escala para todos los canales (se pueden comparar) con el umbral en el centro.
            # Con la suma de Parseval casi todo supera -60 dBm, así que el tramo cálido llega hasta -10 dBm
            # (percentil 95 de los 4 canales): así se ven diferencias dentro de lo contaminado.
            vmin, vcentro, vmax = UMBRAL - 15, UMBRAL, -10
            clases = [("Libre", f"< {UMBRAL} dBm", UMBRAL - 10), ("Contaminado", f"{UMBRAL} a -35 dBm", -47),
                      ("Muy contaminado", "> -35 dBm", -20)]
        imagen, limites = mapa_de_calor(columna, vmin, vcentro, vmax)
        folium.raster_layers.ImageOverlay(imagen, bounds=limites).add_to(mapa)
        for _, m in info.iterrows():  # medidas reales encima, con su valor exacto
            folium.CircleMarker([m.lat, m.lon], radius=2, color="#222222", weight=1, fill=True, fill_color="#222222",
                                fill_opacity=0.8, tooltip=f"{m.archivo}: {m[columna]:.1f} {unidad}").add_to(mapa)
        mapa.get_root().html.add_child(leyenda(capa.upper(), vmin, vcentro, vmax, unidad, clases))

        with col_ficha:
            if columna.startswith("p_") and columna != "p_frec_max":
                c = resumen.set_index("canal").loc[capa[-1]]
                ficha(f"{capa} · {BANDAS[capa[-1]]}",
                      f"Potencia del canal (suma de Parseval) en cada punto. Típica: {c.potencia_tipica:.1f} dBm; "
                      f"supera −60 dBm en el {c.pct_ocupado:.0f} % de la ruta y el {c.pct_bins:.1f} % de sus "
                      f"frecuencias está ocupado.")
                st.html(chip(c.recomendacion))
                st.image("figs/canales.png", width="stretch")
            elif columna == "temp":
                r, p = stats.pearsonr(info.temp, info.piso)
                ficha("Temperatura del sensor",
                      f"Es la temperatura interna del USRP: sube de {info.temp.min():.1f} a {info.temp.max():.1f} °C "
                      f"mientras el equipo se calienta. Con el piso de ruido, r = {r:.2f} (p = {p:.2f}): "
                      f"no tiene una incidencia significativa en la calidad de las medidas.",
                      "figs/temperatura.png")
            else:
                ficha(f"Frecuencia más contaminada · {f_mas.freq_mhz:.3f} MHz",
                      f"Canal {f_mas.canal}. Supera −60 dBm en el {f_mas.pct_ocupado:.0f} % de la ruta. La menos "
                      f"contaminada es {f_menos.freq_mhz:.3f} MHz ({f_menos.pct_ocupado:.0f} %).",
                      "figs/frecuencias_extremas.png")

    with col_mapa:
        st_folium(mapa, height=600, use_container_width=True, returned_objects=[])
        if capa not in ("Ubicación", "Ruta"):
            st.caption("Puntos: medidas reales (pasa el mouse para ver el valor). Entre ellas el color se interpola; "
                       "lo cercano al centro de la escala casi no se pinta."
                       + ("" if capa == "Temperatura" else " El valor más alto, en 016, es porque ahí hay una antena."))

# ---------------- Calidad de datos
elif seccion == "Calidad de datos":
    celdas_dc = 7 * len(info)  # bins 509 a 515 en cada medida (ver etl.py)
    kpis([("Medidas de la ruta", f"{len(info)}", "001 a 061 · 1029 columnas, sin vacíos"),
          ("Archivos descartados", "2", "pruebas del equipo, no son de la ruta"),
          ("Posiciones GPS imputadas", f"{int(info.gps_imputado.sum())}", "interpolación entre vecinas"),
          ("Junto a una antena", f"{int(info.antena.sum())}", "se conservan en los indicadores"),
          ("Celdas del pico DC", f"{celdas_dc}", f"{celdas_dc / (len(info) * 1024) * 100:.2f} % del espectro")])

    motivos = []
    for _, m in info.iterrows():
        if m.gps_imputado:
            problema = "GPS sin posición (lat/lon = 0)" if m.error_gps < 5 else f"GPS impreciso (HDOP {m.error_gps:.1f})"
            motivos.append([m.archivo, problema, "posición interpolada entre la medida anterior y la siguiente"])
        if m.antena:
            motivos.append([m.archivo, f"valor muy alto (pico {m.pico:.1f} dB, piso {m.piso:.1f} dB): hay una antena",
                            "se conserva, entra en los indicadores"])
    motivos += [["medidaprueba.txt", "prueba estática, GPS = 0", "descartado"],
                ["medidapureba2.txt", "prueba del equipo fuera de la ruta", "descartado"]]
    st.subheader("Medidas con correcciones")
    st.dataframe(pd.DataFrame(motivos, columns=["Archivo", "Problema", "Acción"]), hide_index=True, width="stretch")

    a, b = st.columns(2, gap="medium")
    with a:
        ficha("Pico DC del USRP",
              "El receptor genera un pico falso en su frecuencia central (850 MHz). Se reemplazaron los bins 509 a 515 "
              "por una interpolación lineal entre sus vecinos (error de validación ≈ 1.9 dB).",
              "figs/imputacion_dc.png")
    with b:
        ficha("Antena",
              "El S11 en la banda va de −8.6 a −5.8 dB: la antena no llega a −10 dB, así que pierde entre "
              "0.6 y 1.3 dB de señal. Afecta a todos los canales por igual; no cambia el orden entre ellos.",
              "figs/antena.png")
    r, p = stats.pearsonr(info.temp, info.piso)
    texto, figura = st.columns([3, 2], gap="medium")
    with texto:
        ficha("¿La temperatura afecta la calidad?",
              f"Es la temperatura interna del USRP y sube con el recorrido "
              f"(r = {stats.pearsonr(info.temp, info.orden)[0]:.2f} con el orden de las medidas) porque el equipo "
              f"se va calentando. Con el piso de ruido r = {r:.2f} (p = {p:.2f}) y con el HDOP del GPS "
              f"r = {stats.pearsonr(info.temp, info.error_gps)[0]:.2f}: no hay una incidencia significativa. "
              f"Como temperatura y tiempo van juntos, una relación débil tampoco se podría separar del cambio de lugar.")
    with figura:
        st.image("figs/temperatura.png", width="stretch")

# ---------------- Metodología
else:
    a, b = st.columns(2, gap="large")
    with a:
        st.subheader("Potencia del canal")
        st.write("Cada canal ocupa 5 MHz = 256 bins. Su potencia es la sumatoria de Parseval de los bins, "
                 "sumando en mW (en dB no se puede sumar):")
        st.latex(r"P_{canal} = 10\,\log_{10}\left(\sum_{k=1}^{256} 10^{P_k/10}\right)\ \text{dBm}")
        st.write("El equipo guarda |FFT/N|, así que esa suma es la potencia media de la señal en el canal.")
        st.subheader("Criterios")
        st.write(f"- **Canal contaminado:** potencia del canal > {UMBRAL} dBm (criterio del examen).\n"
                 f"- **Frecuencia ocupada:** bin > {UMBRAL} dBm. La más y la menos contaminada son las que superan "
                 "el umbral en más y en menos puntos de la ruta.\n"
                 "- **Recomendación:** como los 4 canales superan el umbral, se comparan por el % de sus frecuencias "
                 "ocupadas: < 25 % usar · 25–50 % con cuidado · > 50 % no usar.")
    with b:
        st.subheader("Limpieza e imputación")
        st.write("- Se descartan los 2 archivos de prueba.\n"
                 "- **GPS:** 008 (sin posición) y 017 (HDOP 17.3) se interpolan entre sus vecinas.\n"
                 "- **Pico DC:** bins 509–515 interpolados en frecuencia.\n"
                 "- **016:** pico a −3.6 dB del máximo del conversor y piso de ruido 35 dB por encima de lo normal. "
                 "Ahí hay una antena: la medida es real y se conserva en los indicadores.")
        st.subheader("Limitaciones")
        st.write("- Una sola pasada: 61 puntos, sin hora, así que no se ve la variación en el día.\n"
                 "- Los niveles son relativos al conversor (dBFS), sin calibración absoluta.\n"
                 "- Cada espectro es un *max-hold* (el máximo de varias capturas), así que sobreestima la potencia media.\n"
                 "- La antena está desadaptada en la banda (pérdida de 0.6 a 1.3 dB).")
