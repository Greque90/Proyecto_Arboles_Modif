# Metodología

Este documento explica cómo se construyeron los números que muestran el notebook
(`ArbolesFinal.ipynb`) y el tablero (`app.py`), para que puedan reproducirse y para que
cualquier pregunta sobre "¿de dónde sale ese número?" tenga una respuesta escrita, no una
que dependa de leer el código.

---

## 1. Fuente y fecha

| Archivo | Contenido | Filas |
|---|---|---|
| `arboles.csv` | Padrón de árboles (id, especie, dirección, vereda, coordenadas) | 10.286 |
| `Seguimiento_Arboles.csv` | Historial de seguimientos/mantenimiento por árbol | 12.597 |
| `barrios_de_la_ciudad.csv` | Polígonos y superficie de los barrios de Corrientes Capital | 140 |

**Pendiente de completar por el equipo antes de publicar** (no lo podemos reconstruir desde
el notebook, que carga los archivos desde una carpeta personal de Google Drive y no desde una
URL pública):

- [ ] URL exacta de descarga de cada uno de los 3 CSV.
- [ ] Fecha en la que se descargaron.
- [ ] Si hay una API o un portal versionado (candidato: Portal de Datos Abiertos de la Ciudad
  de Corrientes, comprometido en el plan de acción de Gobierno Abierto 2022-2024 de la
  Municipalidad), indicar el identificador del recurso/dataset ahí.

Esto importa porque **los datos abiertos cambian entre descargas**: si alguien vuelve a bajar
estos mismos tres archivos dentro de un mes, los conteos de este documento (10.286 árboles,
12.597 seguimientos, etc.) van a estar desactualizados y hay que volver a correr el notebook.

---

## 2. Qué se transforma (filas antes → después de cada paso)

| Paso | Filas antes | Filas después | Qué se pierde y por qué |
|---|---|---|---|
| Carga `arboles.csv` | — | 10.286 árboles | — |
| Carga `Seguimiento_Arboles.csv` | — | 12.597 seguimientos | — |
| Carga `barrios_de_la_ciudad.csv` | — | 140 barrios | — |
| **Cruce espacial** (punto-en-polígono: `lat`/`lng` de cada árbol vs. polígono de cada barrio) | 10.286 árboles | 9.669 geolocalizados (94%) | 617 árboles caen fuera de todos los polígonos del shapefile de barrios. **Exclusión acordada con la cátedra**, no un bug — ver Supuesto 4. Quedan sin `nombre_barrio` y por lo tanto fuera de cualquier análisis agrupado por barrio. De paso, 33 de los 140 barrios no tienen ningún árbol geolocalizado dentro (107/140 sí tienen). |
| **Merge árboles + seguimiento** (`pd.merge(arboles, mantenimiento, on="id_arbol", how="left")`, con `arboles` como tabla base) | 12.597 seguimientos | 10.388 seguimientos conservados | 2.209 seguimientos (17,5%) tienen un `id_arbol` que no existe en `arboles.csv`. El `how="left"` los descarta porque no hay contra qué pegarlos. Ver Supuesto 3. |
| **Filtros del tablero** (barrio, en la barra lateral) | según selección | según selección | No es un paso fijo del pipeline: cambia con cada interacción del usuario. Todas las pestañas del tablero trabajan sobre estos datos ya filtrados. |
| **Deduplicación a "último seguimiento por árbol"** (`sort_values("fecha_hora").drop_duplicates("id_arbol", keep="last")`) | 10.388 filas árbol×seguimiento | ≤ 10.286 filas, una por árbol | Se aplica **solo** en los indicadores que representan el *estado actual* de un árbol (riesgo, salud, ahuecamiento, inclinación, fase vital, próximo mantenimiento programado): índice de intervención v1/v2 y la pestaña "Indicadores por barrio". Los conteos de actividad histórica (tipos de mantenimiento más frecuentes, línea de seguimientos por mes) **no** deduplican, porque ahí interesa el volumen de trabajo realizado en el tiempo, no el estado final de cada árbol. |

---

## 3. Cómo se calcula cada número

Todas las fórmulas que siguen usan, salvo que se diga lo contrario, el **último seguimiento
de cada árbol** (ver deduplicación arriba).

| Indicador | Fórmula (una línea) |
|---|---|
| Cobertura del padrón | `árboles con nombre_barrio asignado / total de árboles` (geolocalización); `barrios con ≥1 árbol / total de barrios` |
| Árboles por hectárea | `total_arboles(barrio) / sup_ha(barrio)`, con `sup_ha` reparada (ver Supuesto 5) |
| Mantenimiento vencido | `% de árboles cuyo prox_fecha_mante (último seguimiento) < fecha de hoy` |
| Conflicto con vereda | `% de árboles con levantamiento_vereda en {Leve, Considerable}` |
| Árboles parasitados | `% de árboles cuyo riesgo empieza con "Arbol parasitado"` (agrupa las 4 subcategorías: con especies vegetales / insectos / hongos / otros animales) |
| Antigüedad del relevamiento | `hoy − MAX(fecha_hora)` entre todos los seguimientos del barrio, en días. Si el barrio no tiene ningún seguimiento con fecha válida, el resultado queda **sin dato**, no en 0. |
| Diversidad de especies | Índice de Shannon `H = −Σ(pᵢ · ln pᵢ)` sobre las proporciones `pᵢ` de cada especie dentro del barrio; se reporta también `% de la especie dominante` |
| **Índice de intervención v1** (pestaña "Necesidad de intervención") | Promedio de 3 porcentajes por barrio: `(% riesgo_relevante + % conflicto_vereda + % estado_critico) / 3`, donde `riesgo_relevante` = cualquier `riesgo` ≠ "Sin riesgo de caída" y `estado_critico` = `estado_salud` en {Malo, Muerto} |
| **Índice de intervención v2** (pestaña "Indicadores por barrio") | Cada árbol suma 1 de 5 puntos si tiene: `riesgo` relevante, `estado_salud` crítico, `ahuecamiento` ≠ "No", `inclinacion` ≠ "Sin inclinación", `fase_vital` == "Añoso". El índice del barrio es el **promedio** de `(puntos / 5 × 100)` entre sus árboles |

