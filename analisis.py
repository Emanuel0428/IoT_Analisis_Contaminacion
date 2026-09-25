# Análisis - Examen 3 IoT
# Hace las gráficas del informe con lo que dejó etl.py en data/ y las guarda en figs/
# (el dashboard muestra estas mismas imágenes, por eso usan su tema oscuro)
import glob
import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

UMBRAL = -60
os.makedirs("figs", exist_ok=True)

# ---------------- Estilo (mismos colores que el dashboard, .streamlit/config.toml)
FONDO = "#111827"
TINTA = "#e5e7eb"  # texto principal
TINTA2 = "#9ca3af"  # texto secundario y ejes
REJILLA = "#1f2937"
LIMITE = "#e66767"  # umbral de -60 dBm y "más contaminada"
# un color fijo por canal (paleta validada para daltonismo sobre FONDO)
COLOR_CANAL = {"A": "#3987e5", "B": "#d95926", "C": "#199e70", "D": "#c98500"}
AZUL, NARANJA, VERDE = COLOR_CANAL["A"], COLOR_CANAL["B"], COLOR_CANAL["C"]
BANDAS = {"A": (840, 845), "B": (845, 850), "C": (850, 855), "D": (855, 860)}

plt.rcParams.update({
    "figure.facecolor": FONDO, "axes.facecolor": FONDO, "savefig.facecolor": FONDO,
    "font.family": "sans-serif", "font.sans-serif": ["Inter", "Segoe UI", "DejaVu Sans"], "font.size": 13,
    "text.color": TINTA, "axes.labelcolor": TINTA2, "xtick.color": TINTA2, "ytick.color": TINTA2,
    "axes.edgecolor": REJILLA, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": REJILLA, "grid.linewidth": 0.8,
    "axes.titlesize": 14, "axes.titleweight": "semibold", "axes.titlelocation": "left", "axes.titlepad": 10,
    "legend.frameon": False, "legend.labelcolor": TINTA,
    "lines.linewidth": 1.6, "savefig.dpi": 160, "savefig.bbox": "tight",
})


def umbral(ax, x=1):
    # línea del umbral con su etiqueta directa (x: dónde va la etiqueta, en fracción del eje)
    ax.axhline(UMBRAL, color=LIMITE, linewidth=1, linestyle=(0, (4, 3)))
    ax.annotate("umbral −60 dBm", (x, UMBRAL), xycoords=("axes fraction", "data"), xytext=(-4 if x == 1 else 4, 4),
                textcoords="offset points", ha="right" if x == 1 else "left", fontsize=11.5, color=TINTA)


def canales_de_fondo(ax, etiquetas=True):
    # sombrea los canales alternados y escribe su letra arriba
    for i, (canal, (ini, fin)) in enumerate(BANDAS.items()):
        if i % 2 == 0:
            ax.axvspan(ini, fin, color="white", alpha=0.035, linewidth=0)
        if etiquetas:
            ax.annotate(f"Canal {canal}", ((ini + fin) / 2, 1), xycoords=("data", "axes fraction"),
                        xytext=(0, 4), textcoords="offset points", ha="center", fontsize=11.5, color=TINTA2)


info = pd.read_csv("data/mediciones.csv")
espectro = pd.read_csv("data/espectro_limpio.csv")
frec = pd.read_csv("data/indicadores_frecuencia.csv")
resumen = pd.read_csv("data/indicadores_canal.csv")
mas = frec.pct_ocupado.idxmax()
menos = frec.pct_ocupado.idxmin()
validas = info[~info.saturada]

# ---------------- 1. Espectro de toda la ruta
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6.5), sharex=True, gridspec_kw={"hspace": 0.3})
canales_de_fondo(ax1)
ax1.plot(frec.freq_mhz, frec.mediana, color=AZUL)
umbral(ax1)
ax1.set_ylabel("Mediana de la ruta (dBm)")
ax1.set_title("Espectro típico de la ruta", pad=22)

canales_de_fondo(ax2, etiquetas=False)
ax2.plot(frec.freq_mhz, frec.pct_ocupado, color=TINTA2, linewidth=1.2)
for i, color, texto, dy in [(mas, LIMITE, "más contaminada", 14), (menos, VERDE, "menos contaminada", 40)]:
    ax2.plot(frec.freq_mhz[i], frec.pct_ocupado[i], "o", color=color, markersize=8,
             markeredgecolor=FONDO, markeredgewidth=2)
    ax2.annotate(f"{texto}\n{frec.freq_mhz[i]:.3f} MHz · {frec.pct_ocupado[i]:.0f} %",
                 (frec.freq_mhz[i], frec.pct_ocupado[i]), xytext=(10, dy), textcoords="offset points",
                 fontsize=11.5, color=TINTA, va="center")
