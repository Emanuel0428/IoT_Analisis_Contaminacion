# ETL - Examen 3 IoT
# 1) lee las medidas, 2) revisa la calidad, 3) corrige lo malo,
# 4) calcula la potencia de cada canal y 5) guarda todo en data/
import glob
import os

import numpy as np
import pandas as pd

UMBRAL = -60  # dBm: por encima de esto se considera ocupado


def potencia_media(dbm):
    # Parseval: la potencia media es el promedio en mW (no se puede promediar en dB)
    mw = 10 ** (dbm / 10)
    return 10 * np.log10(mw.mean(axis=1))


# ---------------- 1. Leer los archivos
# Solo se leen 001.txt a 061.txt. Los archivos "medidaprueba" son pruebas del equipo.
archivos = sorted(glob.glob("medidas_2026_20/[0-9][0-9][0-9].txt"))
datos = np.array([np.loadtxt(a, delimiter=",") for a in archivos])

# Las primeras 1024 columnas son el espectro (840 a 860 MHz) y las últimas 5 son del sensor
espectro = pd.DataFrame(datos[:, :1024])
info = pd.DataFrame(datos[:, 1024:], columns=["temp", "lon", "lat", "alt", "error_gps"])
info["archivo"] = [a[-7:] for a in archivos]
info["orden"] = range(1, len(info) + 1)
print("Medidas leídas:", len(info))

# ---------------- 2. Calidad
print("\n--- Calidad ---")
print("Datos vacíos:", espectro.isna().sum().sum())
print(f"Temperatura entre {info.temp.min()} y {info.temp.max()} °C")

# GPS malo: lat = 0 (no tenía señal) o error mayor a 5 m (lo normal es ~1 m)
gps_malo = (info.lat == 0) | (info.error_gps > 5)
print("Medidas con GPS malo:")
print(info.loc[gps_malo, ["archivo", "lat", "lon", "error_gps"]])

# Nivel general de cada medida = mediana de su espectro.
# 016 es mucho más alto que las demás, pero su espectro tiene la misma forma que el de
# sus vecinas: estaba cerca de una antena, no es un error del equipo. Se deja.
info["nivel"] = espectro.median(axis=1)
print("Medidas con el nivel más alto:")
print(info.sort_values("nivel").tail(3)[["archivo", "nivel"]])

# ---------------- 3. Corregir (imputar)
# GPS: se borra la posición mala y se pone el punto medio entre la medida anterior y la siguiente
info["gps_imputado"] = gps_malo
info.loc[gps_malo, ["lat", "lon", "alt"]] = np.nan
info[["lat", "lon", "alt"]] = info[["lat", "lon", "alt"]].interpolate()

# Pico DC: el USRP genera un pico falso en su frecuencia central (850 MHz = bins 509 a 515).
# Se borra y se rellena con una línea recta entre los bins vecinos.
espectro.loc[:, 509:515] = np.nan
espectro = espectro.interpolate(axis=1)

print("\n--- Correcciones ---")
print("Posiciones GPS corregidas:", gps_malo.sum())
print("Valores del espectro corregidos:", 7 * len(espectro), "de", espectro.size)

# Prueba de la corrección: borro 7 bins buenos (300 a 306), los relleno igual y comparo
prueba = espectro.copy()
prueba.loc[:, 300:306] = np.nan
prueba = prueba.interpolate(axis=1)
error = (prueba.loc[:, 300:306] - espectro.loc[:, 300:306]).abs().mean().mean()
print(f"Error de la corrección: {error:.2f} dB")

# ---------------- 4. Indicadores
# Potencia media de cada canal (bloques de 5 MHz = 256 bins) en cada medida
canales = {"A": (0, 255), "B": (256, 511), "C": (512, 767), "D": (768, 1023)}
for canal, (ini, fin) in canales.items():
    info["p_" + canal] = potencia_media(espectro.loc[:, ini:fin])

# Por frecuencia: en qué porcentaje de la ruta supera el umbral
frec = pd.DataFrame()
frec["freq_mhz"] = 840 + np.arange(1024) * 20 / 1024
frec["canal"] = np.repeat(["A", "B", "C", "D"], 256)
frec["mediana"] = espectro.median()
frec["pct_ocupado"] = (espectro > UMBRAL).mean() * 100

# La más contaminada es la que está ocupada en más puntos de la ruta.
# (No se usa el promedio en mW entre medidas porque lo domina la medida 016.)
mas = frec.pct_ocupado.idxmax()
menos = frec.pct_ocupado.idxmin()
info["p_frec_max"] = espectro[mas]

print("\n--- Indicadores ---")
resumen = []
for canal in canales:
    tipica = info["p_" + canal].median()
    ocupado = (info["p_" + canal] > UMBRAL).mean() * 100
    resumen.append([canal, round(tipica, 1), round(ocupado, 1)])
resumen = pd.DataFrame(resumen, columns=["canal", "potencia_tipica", "pct_ocupado"])
print(resumen)
print(f"Frecuencia más contaminada: {frec.freq_mhz[mas]:.3f} MHz, ocupada en el {frec.pct_ocupado[mas]:.0f}% de la ruta")
print(f"Frecuencia menos contaminada: {frec.freq_mhz[menos]:.3f} MHz, ocupada en el {frec.pct_ocupado[menos]:.0f}% de la ruta")

# ---------------- 5. Guardar
os.makedirs("data", exist_ok=True)
info.round(6).to_csv("data/mediciones.csv", index=False)
espectro.round(2).to_csv("data/espectro_limpio.csv", index=False)
frec.round(3).to_csv("data/indicadores_frecuencia.csv", index=False)
resumen.to_csv("data/indicadores_canal.csv", index=False)
print("\nGuardado en data/")