Los índices v1 y v2 son promedios **simples, sin ponderar**: cada componente pesa igual aunque
en la realidad no tengan la misma frecuencia ni gravedad (ver Supuesto 6).

---

## 4. Supuestos

1. **Se usa el último seguimiento por árbol, no todos**, para cualquier indicador que
   represente el *estado actual* del árbol (riesgo, salud, ahuecamiento, inclinación, fase
   vital, mantenimiento programado). Hay 98 árboles con más de un seguimiento registrado, y 30
   de ellos tienen un `riesgo` distinto entre sus propios registros — sin esta regla, esos
   árboles se contarían más de una vez y con estados contradictorios.

2. **"Registro de Árbol" no cuenta como mantenimiento.** Es el 72% de los seguimientos
   (9.125 de 12.597) y corresponde al alta del árbol en el padrón — el evento administrativo
   de ingreso, análogo a que un hospital admita un paciente. Se excluye de la pregunta "¿qué
   tipo de mantenimiento es más frecuente?" y se muestra por separado; con esa exclusión, la
   respuesta real es Plantación (68,9%) seguida de Mantenimiento propiamente dicho (25,4%).

3. **Los 2.209 seguimientos huérfanos** (17,5% del total, con `id_arbol` que no existe en
   `arboles.csv`) se descartan en el merge, pero **se cuentan explícitamente antes de
   descartarlos** (celda de diagnóstico en el notebook, justo antes del merge). El tablero hoy
   no repite ese conteo en pantalla — queda como pendiente si se quiere mostrar también ahí
   como indicador de calidad de datos.

4. **Los 617 árboles sin barrio asignado y los 33 barrios sin árboles registrados se excluyen
   de todo análisis por barrio.** Esto es una **decisión acordada con la cátedra, no una
   omisión**: se documenta acá y además se muestra en el indicador de cobertura que aparece
   arriba de todo en el tablero ("9.669 de 10.286 árboles geolocalizados · 107 de 140 barrios
   con registros"), para que quien abre el tablero lo sepa sin tener que leer este documento.

5. **`sup_ha` se repara automáticamente al cargar los datos.** Venía con el separador de miles
   mal puesto sobre toda la cadena de dígitos (ej. `488.214.568.517.694` en vez de
   `488.214568517694` hectáreas). La función `reparar_sup_ha()` en `app.py` toma el primer
   grupo como parte entera y concatena el resto como decimales; si un valor ya venía bien
   formado, la función no lo altera.

6. **Los índices de intervención (v1 y v2) son un promedio simple, no ponderado.** Cada
   componente (riesgo, salud, vereda, ahuecamiento, inclinación, añosidad) pesa igual, aunque
   en frecuencia real no lo sean — por ejemplo "estado crítico" es mucho más raro que
   "conflicto de vereda". Ponderar de otra forma es una decisión de política de gestión
   arbórea, no una decisión técnica, y no se tomó en este proyecto.

7. **Los barrios con menos de 30 árboles se excluyen de los rankings por porcentaje**
   (parámetro ajustable con un slider en el tablero), para que 1 o 2 casos en un barrio chico
   no generen un porcentaje inflado del 50-100%.

---

## 5. Límites (qué no se puede responder con estos datos)

- **No hay causalidad, solo asociación.** Los tests de chi-cuadrado del notebook (riesgo vs.
  inclinación, riesgo vs. ahuecamiento, riesgo vs. fase vital) muestran asociación
  estadísticamente significativa, no que una variable *cause* la otra.
- **El padrón está desactualizado.** La última inspección registrada es del 20/11/2025 y los
  3.426 mantenimientos programados (`prox_fecha_mante`) están **todos vencidos** a la fecha de
  hoy. Cualquier indicador de "estado actual" refleja el último dato cargado en el sistema, no
  necesariamente lo que hay hoy en la calle.
- **Los 617 árboles fuera de polígono y los 2.209 seguimientos huérfanos no aparecen en ningún
  resultado por barrio.** Existen en el padrón, pero ninguna conclusión sobre "el barrio X"
  los incluye.
- **La diversidad de especies se mide sobre los árboles geolocalizados**, no sobre el total de
  la ciudad; si el relevamiento tuvo sesgos sistemáticos hacia ciertas zonas, la diversidad
  medida hereda ese sesgo.
- **El MCA es descriptivo, no predictivo.** Las dos primeras dimensiones explican ~72% de la
  variabilidad de las variables categóricas analizadas — es una herramienta exploratoria para
  ver qué categorías tienden a aparecer juntas, no un modelo que prediga qué árbol va a
  necesitar intervención.
- **No hay datos de presupuesto ni de capacidad operativa municipal.** Los índices de
  intervención priorizan barrios en términos técnicos (dónde hay más problemas relativos), no
  dicen cuántos barrios se pueden atender por año ni a qué costo.
- **Los indicadores por barrio no distinguen "sano" de "sin datos".** Un barrio con 0% en un
  indicador puede tener realmente 0 casos, o puede tener muchos árboles sin ningún seguimiento
  registrado (por eso se agregó `pct_sin_seguimiento` como columna de alerta en la pestaña de
  indicadores).