ax2.set_ylabel("% de la ruta > −60 dBm")
ax2.set_xlabel("Frecuencia (MHz)")
ax2.set_title("Ocupación de cada frecuencia")
ax2.set_xlim(840, 860)
fig.savefig("figs/espectro.png")

# ---------------- 2. Frecuencia más y menos contaminada a lo largo de la ruta
fig, ax = plt.subplots(figsize=(10, 4.5))
umbral(ax, x=0)
for i, color, texto in [(mas, LIMITE, "más contaminada"), (menos, AZUL, "menos contaminada")]:
    y = espectro[str(i)]
    ax.plot(info.orden, y, "-o", color=color, markersize=3.5, label=f"{texto} ({frec.freq_mhz[i]:.3f} MHz)")
    ax.annotate(f"{frec.freq_mhz[i]:.3f} MHz", (info.orden.iloc[-1], y.iloc[-1]), xytext=(6, 0),
                textcoords="offset points", fontsize=11.5, color=TINTA, va="center")
for _, m in info[info.saturada].iterrows():  # la medida saturada se ve pero no cuenta
    ax.annotate(f"{m.archivo[:3]}: receptor saturado\n(no entra en los indicadores)", (m.orden, espectro[str(mas)][m.name]),
                xytext=(-150, 4), textcoords="offset points", fontsize=11, color=TINTA2, va="top",
                arrowprops={"arrowstyle": "-", "color": TINTA2, "linewidth": 0.8})
ax.set_xlabel("Medida (orden del recorrido)")
ax.set_ylabel("dBm")
ax.set_title("Frecuencias extremas a lo largo de la ruta")
ax.legend(loc="lower right", bbox_to_anchor=(1, 1), ncols=2)
fig.savefig("figs/frecuencias_extremas.png")

# ---------------- 3. Potencia de cada canal (una fila por canal: cada punto es una medida)
fig, ax = plt.subplots(figsize=(8, 5.5))
rng = np.random.default_rng(0)  # separación vertical fija de los puntos, para que no se tapen
for fila, canal in enumerate(["D", "C", "B", "A"]):
    p = validas["p_" + canal]
    ax.scatter(p, fila + rng.uniform(-0.18, 0.18, len(p)), s=22, color=COLOR_CANAL[canal],
               edgecolors=FONDO, linewidths=0.8, zorder=3)
    ax.plot([p.median()] * 2, [fila - 0.3, fila + 0.3], color=TINTA, linewidth=2, zorder=4)
    ax.annotate(f"mediana {p.median():.1f} dBm", (p.median(), fila + 0.3), xytext=(0, 3),
                textcoords="offset points", ha="center", fontsize=11, color=TINTA2)
ax.axvline(UMBRAL, color=LIMITE, linewidth=1, linestyle=(0, (4, 3)))
ax.annotate("umbral −60 dBm", (UMBRAL, 0), xycoords=("data", "axes fraction"), xytext=(4, 6),
            textcoords="offset points", fontsize=11.5, color=TINTA)
ax.set_yticks(range(4), [f"Canal {c}" for c in ["D", "C", "B", "A"]])
ax.tick_params(axis="y", length=0, labelcolor=TINTA)
ax.grid(axis="y", visible=False)
ax.set_xlabel("Potencia del canal en cada medida (dBm)")
ax.set_title("Potencia de cada canal en la ruta")
fig.savefig("figs/canales.png")

# ---------------- 4. Ruta
fig, ax = plt.subplots(figsize=(7, 8.5))
ax.plot(info.lon, info.lat, "-", color=TINTA2, linewidth=1.2, zorder=1)
ax.scatter(info.lon, info.lat, s=18, color=AZUL, edgecolors=FONDO, linewidths=0.8, zorder=2)
imputados = info[info.gps_imputado]
ax.scatter(imputados.lon, imputados.lat, s=70, facecolors="none", edgecolors=NARANJA, linewidths=1.6, zorder=3,
           label="posición GPS imputada")
saturadas = info[info.saturada]
ax.scatter(saturadas.lon, saturadas.lat, s=70, facecolors="none", edgecolors=LIMITE, linewidths=1.6, zorder=3,
           label="receptor saturado")
ax.plot(info.lon.iloc[0], info.lat.iloc[0], "^", color=VERDE, markersize=11, zorder=4, label="inicio (001)")
ax.plot(info.lon.iloc[-1], info.lat.iloc[-1], "s", color=TINTA, markersize=8, zorder=4, label=f"fin ({info.archivo.iloc[-1][:3]})")
for i in range(0, len(info), 10):
    ax.annotate(info.archivo[i][:3], (info.lon[i], info.lat[i]), xytext=(6, 4), textcoords="offset points",
                fontsize=11, color=TINTA2)
