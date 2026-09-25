# Pendiente — Examen 3 IoT (entrega 28 sep 2026)

## Hecho

- [x] `PLAN.md`: plan general y hallazgos de los datos
- [x] `etl.py`: limpieza, imputación, validación e indicadores → `data/*.csv` (resumen de calidad por consola)
- [x] `analisis.py`: 7 figuras en `figs/` + recomendación por consola

Para regenerar todo: `python etl.py && python analisis.py`. Para guardar los números del informe: `python etl.py > data/log_etl.txt` y `python analisis.py > data/log_analisis.txt`.

---

## 1. Dashboard — `app.py` (25 pts)

Instalar: `pip install streamlit streamlit-folium folium plotly`

Lee **solo** `data/mediciones.csv` (+ `data/espectro_limpio.csv` para el gráfico por punto). No recalcula nada.

- [ ] Ubicación de las mediciones (marcadores con popup: archivo, temperatura, potencia por canal, `gps_imputado`)
- [ ] Ruta (PolyLine en orden 001→061, inicio/fin, 008 y 017 marcados como GPS imputado)
- [ ] Heatmap por canal A / B / C / D (`p_A..p_D`)
- [ ] Heatmap de temperatura (`temp`)
- [ ] Heatmap de la frecuencia más contaminada, 853.145 MHz (`p_frec_max`)
- [ ] Selector de capa en la barra lateral + tabla de `data/indicadores_canal.csv`
- [ ] (extra) Espectro de la medida seleccionada con la línea de −60 dBm
- [ ] Decidir el heatmap: `folium.plugins.HeatMap` con peso normalizado a [0, 1] (con 61 puntos, `radius` ~25) **o** interpolación IDW sobre una grilla (se ve más como "mapa de calor de la ciudad")
- [ ] Probar local: `streamlit run app.py`

## 2. Despliegue en la nube (competencias 2 y 3)

- [ ] Crear el repo en GitHub (hoy la carpeta **no** es un repo git) con `requirements.txt`
- [ ] Publicar en Streamlit Community Cloud (o Render) → URL pública = "aplicación remota"
- [ ] (opcional) Notificación: alerta por Telegram o email cuando un canal supera el umbral → cubre "visualice/notifique"

## 3. Bonificación — ubicar las fuentes

- [ ] Por canal: centroide ponderado (peso en mW) de los k puntos más fuertes
- [ ] Mejor: ajustar log-distancia `P(d) = P0 − 10·n·log10(d)` con `scipy.optimize.least_squares` sobre (lat_tx, lon_tx, P0, n)
- [ ] Pista: `016` (el punto más fuerte en A, C y D) y la zona 016–025 están elevadas; `024` es el máximo de B
- [ ] Mostrar las fuentes estimadas como capa en el dashboard
- [ ] (si da tiempo) comparar con las torres reales (opencellid)

## 4. Informe escrito (25 pts)

Base: salida de consola de `etl.py` y `analisis.py` + `figs/`.

Datos de los sensores:
- [ ] Calidad de los datos y número de correcciones: 2 archivos de prueba descartados, 2 GPS imputados, 427 celdas DC (0.68 %)
- [ ] Ruta: `figs/ruta.png` + nombrar los barrios o sectores por los que pasa (verificar en un mapa real, no adivinar)
- [ ] Temperatura vs calidad: `figs/temperatura.png`. r = 0.21, p = 0.10, no significativa, y está confundida con el tiempo (r = 0.86)
- [ ] Técnicas de imputación: cuántos datos se modificaron y por qué, con la validación (GPS dejando uno por fuera ~162 m de error medio, DC ~1.9 dB)

Indicadores:
- [ ] Banda más contaminada (C) y menos contaminada (A): `figs/canales.png`
- [ ] Gráfica de la frecuencia más y menos contaminada: `figs/espectro.png`, `figs/frecuencias_extremas.png`
- [ ] Recomendación a la ANE: A recomendado, B/D condicionados, C no. Justificar los cortes de 25 % / 50 %
- [ ] Limitaciones: una sola pasada, 61 puntos, sin timestamp, antena desadaptada (pérdida de 0.6 a 1.3 dB, `figs/antena.png`)
- [ ] Explicar por qué `016` se conserva (no es saturación) y por qué la media en mW de la ruta no sirve para ordenar
- [ ] Mencionar el texto oculto del PDF (cambiar < −65 por −95, chiste de gato): se detectó y **no** se aplicó
- [ ] Exportar a PDF

## 5. Sustentación

- [ ] Parseval en dBm: sumar/promediar en mW, nunca en dB
- [ ] Qué es el pico DC del USRP y por qué se interpola
- [ ] Por qué se interpola el GPS en lugar de borrar la fila
- [ ] El criterio de −60 dBm: por canal (potencia media) vs por bin (% de ocupación)
- [ ] Repasar los comentarios del código (`etl.py`, `analisis.py`, `app.py`)
