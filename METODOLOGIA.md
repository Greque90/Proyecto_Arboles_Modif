# Metodología

La versión de referencia es la del botón **«Metodología y detalles del proyecto»** del tablero; este archivo la replica. Si hay diferencias, vale la del tablero, que calcula las cifras con los datos.

Tablero: Arbolado urbano de Corrientes Capital · Tecnicatura en Ciencia de Datos e Inteligencia Artificial, Práctica Profesionalizante II (2026) · Autoras: Dolores Guadalupe Medina y Amalia Graciela Rodríguez.

## Fuentes y fechas

Los cuatro archivos fueron extraídos del **Portal de datos abiertos de la Municipalidad de Corrientes**. Una descarga nueva puede traer otros números; por eso los CSV están en el repositorio, que fija la versión con la que se validó el tablero.

| Archivo | Contenido | Publicación / actualización | Descarga |
|---|---|---|---|
| `arboles.csv` | Inventario de 10.286 árboles (Aplicación de Arbolado Urbano) | Publicado 13/03/2024, actualizado 22/09/2025 | 07/07/2026 |
| `Seguimiento_Arboles.csv` | 12.597 registros de seguimiento | Publicado 13/03/2024, actualizado 13/08/2025 | 07/07/2026 |
| `barrios_de_la_ciudad.csv` | Delimitación de barrios (Dirección General de Sistemas de Información Geográfica) | Actualizado 01/10/2025 | 07/07/2026 |
| `Densidad_Poblacional.csv` | Población por radio censal (datos del Censo 2010, INDEC, publicados en el portal) | Actualizado 01/10/2025 | **27/10/2026** |

## Orden de las transformaciones

1. Lectura de los CSV y conversión de fechas.
2. **Barrios:** se unen (`dissolve`) los polígonos con `id_barrios` repetido (Collantes y Molina Punta) en lugar de descartarlos. Los nombres se normalizan para mostrarlos (un solo criterio de mayúsculas).
3. **Superficie:** se calcula desde el polígono, proyectando a EPSG:32721. No se usa la columna `sup_ha` del CSV.
4. **Cruce espacial árbol → barrio** (`within`): 9.669 de 10.286 árboles (94,0%) quedan dentro de un barrio; 617 quedan fuera de todo polígono.
5. **Seguimientos huérfanos** (sin árbol en el padrón): 2.209 de 12.597 (17,5%), cuantificados y descartados; se muestran en la barra lateral.
6. **Estado actual:** último seguimiento de cada árbol según `fecha_hora` (una fila por árbol).
7. «Registro de Árbol» se excluye del análisis de mantenimiento: es el alta del árbol, no una intervención.
8. Indicadores por barrio. Hay árboles registrados en 107 de 138 barrios; los 31 restantes quedan fuera de los análisis por barrio.
9. **Población por barrio:** cada radio censal se reparte entre los barrios según la fracción de su área que cae en cada uno (intersección en EPSG:32721).

## Indicadores

- **Árboles por ha** = árboles del barrio ÷ superficie calculada (ha).
- **Necesidad de intervención** = % de árboles con 2 o más señales entre: riesgo de caída alto; salud Malo o Muerto; ahuecamiento severo; inclinación Pronunciada; fase vital Añosa o Decrépita. El umbral de 2 es un criterio del equipo, no una norma. Los rankings usan barrios con un mínimo de árboles (filtro ajustable, 30 por defecto).
- **Mantenimiento vencido** = `prox_fecha_mante` anterior a la fecha de consulta, sobre el último seguimiento.
- **Conflicto con vereda** = levantamiento de vereda Considerable o Leve. **Parasitados** = riesgo que empieza con «Arbol parasitado». Ambos son indicadores propios.
- **Antigüedad del relevamiento** = fecha de consulta − fecha del seguimiento más reciente del barrio.
- **Diversidad** = índice de Shannon, H = −Σ pᵢ·ln(pᵢ), con pᵢ la proporción de cada especie en el barrio.
- **Árboles cada 1.000 habitantes** = árboles del barrio ÷ población estimada × 1.000. Con menos de 500 habitantes estimados el cociente es inestable y se marca.
- **Prioridad de plantación:** árboles por ha por debajo de la mediana y habitantes por ha por encima de la mediana, sobre los barrios con árboles registrados y población estimada. El índice de 0 a 1 (promedio de percentiles de ambas variables) solo ordena.

## Análisis exploratorio y estadístico

- **Zona Norte / Sur:** se divide la ciudad por la latitud del cruce de Av. 3 de Abril y Rioja (−27,472), ajustable en la pestaña.
- **Riesgo vs. otras variables:** prueba de independencia chi-cuadrado entre `riesgo` y cada variable, sobre la tabla árbol × seguimiento; asociación significativa con p < 0,05.
- **MCA:** análisis de correspondencias múltiples sobre riesgo, estado de salud, inclinación, ahuecamiento, levantamiento de vereda y fase vital.

## Supuestos y límites

- **El padrón está concentrado en pocos barrios.** Alrededor de las tres cuartas partes de los árboles geolocalizados están en 8 barrios y la gran mayoría de los barrios tiene menos de un árbol registrado por hectárea. «Pocos árboles registrados» no equivale a «pocos árboles»: la prioridad de plantación señala sobre todo barrios poco relevados. Falta confirmar con el área municipal qué barrios tienen el relevamiento completo. (Las cifras exactas se muestran en la pestaña «Equidad y plantación».)
- La población es del Censo 2010 y se supone uniforme dentro de cada radio: es una aproximación territorial, no el acceso individual al arbolado.
- El padrón está desactualizado: el estado mostrado es el de la última inspección de cada árbol, no necesariamente el de hoy, y los mantenimientos programados figuran vencidos.
- Quedan fuera 617 árboles sin polígono y 31 barrios sin árboles registrados.
- La categoría `ahuecamiento` tiene valores inconsistentes en la fuente, lo que debilita su aporte al índice.
- La prioridad de plantación es una orientación preliminar: antes de plantar hay que verificar veredas, servicios, espacio y especie.

## Código y reproducibilidad

- Repositorio: https://github.com/Greque90/Proyecto_Arboles_Modif
- Incluye `app.py`, los cuatro CSV, `requirements.txt`, `README.md` y este archivo.
- Para correrlo: `pip install -r requirements.txt` y `streamlit run app.py`. Los CSV se leen desde la raíz del repositorio o se pueden subir desde la barra lateral.
- Cada gráfico lleva escrita su fuente al pie.
