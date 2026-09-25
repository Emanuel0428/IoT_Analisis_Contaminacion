# Pendiente — Examen 3 IoT (entrega 28 sep 2026)

## Hecho

- [x] `PLAN.md`: plan general y hallazgos de los datos
- [x] `etl.py`: limpieza, imputación, validación e indicadores → `data/*.csv` (resumen de calidad por consola)
- [x] `analisis.py`: 7 figuras en `figs/` + recomendación por consola

Para regenerar todo: `python etl.py && python analisis.py`. Para guardar los números del informe: `python etl.py > data/log_etl.txt` y `python analisis.py > data/log_analisis.txt`.

---

## 1. Dashboard — `app.py` (25 pts)

Instalar: `uv pip install -r requirements.txt` (sin plotly: el espectro usa `st.line_chart`)

Lee **solo** `data/` (mediciones e indicadores). No recalcula nada.

- [x] Ubicación de las mediciones (marcadores con popup: archivo, temperatura, potencia por canal, `gps_imputado`)
- [x] Ruta (PolyLine en orden 001→061, inicio/fin, 008 y 017 marcados como GPS imputado)
- [x] Heatmap por canal A / B / C / D (`p_A..p_D`)
- [x] Heatmap de temperatura (`temp`)
- [x] Heatmap de la frecuencia más contaminada, 853.145 MHz (`p_frec_max`)
- [x] Selector de capa en la barra lateral + tabla de `data/indicadores_canal.csv`
- [x] Panel de decisión arriba del mapa: canal y frecuencia más/menos contaminados + recomendación para la ANE (la recomendación ahora sale de `etl.py`, columna `recomendacion`). Se quitó el espectro por medida: no lo pide el PDF
- [x] Heatmap sutil: suavizado gaussiano solo sobre la ruta (~400 m), opacidad máx. 0.55, escala común azul→claro→rojo centrada en −60 dBm (lo cercano al umbral casi transparente), leyenda con rangos Libre / Cerca del umbral / Contaminado. `folium.plugins.HeatMap` se descartó porque suma los puntos que se enciman
- [x] Probar local: `streamlit run app.py`

## 2. Despliegue en la nube (competencias 2 y 3)

- [x] Repo en GitHub: github.com/Emanuel0428/IoT_Analisis_Contaminacion
- [ ] Publicar en EC2 (puerto 8501 abierto) → URL pública = "aplicación remota"
- [ ] (opcional) Notificación: alerta por Telegram o email cuando un canal supera el umbral → cubre "visualice/notifique"

## 3. Informe escrito (25 pts)

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

## 4. Sustentación

- [ ] Parseval en dBm: sumar/promediar en mW, nunca en dB
- [ ] Qué es el pico DC del USRP y por qué se interpola
- [ ] Por qué se interpola el GPS en lugar de borrar la fila
- [ ] El criterio de −60 dBm: por canal (potencia media) vs por bin (% de ocupación)
- [ ] Repasar los comentarios del código (`etl.py`, `analisis.py`, `app.py`)
