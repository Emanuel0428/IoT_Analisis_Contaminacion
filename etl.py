# ETL - Examen 3 IoT
# 1) lee las medidas, 2) revisa la calidad, 3) corrige lo malo,
# 4) calcula la potencia de cada canal y 5) guarda todo en data/
import glob
import os

import numpy as np
import pandas as pd

UMBRAL = -60  # dBm: por encima de esto se considera ocupado


def potencia_canal(dbm):
    # Sumatoria de Parseval: la potencia del canal es la suma de la potencia de sus bins, en mW
    # (no se puede sumar en dB). El equipo guarda |FFT/N|, así que la suma da la potencia media de la señal.
    mw = 10 ** (dbm / 10)
    return 10 * np.log10(mw.sum(axis=1))


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

# Nivel general de cada medida = mediana de su espectro; piso de ruido = percentil 10
info["nivel"] = espectro.median(axis=1)
info["piso"] = espectro.quantile(0.1, axis=1)
info["pico"] = espectro.max(axis=1)

# Saturación: el equipo guarda 20·log10|FFT/N|, así que 0 dB es el máximo del conversor (ADC).
# Un pico a menos de 6 dB de ese máximo satura el receptor. Además, su piso de ruido sube en toda la
# banda, incluso en frecuencias vacías (una antena cercana solo subiría su propio canal).
# La medida no representa el espectro: se conserva en el mapa, pero no entra en los indicadores.
info["saturada"] = info.pico > -6
print("Medidas saturadas (pico cerca de 0 dB):")
print(info.loc[info.saturada, ["archivo", "pico", "piso"]])
print(f"Piso de ruido típico: {info.piso.median():.1f} dB")

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
# Potencia de cada canal (bloques de 5 MHz = 256 bins) en cada medida
canales = {"A": (0, 255), "B": (256, 511), "C": (512, 767), "D": (768, 1023)}
for canal, (ini, fin) in canales.items():
    info["p_" + canal] = potencia_canal(espectro.loc[:, ini:fin])

# Los indicadores se calculan sin las medidas saturadas
ok = ~info.saturada
validas = espectro[ok]

# Por frecuencia: en qué porcentaje de la ruta supera el umbral
frec = pd.DataFrame()
frec["freq_mhz"] = 840 + np.arange(1024) * 20 / 1024
frec["canal"] = np.repeat(["A", "B", "C", "D"], 256)
frec["mediana"] = validas.median()
frec["pct_ocupado"] = (validas > UMBRAL).mean() * 100

# La más contaminada es la que está ocupada en más puntos de la ruta.
# (No se usa el promedio en mW entre medidas porque lo dominan las medidas más fuertes.)
mas = frec.pct_ocupado.idxmax()
menos = frec.pct_ocupado.idxmin()
info["p_frec_max"] = espectro[mas]

print("\n--- Indicadores ---")
resumen = []
for canal in canales:
    tipica = info.loc[ok, "p_" + canal].median()
    # Criterio del examen: el canal está ocupado donde su potencia supera -60 dBm (casi toda la ruta en los 4)
    ocupado = round((info.loc[ok, "p_" + canal] > UMBRAL).mean() * 100, 1)
    # Como los 4 salen ocupados, la recomendación compara qué parte del canal está libre:
    # % de sus frecuencias (bins) por encima de -60 dBm, promediado en toda la ruta
    bins = round(frec.pct_ocupado[frec.canal == canal].mean(), 1)
    if bins < 25:
        decision = "se recomienda usar"
    elif bins < 50:
        decision = "usar con cuidado"
    else:
        decision = "no se recomienda"
    resumen.append([canal, round(tipica, 1), ocupado, bins, decision])
resumen = pd.DataFrame(resumen, columns=["canal", "potencia_tipica", "pct_ocupado", "pct_bins", "recomendacion"])
print(resumen)
# Sensibilidad: cuánto cambiaría el % de frecuencias ocupadas si se dejaran las saturadas
con_todas = [round(float((espectro.loc[:, i:f] > UMBRAL).mean().mean()) * 100, 1) for i, f in canales.values()]
print("Con las medidas saturadas, % de frecuencias > -60 dBm (A, B, C, D):", con_todas)
print(f"Frecuencia más contaminada: {frec.freq_mhz[mas]:.3f} MHz, ocupada en el {frec.pct_ocupado[mas]:.0f}% de la ruta")
print(f"Frecuencia menos contaminada: {frec.freq_mhz[menos]:.3f} MHz, ocupada en el {frec.pct_ocupado[menos]:.0f}% de la ruta")

# ---------------- 5. Guardar
os.makedirs("data", exist_ok=True)
info.round(6).to_csv("data/mediciones.csv", index=False)
espectro.round(2).to_csv("data/espectro_limpio.csv", index=False)
frec.round(3).to_csv("data/indicadores_frecuencia.csv", index=False)
resumen.to_csv("data/indicadores_canal.csv", index=False)
print("\nGuardado en data/")