ax.set_aspect("equal")
ax.set_xlabel("Longitud")
ax.set_ylabel("Latitud")
ax.set_title("Recorrido de la estación móvil")
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.08), ncols=2, fontsize=11.5)
fig.savefig("figs/ruta.png")

# Largo de la ruta: 1 grado de latitud ~ 110.5 km; en longitud se multiplica por cos(latitud)
dx = np.diff(info.lon) * 111.3 * np.cos(np.radians(6.2))
dy = np.diff(info.lat) * 110.5
print(f"Largo de la ruta: {np.sqrt(dx**2 + dy**2).sum():.1f} km")

# ---------------- 5. ¿La temperatura afecta la medida?
# orden: la temperatura sube con el tiempo · piso de ruido (percentil 10 del espectro) · HDOP del GPS
fig, axs = plt.subplots(3, 1, figsize=(7, 10), gridspec_kw={"hspace": 0.6})
paneles = [("orden", "Medida (orden)"), ("piso", "Piso de ruido (dBm)"), ("error_gps", "HDOP del GPS")]
for ax, (columna, nombre) in zip(axs, paneles):
    r, p = stats.pearsonr(info.temp, info[columna])
    ax.scatter(info.temp, info[columna], s=20, color=AZUL, edgecolors=FONDO, linewidths=0.8)
    ax.set_xlabel("Temperatura del USRP (°C)")
    ax.set_ylabel(nombre)
    ax.set_title(f"{nombre}   r = {r:.2f} · p = {p:.3f}", fontsize=13)
    print(f"Temperatura vs {columna}: r = {r:.2f}, p = {p:.3f}")
fig.savefig("figs/temperatura.png")

# ---------------- 6. Pico DC antes y después de corregir
archivos = sorted(glob.glob("medidas_2026_20/[0-9][0-9][0-9].txt"))
crudo = np.array([np.loadtxt(a, delimiter=",")[:1024] for a in archivos])
zona = range(490, 535)
fig, ax = plt.subplots(figsize=(10, 4))
ax.axvspan(frec.freq_mhz[509], frec.freq_mhz[515], color="white", alpha=0.05, linewidth=0)
ax.annotate("bins corregidos\n(509 a 515)", (frec.freq_mhz[512], 0), xycoords=("data", "axes fraction"),
            xytext=(0, 6), textcoords="offset points", ha="center", va="bottom", fontsize=11.5, color=TINTA2)
ax.plot(frec.freq_mhz[zona], np.median(crudo[:, zona], axis=0), "-o", markersize=3.5, color=NARANJA, label="original")
ax.plot(frec.freq_mhz[zona], espectro.iloc[:, zona].median(), "-o", markersize=3.5, color=AZUL, label="corregido")
ax.set_xlabel("Frecuencia (MHz)")
ax.set_ylabel("Mediana de la ruta (dBm)")
ax.set_title("Pico DC del USRP en 850 MHz")
ax.legend(loc="upper left")
fig.savefig("figs/imputacion_dc.png")

# ---------------- 7. Antena (S11 medido con el analizador de redes)
antena = pd.read_csv("medidas_2026_20/ANTENNA1.csv", skiprows=17, skipfooter=1,
                     names=["freq", "s11"], engine="python")
antena["freq"] = antena.freq / 1e6
fig, ax = plt.subplots(figsize=(10, 4))
ax.axvspan(840, 860, color=LIMITE, alpha=0.15, linewidth=0)
ax.annotate("banda medida", (850, 1), xycoords=("data", "axes fraction"), xytext=(0, -6),
            textcoords="offset points", ha="center", va="top", fontsize=11.5, color=TINTA)
ax.plot(antena.freq, antena.s11, color=AZUL)
ax.axhline(-10, color=TINTA2, linewidth=1, linestyle=(0, (4, 3)))
ax.annotate("−10 dB: buena adaptación", (0.22, -10), xycoords=("axes fraction", "data"), xytext=(0, -12),
            textcoords="offset points", ha="left", fontsize=11.5, color=TINTA2)
ax.set_xlabel("Frecuencia (MHz)")
ax.set_ylabel("S11 (dB)")
ax.set_title("Adaptación de la antena")
fig.savefig("figs/antena.png")

banda = antena[(antena.freq >= 840) & (antena.freq <= 860)]
print(f"Antena: en la banda el S11 va de {banda.s11.min():.1f} a {banda.s11.max():.1f} dB (no llega a -10 dB)")

# ---------------- 8. Recomendación para la ANE
print("\nRecomendación:")
for _, fila in resumen.iterrows():
    print(f"Canal {fila.canal}: ocupado en el {fila.pct_ocupado}% de la ruta, "
          f"{fila.pct_bins}% de sus frecuencias > -60 dBm -> {fila.recomendacion}")
