# Tablero de arbolado urbano — Corrientes Capital

Tablero en Streamlit sobre el padrón de arbolado, su seguimiento/mantenimiento y los barrios
de la ciudad. La metodología completa (fuentes, transformaciones, fórmulas, supuestos y
límites) está en [`METODOLOGIA.md`](./METODOLOGIA.md) — léanla antes de citar cualquier número
de este tablero.

## Contenido del repo

| Archivo | Qué hace |
|---|---|
| `app.py` | La app de Streamlit completa: carga y limpieza de datos, filtros, y las 9 pestañas del tablero. |
| `requirements.txt` | Dependencias de Python, con versiones mínimas. |
| `.streamlit/config.toml` | Tema oscuro de Streamlit. **Tiene que vivir en esta carpeta `.streamlit/`, no en la raíz del repo** — si se mueve a la raíz, Streamlit lo ignora y el tema no se aplica. |
| `METODOLOGIA.md` | Fuente de los datos, qué se transforma en cada paso, fórmula de cada indicador, supuestos y límites. |
| `README.md` | Este archivo. |

## Cómo correrlo

1. Instalar las dependencias:
   ```bash
   pip install -r requirements.txt
   ```
2. Conseguir los tres CSV de origen (ver `METODOLOGIA.md` § 1 para la fuente y la fecha exactas
   de la versión usada en este análisis):
   - `arboles.csv`
   - `Seguimiento_Arboles.csv`
   - `barrios_de_la_ciudad.csv`
3. Correr la app:
   ```bash
   streamlit run app.py
   ```
4. En la barra lateral, elegir **"Usar archivos locales del repo"** si los tres CSV están en la
   misma carpeta que `app.py` (con esos nombres exactos), o **"Subir archivos"** para cargarlos
   manualmente desde cualquier ubicación.

## Versión de los datos usada en este análisis

> ⚠️ **Pendiente de completar por el equipo** — el notebook original cargaba estos archivos
> desde una carpeta personal de Google Drive, no desde una URL pública, así que no hay forma de
> reconstruir esto desde el código. Antes de publicar el tablero, completar:

- Fecha de descarga de `arboles.csv`: ____
- Fecha de descarga de `Seguimiento_Arboles.csv`: ____
- Fecha de descarga de `barrios_de_la_ciudad.csv`: ____
- URL o dataset de origen de cada uno: ____
- Filas al momento de esta descarga (para detectar si el dataset cambió en una descarga futura):
  10.286 árboles · 12.597 seguimientos · 140 barrios

## Notebook de análisis (`ArbolesFinal.ipynb`)

El notebook con el análisis exploratorio completo (EDA, cruces bivariados, tests de
chi-cuadrado, MCA) es un archivo aparte, pensado para correr en Google Colab:

1. Abrir en Colab y montar Google Drive.
2. Ajustar las rutas de `pd.read_csv(...)` a donde estén los tres CSV en el Drive.
3. Instalar `prince` si no está disponible (`!pip install prince`, ya incluido en la primera
   celda que lo usa).
4. Correr todas las celdas en orden — varias celdas de diagnóstico (huérfanos del merge,
   comparación "riesgo alto" vs. "parasitado"/"conflicto de vereda") solo tienen sentido después
   de las celdas de limpieza que las preceden.

## Notas para quien reproduzca esto con datos nuevos

- Si los tres CSV se vuelven a descargar, correr primero el notebook: los conteos de
  `METODOLOGIA.md` (10.286 árboles, 78 casos de riesgo alto, etc.) van a cambiar y hay que
  actualizarlos ahí también.
- La reparación de `sup_ha` (separador de miles mal puesto) es automática y no debería requerir
  ajustes, salvo que la fuente cambie el formato de exportación de ese campo.
