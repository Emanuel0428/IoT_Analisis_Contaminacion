# Examen 3 IoT: ocupación del espectro 840-860 MHz

Análisis de las medidas de una estación móvil en el occidente de Medellín para determinar qué tan contaminados están los canales A, B, C y D (5 MHz cada uno).

## Estructura

```
medidas_2026_20/   datos originales (001.txt ... 061.txt, ANTENNA1.csv)
etl.py             limpieza, imputación e indicadores  -> data/
analisis.py        gráficas del informe                 -> figs/
app.py             dashboard (Streamlit)
```

## Cómo correrlo (con uv, desde esta carpeta)

```bash
uv venv
uv pip install -r requirements.txt
uv run etl.py
uv run analisis.py
uv run streamlit run app.py
```

`etl.py` tiene que correr primero porque `analisis.py` y `app.py` leen lo que deja en `data/`.
Los resultados (calidad, imputaciones, indicadores, recomendación) salen por consola. Para guardarlos:

```bash
uv run etl.py > data/log_etl.txt
uv run analisis.py > data/log_analisis.txt
```

## Salidas

- `data/mediciones.csv`: una fila por medida con posición, temperatura y potencia por canal
- `data/espectro_limpio.csv`: espectro ya imputado (61 × 1024)
- `data/indicadores_frecuencia.csv` y `data/indicadores_canal.csv`
- `figs/*.png`: espectro, frecuencias extremas, canales, ruta, temperatura, pico DC y antena
