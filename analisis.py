# Análisis - Examen 3 IoT
# Hace las gráficas del informe con lo que dejó etl.py en data/ y las guarda en figs/
import glob
import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

UMBRAL = -60
os.makedirs("figs", exist_ok=True)

info = pd.read_csv("data/mediciones.csv")
espectro = pd.read_csv("data/espectro_limpio.csv")
frec = pd.read_csv("data/indicadores_frecuencia.csv")
resumen = pd.read_csv("data/indicadores_canal.csv")
mas = frec.pct_ocupado.idxmax()
menos = frec.pct_ocupado.idxmin()


def limites_canales(ax):
    # líneas grises donde termina cada canal (A | B | C | D)
    for limite in (845, 850, 855):
        ax.axvline(limite, color="gray")


# ---------------- 1. Espectro de toda la ruta
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 7), sharex=True)
ax1.plot(frec.freq_mhz, frec.mediana, label="mediana de la ruta")
ax1.axhline(UMBRAL, color="red", linestyle="--", label="umbral -60 dBm")
ax1.set_ylabel("dBm")
ax1.set_title("Espectro 840-860 MHz (canales A, B, C, D separados por las líneas grises)")
ax1.legend()
limites_canales(ax1)

ax2.plot(frec.freq_mhz, frec.pct_ocupado, color="black")
ax2.plot(frec.freq_mhz[mas], frec.pct_ocupado[mas], "ro", label=f"más contaminada: {frec.freq_mhz[mas]:.3f} MHz")
ax2.plot(frec.freq_mhz[menos], frec.pct_ocupado[menos], "bo", label=f"menos contaminada: {frec.freq_mhz[menos]:.3f} MHz")
ax2.set_xlabel("Frecuencia (MHz)")
ax2.set_ylabel("% de la ruta ocupada")
ax2.legend()
limites_canales(ax2)
fig.savefig("figs/espectro.png")

# ---------------- 2. Frecuencia más y menos contaminada a lo largo de la ruta
fig, ax = plt.subplots(figsize=(12, 4))
ax.plot(info.orden, espectro[str(mas)], "o-", color="red", label=f"más contaminada ({frec.freq_mhz[mas]:.3f} MHz)")
ax.plot(info.orden, espectro[str(menos)], "o-", color="blue", label=f"menos contaminada ({frec.freq_mhz[menos]:.3f} MHz)")
ax.axhline(UMBRAL, color="red", linestyle="--", label="umbral")
ax.set_xlabel("Medida")
ax.set_ylabel("dBm")
ax.legend()
fig.savefig("figs/frecuencias_extremas.png")

# ---------------- 3. Potencia de cada canal
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 4.5))
ax1.boxplot([info.p_A, info.p_B, info.p_C, info.p_D], tick_labels=["A", "B", "C", "D"])
ax1.axhline(UMBRAL, color="red", linestyle="--")
ax1.set_ylabel("Potencia media del canal (dBm)")
for canal in ["A", "B", "C", "D"]:
    ax2.plot(info.orden, info["p_" + canal], "o-", markersize=3, label="Canal " + canal)
ax2.axhline(UMBRAL, color="red", linestyle="--")
ax2.set_xlabel("Medida")
ax2.legend()
fig.savefig("figs/canales.png")

# ---------------- 4. Ruta
fig, ax = plt.subplots(figsize=(7, 9))
ax.plot(info.lon, info.lat, "o-", color="gray")
imputados = info[info.gps_imputado]
ax.plot(imputados.lon, imputados.lat, "ro", label="GPS corregido")
ax.plot(info.lon.iloc[0], info.lat.iloc[0], "g^", markersize=12, label="inicio")
ax.plot(info.lon.iloc[-1], info.lat.iloc[-1], "ks", markersize=9, label="fin")
for i in range(0, len(info), 10):
    ax.text(info.lon[i], info.lat[i], info.archivo[i][:3])
ax.axis("equal")
ax.set_xlabel("Longitud")
ax.set_ylabel("Latitud")
ax.legend()
fig.savefig("figs/ruta.png")

# Largo de la ruta: 1 grado de latitud ~ 110.5 km; en longitud se multiplica por cos(latitud)
dx = np.diff(info.lon) * 111.3 * np.cos(np.radians(6.2))
dy = np.diff(info.lat) * 110.5
print(f"Largo de la ruta: {np.sqrt(dx**2 + dy**2).sum():.1f} km")

# ---------------- 5. ¿La temperatura afecta la medida?
fig, axs = plt.subplots(1, 3, figsize=(15, 4))
for ax, columna in zip(axs, ["orden", "nivel", "error_gps"]):
    r, p = stats.pearsonr(info.temp, info[columna])
    ax.scatter(info.temp, info[columna])
    ax.set_xlabel("Temperatura (°C)")
    ax.set_ylabel(columna)
    ax.set_title(f"r = {r:.2f}, p = {p:.3f}")
    print(f"Temperatura vs {columna}: r = {r:.2f}, p = {p:.3f}")
fig.savefig("figs/temperatura.png")

# ---------------- 6. Pico DC antes y después de corregir
archivos = sorted(glob.glob("medidas_2026_20/[0-9][0-9][0-9].txt"))
crudo = np.array([np.loadtxt(a, delimiter=",")[:1024] for a in archivos])
zona = range(490, 535)
fig, ax = plt.subplots(figsize=(10, 4))
ax.plot(frec.freq_mhz[zona], np.median(crudo[:, zona], axis=0), "o-", color="red", label="original")
ax.plot(frec.freq_mhz[zona], espectro.iloc[:, zona].median(), "o-", color="green", label="corregido")
ax.set_xlabel("Frecuencia (MHz)")
ax.set_ylabel("Mediana de la ruta (dBm)")
ax.set_title("Pico DC del USRP en 850 MHz")
ax.legend()
fig.savefig("figs/imputacion_dc.png")

# ---------------- 7. Antena (S11 medido con el analizador de redes)
antena = pd.read_csv("medidas_2026_20/ANTENNA1.csv", skiprows=17, skipfooter=1,
                     names=["freq", "s11"], engine="python")
antena["freq"] = antena.freq / 1e6
fig, ax = plt.subplots(figsize=(10, 4))
ax.plot(antena.freq, antena.s11, color="black")
ax.axvspan(840, 860, color="red", alpha=0.2, label="banda medida")
ax.axhline(-10, color="gray", linestyle="--", label="-10 dB (buena adaptación)")
ax.set_xlabel("Frecuencia (MHz)")
ax.set_ylabel("S11 (dB)")
ax.legend()
fig.savefig("figs/antena.png")

banda = antena[(antena.freq >= 840) & (antena.freq <= 860)]
print(f"Antena: en la banda el S11 va de {banda.s11.min():.1f} a {banda.s11.max():.1f} dB (no llega a -10 dB)")

# ---------------- 8. Recomendación para la ANE
print("\nRecomendación:")
for _, fila in resumen.iterrows():
    print(f"Canal {fila.canal}: ocupado en el {fila.pct_ocupado}% de la ruta, "
          f"{fila.pct_bins}% de sus frecuencias > -60 dBm -> {fila.recomendacion}")
