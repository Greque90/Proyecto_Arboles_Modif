import json

import numpy as np
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.patches import Polygon as MplPolygon
from matplotlib.cm import ScalarMappable
from scipy.stats import chi2_contingency
from shapely.geometry import Point, shape
from shapely.strtree import STRtree

# ==========================================================
# Configuración inicial
# ==========================================================
st.set_page_config(page_title="Arbolado Urbano - Corrientes Capital", layout="wide", page_icon="🌳")

# ==========================================================
# Estética: paleta de alto impacto para exposición (tema oscuro)
# ==========================================================
PALETA = {
    "fondo": "#0E1F17",
    "fondo_secundario": "#153726",
    "verde_neon": "#00E676",
    "verde_oscuro": "#00C853",
    "amarillo": "#FFD600",
    "naranja": "#FF6D00",
    "rojo": "#FF1744",
    "azul": "#00B0FF",
    "texto": "#F1FFF6",
}

# Paleta de colores vivos para gráficos multi-categoría (chi2, MCA)
PALETA_VIVA = ["#00E676", "#00B0FF", "#FFD600", "#FF1744", "#D500F9", "#FF6D00", "#1DE9B6"]

st.markdown(
    f"""
    <style>
    /* Encabezado con degradé de alto contraste */
    .encabezado-app {{
        background: linear-gradient(90deg, #003D1F 0%, #00A152 55%, #00E676 100%);
        padding: 1.6rem 2rem;
        border-radius: 16px;
        margin-bottom: 1.4rem;
        box-shadow: 0 4px 20px rgba(0, 230, 118, 0.25);
    }}
    .encabezado-app h1 {{
        color: white !important;
        margin: 0;
        font-size: 2.2rem;
        font-weight: 800;
        text-shadow: 0 2px 6px rgba(0,0,0,0.35);
    }}
    .encabezado-app p {{
        color: #E8FFF0 !important;
        margin-top: 0.5rem;
        margin-bottom: 0;
        font-size: 1rem;
    }}

    /* Tarjetas de métricas (KPIs) con look "neón" */
    div[data-testid="stMetric"] {{
        background-color: {PALETA['fondo_secundario']};
        border: 1px solid rgba(0, 230, 118, 0.35);
        border-left: 6px solid {PALETA['verde_neon']};
        border-radius: 12px;
        padding: 1rem 1.1rem;
        box-shadow: 0 2px 10px rgba(0,0,0,0.25);
    }}
    div[data-testid="stMetricValue"] {{
        color: {PALETA['verde_neon']} !important;
        font-size: 1.9rem !important;
        font-weight: 800 !important;
    }}
    div[data-testid="stMetricLabel"] {{
        color: {PALETA['texto']} !important;
        opacity: 0.85;
    }}

    /* Pestañas grandes y bien visibles */
    button[data-baseweb="tab"] {{
        font-weight: 700;
        font-size: 1.02rem;
    }}
    button[data-baseweb="tab"][aria-selected="true"] {{
        color: {PALETA['verde_neon']} !important;
        border-bottom: 3px solid {PALETA['verde_neon']} !important;
    }}

    /* Subtítulos de sección con acento neón */
    h3 {{
        color: {PALETA['verde_neon']};
        border-bottom: 3px solid {PALETA['amarillo']};
        padding-bottom: 0.35rem;
        font-weight: 800;
    }}

    /* Alertas (success/warning/info) más vívidas */
    div[data-testid="stAlertContentSuccess"] {{
        font-size: 1.05rem;
    }}
    </style>

    <div class="encabezado-app">
        <h1>🌳 Análisis Integral del Arbolado Urbano — Corrientes Capital</h1>
        <p>Tablero basado en arboles.csv, Seguimiento_Arboles.csv y barrios_de_la_ciudad.csv
        (Práctica Profesionalizante II - 2026).</p>
    </div>
    """,
    unsafe_allow_html=True,
)


def estilo_oscuro(fig, ax_o_axes):
    """Aplica el tema oscuro a una figura de matplotlib para que combine con la app."""
    fig.patch.set_facecolor(PALETA["fondo"])
    ejes = ax_o_axes if isinstance(ax_o_axes, (list, np.ndarray)) else [ax_o_axes]
    for ax in ejes:
        ax.set_facecolor(PALETA["fondo_secundario"])
        ax.title.set_color(PALETA["texto"])
        ax.xaxis.label.set_color(PALETA["texto"])
        ax.yaxis.label.set_color(PALETA["texto"])
        ax.tick_params(colors=PALETA["texto"])
        for spine in ax.spines.values():
            spine.set_color(PALETA["texto"])
        leg = ax.get_legend()
        if leg is not None:
            leg.get_frame().set_facecolor(PALETA["fondo_secundario"])
            for text in leg.get_texts():
                text.set_color(PALETA["texto"])
    return fig


def formato_ar(n):
    """Formatea un entero con separador de miles '.' (convención local)."""
    return f"{int(n):,}".replace(",", ".")


def reparar_sup_ha(valor):
    """
    sup_ha llega mal formada: p.ej. '488.214.568.517.694' en vez de '488.214568517694'.
    El punto decimal original quedó tratado como si fuera un separador de miles sobre
    toda la cadena de dígitos, agrupándolos de a 3 desde la derecha. Se reconstruye
    tomando el primer grupo como parte entera y concatenando el resto como decimales
    (si el valor ya viene con un solo punto, esto no lo altera).
    """
    if pd.isna(valor):
        return np.nan
    texto = str(valor).strip()
    partes = texto.split(".")
    if len(partes) <= 1:
        try:
            return float(texto)
        except ValueError:
            return np.nan
    entero, decimales = partes[0], "".join(partes[1:])
    try:
        return float(f"{entero}.{decimales}")
    except ValueError:
        return np.nan


def grafico_ranking_horizontal(serie, color, titulo, xlabel):
    """
    Barras horizontales ordenadas de mayor a menor, con el valor más alto arriba.
    st.bar_chart sobre una Series ordena el eje por índice (alfabético), no por valor,
    así que para un ranking usamos matplotlib con orden explícito.
    """
    serie_ordenada = serie.sort_values(ascending=True)  # ascending: barh dibuja de abajo hacia arriba
    fig, ax = plt.subplots(figsize=(8, max(2.5, 0.4 * len(serie_ordenada))))
    ax.barh(serie_ordenada.index.astype(str), serie_ordenada.values, color=color)
    ax.set_xlabel(xlabel)
    ax.set_title(titulo)
    for i, v in enumerate(serie_ordenada.values):
        ax.text(v, i, f" {v:,.1f}".rstrip("0").rstrip(".") if isinstance(v, float) else f" {v:,}",
                va="center", fontsize=8, color=PALETA["texto"])
    estilo_oscuro(fig, ax)
    return fig


def limites_totales(geometrias):
    """Bounding box (minx, miny, maxx, maxy) de una lista de geometrías shapely."""
    xs_min, ys_min, xs_max, ys_max = [], [], [], []
    for geom in geometrias:
        minx, miny, maxx, maxy = geom.bounds
        xs_min.append(minx); ys_min.append(miny)
        xs_max.append(maxx); ys_max.append(maxy)
    return min(xs_min), min(ys_min), max(xs_max), max(ys_max)


def dibujar_choropleta(barrios_geo, valores, titulo, etiqueta_barra, cmap_nombre="YlOrRd"):
    """
    Dibuja un choropleta de barrios coloreado según 'valores' (Series indexada por nombre_barrio).
    barrios_geo: DataFrame con columnas 'nombre_barrio' y 'geometry' (shapely).
    Los barrios sin dato se pintan en gris para que la ausencia sea visible, no invisible.
    """
    valores_validos = valores.replace([np.inf, -np.inf], np.nan)
    vmin = float(np.nanmin(valores_validos.values)) if valores_validos.notna().any() else 0
    vmax = float(np.nanmax(valores_validos.values)) if valores_validos.notna().any() else 1
    if vmin == vmax:
        vmax = vmin + 1
    cmap = plt.get_cmap(cmap_nombre)
    norm = mcolors.Normalize(vmin=vmin, vmax=vmax)

    fig, ax = plt.subplots(figsize=(8, 8))

    for _, fila in barrios_geo.iterrows():
        nombre = fila["nombre_barrio"]
        geom = fila["geometry"]
        valor = valores_validos.get(nombre, np.nan)
        color = cmap(norm(valor)) if pd.notna(valor) else "#3A3A3A"

        partes = list(geom.geoms) if geom.geom_type == "MultiPolygon" else [geom]
        for parte in partes:
            x, y = parte.exterior.xy
            ax.add_patch(
                MplPolygon(list(zip(x, y)), closed=True, facecolor=color,
                           edgecolor=PALETA["texto"], linewidth=0.4, alpha=0.95)
            )
            for interior in parte.interiors:
                xi, yi = interior.xy
                ax.add_patch(
                    MplPolygon(list(zip(xi, yi)), closed=True, facecolor=PALETA["fondo"],
                               edgecolor=PALETA["texto"], linewidth=0.3)
                )

    minx, miny, maxx, maxy = limites_totales(barrios_geo["geometry"])
    pad_x, pad_y = (maxx - minx) * 0.03, (maxy - miny) * 0.03
    ax.set_xlim(minx - pad_x, maxx + pad_x)
    ax.set_ylim(miny - pad_y, maxy + pad_y)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title(titulo)

    sm = ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=ax, label=etiqueta_barra, fraction=0.04, pad=0.02)
    cbar.ax.yaxis.label.set_color(PALETA["texto"])
    cbar.ax.tick_params(colors=PALETA["texto"])

    estilo_oscuro(fig, ax)
    return fig


# ==========================================================
# 1. Carga y preparación de datos
# ==========================================================
@st.cache_data
def cargar_datos(archivo_arboles, archivo_mantenimiento, archivo_barrios):
    arboles = pd.read_csv(archivo_arboles)
    mantenimiento = pd.read_csv(archivo_mantenimiento)
    barrios = pd.read_csv(archivo_barrios)

    # --- Unión espacial árbol -> barrio (equivalente a gpd.sjoin del notebook) ---
    barrios = barrios.copy()
    _sup_ha_original = barrios["sup_ha"].copy()
    barrios["sup_ha"] = barrios["sup_ha"].apply(reparar_sup_ha)
    barrios.attrs["sup_ha_original"] = _sup_ha_original  # se usa solo para mostrar el ejemplo de reparación
    barrios["geometry"] = barrios["the_geom"].apply(lambda g: shape(json.loads(g)))

    poligonos = list(barrios["geometry"])
    tree_idx = STRtree(poligonos)
    geom_a_barrio = {id(geom): nombre for geom, nombre in zip(poligonos, barrios["nombre_barrio"])}

    def encontrar_barrio(row):
        punto = Point(row["lng"], row["lat"])
        for idx in tree_idx.query(punto):
            geom = poligonos[idx]
            if geom.contains(punto):
                return geom_a_barrio[id(geom)]
        return None

    arboles = arboles.copy()
    arboles["nombre_barrio"] = arboles.apply(encontrar_barrio, axis=1)

    # --- df final: arboles + mantenimiento + barrio ---
    df = pd.merge(arboles, mantenimiento, on="id_arbol", how="left")

    return arboles, mantenimiento, barrios, df


st.sidebar.header("📂 Datos de entrada")
modo = st.sidebar.radio("Origen de los datos", ["Usar archivos locales del repo", "Subir archivos"])

if modo == "Subir archivos":
    file_arboles = st.sidebar.file_uploader("arboles.csv", type="csv")
    file_mantenimiento = st.sidebar.file_uploader("Seguimiento_Arboles.csv", type="csv")
    file_barrios = st.sidebar.file_uploader("barrios_de_la_ciudad.csv", type="csv")
else:
    file_arboles = "arboles.csv"
    file_mantenimiento = "Seguimiento_Arboles.csv"
    file_barrios = "barrios_de_la_ciudad.csv"

if not (file_arboles and file_mantenimiento and file_barrios):
    st.info("⬅️ Cargá los tres archivos CSV desde la barra lateral para ver el tablero.")
    st.stop()

try:
    arboles, mantenimiento, barrios, df = cargar_datos(file_arboles, file_mantenimiento, file_barrios)
except Exception as e:
    st.error(f"No se pudieron cargar/procesar los datos: {e}")
    st.stop()


# ==========================================================
# 1.b Cobertura y actualidad del padrón (indicadores globales,
#      NO dependen de los filtros de barrio: reflejan todo el dataset)
# ==========================================================
st.markdown("### 📊 Cobertura y actualidad del padrón")

total_arboles_catastro = len(arboles)
arboles_geo = int(arboles["nombre_barrio"].notna().sum())
pct_geo = (arboles_geo / total_arboles_catastro * 100) if total_arboles_catastro else 0

total_barrios = len(barrios)
barrios_con_reg = int(arboles["nombre_barrio"].dropna().nunique())

st.info(
    f"📍 **{formato_ar(arboles_geo)} de {formato_ar(total_arboles_catastro)} árboles geolocalizados "
    f"({pct_geo:.0f}%)** · **{barrios_con_reg} de {total_barrios} barrios con registros**. "
    f"Los {formato_ar(total_arboles_catastro - arboles_geo)} árboles fuera de todos los polígonos y los "
    f"{total_barrios - barrios_con_reg} barrios sin árboles registrados quedan fuera de los análisis por "
    f"barrio (exclusión acordada con la cátedra); se muestran acá para que quede explícito."
)

_mant_fechas = mantenimiento.copy()
_mant_fechas["fecha_hora"] = pd.to_datetime(_mant_fechas["fecha_hora"], errors="coerce")
_mant_fechas["prox_fecha_mante"] = pd.to_datetime(_mant_fechas["prox_fecha_mante"], errors="coerce")

_ultima_inspeccion = _mant_fechas["fecha_hora"].max()
_hoy = pd.Timestamp.now().normalize()

_programados = _mant_fechas["prox_fecha_mante"].dropna()
_n_programados = len(_programados)
_n_vencidos = int((_programados < _hoy).sum())
_pct_vencidos = (_n_vencidos / _n_programados * 100) if _n_programados else 0

st.warning(
    f"⚠️ **Padrón desactualizado.** El último seguimiento registrado es del "
    f"**{_ultima_inspeccion.strftime('%d/%m/%Y') if pd.notna(_ultima_inspeccion) else 's/d'}**. "
    f"De los **{formato_ar(_n_programados)}** mantenimientos con fecha programada, "
    f"**{formato_ar(_n_vencidos)} ({_pct_vencidos:.0f}%)** ya están vencidos respecto de hoy "
    f"({_hoy.strftime('%d/%m/%Y')})."
)

_por_mes = (
    _mant_fechas.dropna(subset=["fecha_hora"])
    .set_index("fecha_hora")
    .resample("MS")
    .size()
)
_fig_mes, _ax_mes = plt.subplots(figsize=(10, 3.2))
_ax_mes.plot(_por_mes.index, _por_mes.values, color=PALETA["verde_neon"], linewidth=2, marker="o", markersize=3)
_ax_mes.set_title("Registros de seguimiento por mes")
_ax_mes.set_xlabel("Mes")
_ax_mes.set_ylabel("Cantidad de registros")
_fig_mes.autofmt_xdate()
estilo_oscuro(_fig_mes, _ax_mes)
st.pyplot(_fig_mes)
st.caption(
    "Incluye todos los tipos de seguimiento (altas, mantenimiento, inspecciones, etc.). "
    "Permite ver de un vistazo cuándo se frenó el relevamiento en campo."
)

st.divider()

# ==========================================================
# 2. Filtros globales
# ==========================================================
st.sidebar.header("🔎 Filtros globales")
barrios_disponibles = sorted(arboles["nombre_barrio"].dropna().unique())
barrios_sel = st.sidebar.multiselect("Barrios a incluir", options=barrios_disponibles, default=barrios_disponibles)

arboles_f = arboles[arboles["nombre_barrio"].isin(barrios_sel)]
df_f = df[df["nombre_barrio"].isin(barrios_sel)]

col1, col2, col3, col4 = st.columns(4)
col1.metric("Árboles inventariados", f"{len(arboles_f):,}")
col2.metric("Especies distintas", f"{arboles_f['especie'].nunique()}")
col3.metric("Barrios seleccionados", f"{len(barrios_sel)}")
col4.metric("Registros de mantenimiento", f"{df_f['id_seguimiento'].notna().sum():,}")

st.divider()

tabs = st.tabs(
    [
        "📋 EDA general",
        "🗺️ Distribución espacial",
        "🌳 Barrios con más árboles",
        "🛠️ Tipos de mantenimiento",
        "🧭 Zona Norte / Sur",
        "📊 Riesgo vs. otras variables",
        "🚨 Necesidad de intervención",
        "🔬 Análisis MCA",
        "📋 Indicadores por barrio",
    ]
)

# ----------------------------------------------------------
# TAB 0: EDA general
# ----------------------------------------------------------
with tabs[0]:
    st.subheader("Exploración general del arbolado")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Especies más frecuentes**")
        top_especies = arboles_f["especie"].value_counts().head(10)
        st.bar_chart(top_especies, color=PALETA["verde_neon"])
    with c2:
        st.markdown("**Tipo de vereda**")
        st.bar_chart(arboles_f["tipo_vereda"].value_counts(), color=PALETA["azul"])

    c3, c4 = st.columns(2)
    with c3:
        st.markdown("**Lado de vereda**")
        st.bar_chart(arboles_f["lado_vereda"].value_counts(), color=PALETA["amarillo"])
    with c4:
        st.markdown("**Árboles activos**")
        st.bar_chart(arboles_f["activo"].value_counts(), color=PALETA["verde_oscuro"])

    if st.checkbox("Ver estadísticas descriptivas completas (describe)"):
        st.dataframe(arboles_f.describe(include="all"))

    st.caption(
        f"Duplicados detectados: {arboles_f.duplicated().sum()} · "
        f"Valores nulos totales: {int(arboles_f.isna().sum().sum())}"
    )

# ----------------------------------------------------------
# TAB 1: Distribución espacial
# ----------------------------------------------------------
with tabs[1]:
    st.subheader("Distribución espacial del arbolado urbano")

    st.markdown("**Densidad de arbolado por barrio (árboles por hectárea)**")
    st.caption(
        "Reemplaza el mapa de puntos: con miles de árboles superpuestos los puntos no se leen; "
        "el polígono coloreado por densidad sí."
    )

    _conteo_barrio = arboles_f["nombre_barrio"].value_counts()
    _sup_ha = barrios.set_index("nombre_barrio")["sup_ha"]
    _densidad_barrio = (
        _conteo_barrio.reindex(_sup_ha.index).fillna(0) / _sup_ha
    ).replace([np.inf, -np.inf], np.nan)

    fig_choro = dibujar_choropleta(
        barrios,
        _densidad_barrio,
        titulo="Árboles por hectárea, por barrio",
        etiqueta_barra="Árboles / ha",
    )
    st.pyplot(fig_choro)
    st.caption("Barrios en gris: sin superficie registrada o sin árboles del padrón asignados en la selección actual.")

    st.markdown("**Mapa de densidad puntual (equivalente al heatmap del notebook)**")
    fig, ax = plt.subplots(figsize=(8, 7))
    hb = ax.hexbin(arboles_f["lng"], arboles_f["lat"], gridsize=40, cmap="viridis", mincnt=1)
    ax.set_xlabel("Longitud")
    ax.set_ylabel("Latitud")
    ax.set_title("Densidad de árboles por zona")
    cbar = fig.colorbar(hb, ax=ax, label="Cantidad de árboles")
    cbar.ax.yaxis.label.set_color(PALETA["texto"])
    cbar.ax.tick_params(colors=PALETA["texto"])
    estilo_oscuro(fig, ax)
    st.pyplot(fig)

# ----------------------------------------------------------
# TAB 2: Barrios con más árboles
# ----------------------------------------------------------
with tabs[2]:
    st.subheader("¿Qué barrios tienen más árboles plantados?")

    top_n = st.slider("Cantidad de barrios a mostrar", 5, 30, 15, key="topn_barrios")
    arboles_por_barrio = arboles_f["nombre_barrio"].value_counts().head(top_n)
    # st.bar_chart sobre una Series ordena el eje por índice (alfabético), no por valor:
    # con un ranking eso hace que el gráfico no responda la pregunta del título.
    st.pyplot(
        grafico_ranking_horizontal(
            arboles_por_barrio, PALETA["verde_neon"],
            "Barrios con más árboles plantados", "Cantidad de árboles"
        )
    )

    if not arboles_por_barrio.empty:
        st.success(
            f"El barrio con más árboles plantados es **{arboles_por_barrio.index[0]}** "
            f"con **{arboles_por_barrio.iloc[0]}** árboles."
        )

    if st.checkbox("Ver tabla completa por barrio"):
        st.dataframe(
            arboles_f["nombre_barrio"].value_counts().rename_axis("Barrio").reset_index(name="Cantidad de árboles")
        )

# ----------------------------------------------------------
# TAB 3: Tipos de mantenimiento
# ----------------------------------------------------------
with tabs[3]:
    st.subheader("¿Qué tipos de mantenimiento aparecen con mayor frecuencia?")

    mant_f = mantenimiento[mantenimiento["id_arbol"].isin(arboles_f["id_arbol"])]
    frecuencia = mant_f["tipo_seguimiento"].value_counts()
    porcentaje = (frecuencia / frecuencia.sum() * 100).round(2)

    st.pyplot(
        grafico_ranking_horizontal(
            frecuencia, PALETA["amarillo"],
            "Tipos de mantenimiento más frecuentes", "Cantidad de registros"
        )
    )

    if not frecuencia.empty:
        st.success(
            f"El tipo de mantenimiento más frecuente es **'{frecuencia.index[0]}'** "
            f"con **{frecuencia.iloc[0]}** registros ({porcentaje.iloc[0]:.1f}% del total)."
        )

    if st.checkbox("Ver tabla de frecuencia y porcentaje"):
        st.dataframe(pd.DataFrame({"Frecuencia": frecuencia, "Porcentaje": porcentaje}))

# ----------------------------------------------------------
# TAB 4: Zona Norte / Sur
# ----------------------------------------------------------
with tabs[4]:
    st.subheader("Distribución del arbolado por zona (Norte / Sur)")
    st.caption(
        "Se usa como línea divisoria la latitud del cruce Av. 3 de Abril y Rioja "
        "(límite sur del casco histórico), igual que en el notebook."
    )

    lat_divisoria = st.slider("Latitud divisoria", -27.50, -27.44, -27.472, step=0.001, format="%.3f")

    df_zona = df_f.copy()
    df_zona["zona"] = df_zona["lat"].apply(lambda x: "Zona Norte" if x >= lat_divisoria else "Zona Sur")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Cantidad de árboles por zona**")
        st.bar_chart(df_zona["zona"].value_counts(), color=PALETA["verde_neon"])

    with c2:
        fig, ax = plt.subplots(figsize=(6, 5))
        colores = {"Zona Norte": PALETA["verde_neon"], "Zona Sur": PALETA["naranja"]}
        for zona, color in colores.items():
            datos = df_zona[df_zona["zona"] == zona]
            ax.scatter(datos["lng"], datos["lat"], s=6, alpha=0.5, label=zona, color=color)
        ax.axhline(y=lat_divisoria, color=PALETA["amarillo"], linestyle="--", linewidth=2, label="Línea divisoria")
        ax.set_xlabel("Longitud")
        ax.set_ylabel("Latitud")
        ax.legend()
        estilo_oscuro(fig, ax)
        st.pyplot(fig)

    variable_zona = st.selectbox(
        "Ver distribución de zona vs.",
        ["riesgo", "estado_salud", "levantamiento_vereda", "ahuecamiento", "inclinacion"],
    )
    st.dataframe(pd.crosstab(df_zona["zona"], df_zona[variable_zona]))

# ----------------------------------------------------------
# TAB 5: Riesgo vs. otras variables (bivariado + chi2)
# ----------------------------------------------------------
with tabs[5]:
    st.subheader("Análisis bivariado: riesgo según otras variables")

    variable = st.selectbox(
        "Elegí la variable a cruzar con 'riesgo'",
        ["estado_salud", "inclinacion", "ahuecamiento", "levantamiento_vereda", "fase_vital"],
    )

    tabla_cruzada = pd.crosstab(df_f["riesgo"], df_f[variable])
    st.dataframe(tabla_cruzada)

    fig, ax = plt.subplots(figsize=(8, 5))
    tabla_cruzada.plot(kind="bar", stacked=True, ax=ax, color=PALETA_VIVA[: len(tabla_cruzada.columns)])
    ax.set_title(f"Riesgo según {variable}")
    ax.set_xlabel("Nivel de riesgo")
    ax.set_ylabel("Cantidad de árboles")
    estilo_oscuro(fig, ax)
    st.pyplot(fig)

    try:
        chi2, p, gl, esperados = chi2_contingency(tabla_cruzada)
        st.markdown(f"**Chi-cuadrado:** {chi2:.2f}  |  **Grados de libertad:** {gl}  |  **Valor p:** {p:.6f}")
        if p < 0.05:
            st.info(
                f"Como el valor p ({p:.6f}) es menor a 0.05, se rechaza la hipótesis nula de independencia: "
                f"existe una asociación estadísticamente significativa entre **riesgo** y **{variable}**."
            )
        else:
            st.info(
                f"Como el valor p ({p:.6f}) no es menor a 0.05, no hay evidencia suficiente de asociación "
                f"entre **riesgo** y **{variable}**."
            )
    except Exception as e:
        st.warning(f"No se pudo calcular el chi-cuadrado para esta combinación: {e}")

# ----------------------------------------------------------
# TAB 6: Necesidad de intervención por barrio
# ----------------------------------------------------------
with tabs[6]:
    st.subheader("¿Hay barrios con mayor necesidad de intervención?")

    # --- 1) Estado ACTUAL de cada árbol: último seguimiento por fecha_hora ---
    # df_f trae una fila por combinación árbol×seguimiento (10.388 filas), no una por árbol
    # (10.286). Hay árboles con más de un seguimiento y con riesgo distinto entre registros:
    # para no duplicar/promediar estados viejos, nos quedamos con el más reciente por árbol.
    st.caption(
        "El índice se calcula sobre el **último seguimiento de cada árbol** (su estado actual), "
        "no sobre la tabla cruzada árbol×seguimiento, para no contar dos veces a los árboles "
        "con más de un registro."
    )

    df_estado = df_f.copy()
    df_estado["fecha_hora"] = pd.to_datetime(df_estado["fecha_hora"], errors="coerce")
    df_estado = (
        df_estado.sort_values("fecha_hora", na_position="first")
        .drop_duplicates(subset="id_arbol", keep="last")
    )

    min_arboles = st.slider("Mínimo de árboles por barrio para considerarlo", 0, 100, 30)

    # --- 2) Indicadores de intervención ---
    # "Con riesgo de caída (alto)" son apenas ~78 registros en TODO el dataset: como numerador
    # de un porcentaje por barrio es ruido, incluso con un mínimo de 30 árboles. Mientras tanto,
    # "Árbol parasitado" (miles de registros) y el conflicto con la vereda (miles de registros)
    # quedaban completamente afuera del índice. Se reemplaza por tres indicadores más robustos,
    # cada uno con una base de casos mucho mayor:
    #   a) riesgo estructural relevante: cualquier categoría de "riesgo" distinta de
    #      "Sin riesgo de caída" (incluye parasitosis y los distintos niveles de riesgo de caída)
    #   b) conflicto con la vereda: levantamiento_vereda en {Leve, Considerable}
    #   c) estado de salud crítico: estado_salud en {Malo, Muerto}
    estados_criticos = ["Malo", "Muerto"]

    resumen = pd.DataFrame({"total_arboles": df_estado.groupby("nombre_barrio")["id_arbol"].nunique()})

    _riesgo_relevante = df_estado["riesgo"].notna() & (df_estado["riesgo"] != "Sin riesgo de caída")
    resumen["riesgo_relevante"] = (
        df_estado[_riesgo_relevante].groupby("nombre_barrio")["id_arbol"].nunique()
    )
    resumen["riesgo_relevante"] = resumen["riesgo_relevante"].fillna(0).astype(int)
    resumen["pct_riesgo_relevante"] = (resumen["riesgo_relevante"] / resumen["total_arboles"] * 100).round(2)

    _conflicto_vereda = df_estado["levantamiento_vereda"].isin(["Considerable", "Leve"])
    resumen["conflicto_vereda"] = (
        df_estado[_conflicto_vereda].groupby("nombre_barrio")["id_arbol"].nunique()
    )
    resumen["conflicto_vereda"] = resumen["conflicto_vereda"].fillna(0).astype(int)
    resumen["pct_conflicto_vereda"] = (resumen["conflicto_vereda"] / resumen["total_arboles"] * 100).round(2)

    resumen["estado_critico"] = (
        df_estado[df_estado["estado_salud"].isin(estados_criticos)].groupby("nombre_barrio")["id_arbol"].nunique()
    )
    resumen["estado_critico"] = resumen["estado_critico"].fillna(0).astype(int)
    resumen["pct_estado_critico"] = (resumen["estado_critico"] / resumen["total_arboles"] * 100).round(2)

    resumen["indice_intervencion"] = (
        resumen["pct_riesgo_relevante"] + resumen["pct_conflicto_vereda"] + resumen["pct_estado_critico"]
    ) / 3

    # Densidad (árboles/ha) para el scatter de abajo
    resumen = resumen.merge(
        barrios[["nombre_barrio", "sup_ha"]], left_index=True, right_on="nombre_barrio", how="left"
    ).set_index("nombre_barrio")
    resumen["densidad_ha"] = (resumen["total_arboles"] / resumen["sup_ha"]).round(2)

    resumen_final = resumen[resumen["total_arboles"] >= min_arboles].sort_values(
        "indice_intervencion", ascending=False
    )

    top_n_interv = st.slider("Cantidad de barrios a mostrar", 5, 30, 15, key="topn_interv")
    top_interv = resumen_final.head(top_n_interv)
    st.pyplot(
        grafico_ranking_horizontal(
            top_interv["indice_intervencion"], PALETA["rojo"],
            "Barrios con mayor índice de intervención", "Índice de intervención (%)"
        )
    )

    if not top_interv.empty:
        st.warning(
            f"El barrio con mayor necesidad de intervención es **{top_interv.index[0]}**, "
            f"con un índice de {top_interv['indice_intervencion'].iloc[0]:.1f}% "
            f"({top_interv['pct_riesgo_relevante'].iloc[0]:.1f}% con riesgo estructural relevante, "
            f"{top_interv['pct_conflicto_vereda'].iloc[0]:.1f}% con conflicto de vereda y "
            f"{top_interv['pct_estado_critico'].iloc[0]:.1f}% en estado de salud crítico)."
        )

    if st.checkbox("Ver tabla completa de intervención por barrio"):
        st.dataframe(resumen_final)

    st.markdown("---")
    st.markdown("**Densidad de arbolado vs. estado crítico, por barrio**")
    st.caption(
        "Mucho arbolado en mal estado es prioridad de intervención; poco arbolado y sano es "
        "oportunidad de plantar. Los cuadrantes se separan por la mediana de cada eje."
    )

    _disp = resumen_final.dropna(subset=["densidad_ha", "pct_estado_critico"])
    if len(_disp) >= 2:
        med_x, med_y = _disp["densidad_ha"].median(), _disp["pct_estado_critico"].median()

        fig_sc, ax_sc = plt.subplots(figsize=(8, 6))
        ax_sc.scatter(
            _disp["densidad_ha"], _disp["pct_estado_critico"],
            s=60, color=PALETA["rojo"], edgecolors="white", linewidths=0.5, alpha=0.85,
        )
        for nombre, fila in _disp.iterrows():
            ax_sc.annotate(
                nombre, (fila["densidad_ha"], fila["pct_estado_critico"]),
                fontsize=7, color=PALETA["texto"], xytext=(4, 4), textcoords="offset points",
            )
        ax_sc.axvline(med_x, color=PALETA["amarillo"], linestyle="--", linewidth=1.2, alpha=0.8)
        ax_sc.axhline(med_y, color=PALETA["amarillo"], linestyle="--", linewidth=1.2, alpha=0.8)
        ax_sc.set_xlabel("Densidad (árboles / hectárea)")
        ax_sc.set_ylabel("% de árboles en estado crítico (Malo/Muerto)")
        ax_sc.set_title("Densidad de arbolado vs. estado crítico")
        estilo_oscuro(fig_sc, ax_sc)
        st.pyplot(fig_sc)
        st.caption(
            "Cuadrante superior derecho (alta densidad + alto % crítico): prioridad de intervención. "
            "Cuadrante inferior izquierdo (baja densidad + bajo % crítico): oportunidad de plantar."
        )
    else:
        st.info("No hay suficientes barrios con datos de superficie/estado crítico para el scatter con este filtro.")

# ----------------------------------------------------------
# TAB 7: Análisis de Correspondencias Múltiples (MCA)
# ----------------------------------------------------------
with tabs[7]:
    st.subheader("Análisis de Correspondencias Múltiples (MCA)")
    st.caption(
        "Visualiza conjuntamente las variables categóricas relacionadas con el estado y riesgo del arbolado."
    )

    try:
        import prince

        variables_mca = df_f[
            ["riesgo", "estado_salud", "inclinacion", "ahuecamiento", "levantamiento_vereda", "fase_vital"]
        ].dropna()

        if len(variables_mca) < 10:
            st.info("No hay suficientes registros con los filtros actuales para calcular el MCA.")
        else:
            mca = prince.MCA(n_components=2, random_state=42)
            mca = mca.fit(variables_mca)

            coord = mca.column_coordinates(variables_mca)
            varianza = mca.eigenvalues_summary if hasattr(mca, "eigenvalues_summary") else None

            colores_mca = {
                "riesgo": PALETA["rojo"],
                "estado_salud": PALETA["azul"],
                "inclinacion": PALETA["verde_neon"],
                "ahuecamiento": PALETA["amarillo"],
                "levantamiento_vereda": "#D500F9",
                "fase_vital": PALETA["naranja"],
            }

            fig, ax = plt.subplots(figsize=(10, 8))
            for nombre in coord.index:
                var_base = nombre.split("__")[0] if "__" in nombre else nombre
                color = colores_mca.get(var_base, PALETA["texto"])
                ax.scatter(coord.loc[nombre, 0], coord.loc[nombre, 1], color=color, s=70, edgecolors="white", linewidths=0.5)
                ax.text(coord.loc[nombre, 0] + 0.02, coord.loc[nombre, 1] + 0.02, nombre, fontsize=8, color=PALETA["texto"])

            ax.axhline(0, color=PALETA["texto"], linestyle="--", alpha=0.4)
            ax.axvline(0, color=PALETA["texto"], linestyle="--", alpha=0.4)
            ax.set_xlabel("Dimensión 1")
            ax.set_ylabel("Dimensión 2")
            ax.set_title("MCA - Categorías de variables del arbolado")
            estilo_oscuro(fig, ax)
            st.pyplot(fig)

            st.markdown("**Autovalores (varianza explicada):**")
            st.write(mca.eigenvalues_)

    except ImportError:
        st.warning(
            "La librería `prince` no está instalada en este entorno. "
            "Agregá `prince` a requirements.txt para habilitar esta pestaña."
        )
    except Exception as e:
        st.error(f"No se pudo calcular el MCA: {e}")


# ----------------------------------------------------------
# TAB 8: Indicadores por barrio
# ----------------------------------------------------------
def _shannon(serie_especies):
    conteos = serie_especies.value_counts()
    total = conteos.sum()
    if total == 0:
        return np.nan
    proporciones = conteos / total
    return float(-(proporciones * np.log(proporciones)).sum())


with tabs[8]:
    st.subheader("Indicadores por barrio")

    _sup_ha_orig = barrios.attrs.get("sup_ha_original")
    if _sup_ha_orig is not None:
        _idx_ejemplo = _sup_ha_orig.astype(str).str.count(r"\.").idxmax()
        st.caption(
            f"⚠️ `sup_ha` venía con el separador de miles mal puesto — ej. barrio "
            f"**{barrios.loc[_idx_ejemplo, 'nombre_barrio']}**: "
            f"`{_sup_ha_orig.loc[_idx_ejemplo]}` → **{barrios.loc[_idx_ejemplo, 'sup_ha']:.2f} ha** "
            f"reparado. Se corrige automáticamente al cargar los datos, antes de calcular densidad."
        )

    min_arboles_ind = st.slider("Mínimo de árboles por barrio para considerarlo", 0, 100, 30, key="min_ind")

    # --- Base: un árbol = una fila, y su último seguimiento (estado actual) ---
    df_estado_ind = df_f.copy()
    df_estado_ind["fecha_hora"] = pd.to_datetime(df_estado_ind["fecha_hora"], errors="coerce")
    df_estado_ind["prox_fecha_mante"] = pd.to_datetime(df_estado_ind["prox_fecha_mante"], errors="coerce")
    df_estado_ind = (
        df_estado_ind.sort_values("fecha_hora", na_position="first")
        .drop_duplicates(subset="id_arbol", keep="last")
    )

    hoy = pd.Timestamp.now().normalize()

    resumen_ind = pd.DataFrame({"total_arboles": arboles_f["nombre_barrio"].value_counts()})
    resumen_ind = resumen_ind.merge(
        barrios[["nombre_barrio", "sup_ha"]], left_index=True, right_on="nombre_barrio", how="left"
    ).set_index("nombre_barrio")

    # 1) Árboles por hectárea
    resumen_ind["densidad_ha"] = (resumen_ind["total_arboles"] / resumen_ind["sup_ha"]).round(2)

    # 2) Mantenimiento vencido: prox_fecha_mante < hoy
    _vencido = df_estado_ind["prox_fecha_mante"].notna() & (df_estado_ind["prox_fecha_mante"] < hoy)
    resumen_ind["mantenimiento_vencido"] = (
        df_estado_ind[_vencido].groupby("nombre_barrio")["id_arbol"].nunique()
    )
    resumen_ind["mantenimiento_vencido"] = resumen_ind["mantenimiento_vencido"].fillna(0).astype(int)
    resumen_ind["pct_mantenimiento_vencido"] = (
        resumen_ind["mantenimiento_vencido"] / resumen_ind["total_arboles"] * 100
    ).round(2)

    # 3) Conflicto con vereda
    _conflicto = df_estado_ind["levantamiento_vereda"].isin(["Considerable", "Leve"])
    resumen_ind["conflicto_vereda"] = (
        df_estado_ind[_conflicto].groupby("nombre_barrio")["id_arbol"].nunique()
    )
    resumen_ind["conflicto_vereda"] = resumen_ind["conflicto_vereda"].fillna(0).astype(int)
    resumen_ind["pct_conflicto_vereda"] = (
        resumen_ind["conflicto_vereda"] / resumen_ind["total_arboles"] * 100
    ).round(2)

    # 4) Árboles parasitados: cualquier categoría de 'riesgo' que empiece con "Arbol parasitado"
    _parasitado = df_estado_ind["riesgo"].str.startswith("Arbol parasitado", na=False)
    resumen_ind["parasitados"] = (
        df_estado_ind[_parasitado].groupby("nombre_barrio")["id_arbol"].nunique()
    )
    resumen_ind["parasitados"] = resumen_ind["parasitados"].fillna(0).astype(int)
    resumen_ind["pct_parasitados"] = (
        resumen_ind["parasitados"] / resumen_ind["total_arboles"] * 100
    ).round(2)

    # 5) Antigüedad del relevamiento: hoy - último fecha_hora, por barrio
    _ultima_por_barrio = df_estado_ind.groupby("nombre_barrio")["fecha_hora"].max()
    resumen_ind["ultima_inspeccion"] = _ultima_por_barrio
    resumen_ind["dias_desde_ultima_inspeccion"] = (hoy - resumen_ind["ultima_inspeccion"]).dt.days

    # árboles sin NINGÚN seguimiento: un barrio "sin datos" no es lo mismo que un barrio sano
    _sin_seguimiento = df_estado_ind["fecha_hora"].isna()
    resumen_ind["sin_seguimiento"] = (
        df_estado_ind[_sin_seguimiento].groupby("nombre_barrio")["id_arbol"].nunique()
    )
    resumen_ind["sin_seguimiento"] = resumen_ind["sin_seguimiento"].fillna(0).astype(int)
    resumen_ind["pct_sin_seguimiento"] = (
        resumen_ind["sin_seguimiento"] / resumen_ind["total_arboles"] * 100
    ).round(2)

    # 6) Diversidad de especies: índice de Shannon + % de la especie dominante
    resumen_ind["diversidad_shannon"] = (
        arboles_f.groupby("nombre_barrio")["especie"].apply(_shannon).round(2)
    )
    resumen_ind["especie_dominante"] = arboles_f.groupby("nombre_barrio")["especie"].agg(
        lambda s: s.value_counts().idxmax() if len(s) else np.nan
    )
    resumen_ind["pct_especie_dominante"] = (
        arboles_f.groupby("nombre_barrio")["especie"].apply(
            lambda s: s.value_counts(normalize=True).max() * 100 if len(s) else np.nan
        )
    ).round(2)

    # 7) Índice de intervención v2: compuesto de 5 señales sobre el último seguimiento
    #    (riesgo, estado_salud, ahuecamiento, inclinación, fase_vital=Añoso), no solo "riesgo alto"
    df_estado_ind["flag_riesgo"] = (
        df_estado_ind["riesgo"].notna() & (df_estado_ind["riesgo"] != "Sin riesgo de caída")
    )
    df_estado_ind["flag_salud"] = df_estado_ind["estado_salud"].isin(["Malo", "Muerto"])
    df_estado_ind["flag_ahuecamiento"] = (
        df_estado_ind["ahuecamiento"].notna() & (df_estado_ind["ahuecamiento"] != "No")
    )
    df_estado_ind["flag_inclinacion"] = (
        df_estado_ind["inclinacion"].notna() & (df_estado_ind["inclinacion"] != "Sin inclinación")
    )
    df_estado_ind["flag_anoso"] = df_estado_ind["fase_vital"] == "Añoso"

    _flags = ["flag_riesgo", "flag_salud", "flag_ahuecamiento", "flag_inclinacion", "flag_anoso"]
    df_estado_ind["score_interv_v2"] = df_estado_ind[_flags].sum(axis=1) / len(_flags) * 100

    resumen_ind["indice_intervencion_v2"] = (
        df_estado_ind.groupby("nombre_barrio")["score_interv_v2"].mean().round(2)
    )

    resumen_ind_final = resumen_ind[resumen_ind["total_arboles"] >= min_arboles_ind].sort_values(
        "indice_intervencion_v2", ascending=False
    )

    st.markdown("**Índice de intervención v2** (riesgo + estado de salud + ahuecamiento + inclinación + añosidad)")
    st.caption(
        "Cada árbol suma 1 de 5 puntos por cada señal de riesgo presente en su último seguimiento; "
        "el índice del barrio es el promedio de esos puntos (0-100%). Al combinar cinco dimensiones "
        "en vez de depender de una sola categoría de ~78 casos, el ranking deja de moverse por ruido."
    )
    top_n_ind = st.slider("Cantidad de barrios a mostrar", 5, 30, 15, key="topn_ind_v2")
    st.pyplot(
        grafico_ranking_horizontal(
            resumen_ind_final["indice_intervencion_v2"].head(top_n_ind), PALETA["rojo"],
            "Barrios con mayor índice de intervención v2", "Índice de intervención v2 (%)"
        )
    )

    _con_seguimiento = resumen_ind_final["pct_sin_seguimiento"] > 30
    if _con_seguimiento.any():
        st.warning(
            "⚠️ Los siguientes barrios tienen más del 30% de sus árboles sin ningún seguimiento "
            "registrado — su índice de intervención v2 puede estar subestimado, no reflejar que estén "
            "sanos: **"
            + ", ".join(resumen_ind_final[_con_seguimiento].index[:10])
            + "**."
        )

    st.markdown("---")
    st.markdown("**Diversidad de especies por barrio**")
    st.caption(
        "Un barrio con una sola especie dominante es vulnerable a que una plaga específica de esa "
        "especie arrase el arbolado. Mayor índice de Shannon = mayor diversidad."
    )
    _div = resumen_ind_final.sort_values("diversidad_shannon", ascending=True).head(top_n_ind)
    st.pyplot(
        grafico_ranking_horizontal(
            _div["diversidad_shannon"], PALETA["naranja"],
            "Barrios con MENOR diversidad de especies (más vulnerables)", "Índice de Shannon"
        )
    )

    st.markdown("---")
    st.markdown("**Tabla completa de indicadores por barrio**")
    columnas_tabla = [
        "total_arboles", "densidad_ha",
        "pct_mantenimiento_vencido", "pct_conflicto_vereda", "pct_parasitados",
        "dias_desde_ultima_inspeccion", "pct_sin_seguimiento",
        "diversidad_shannon", "especie_dominante", "pct_especie_dominante",
        "indice_intervencion_v2",
    ]
    st.dataframe(resumen_ind_final[columnas_tabla])
    st.caption(
        "`dias_desde_ultima_inspeccion` en blanco = el barrio no tiene ningún seguimiento con fecha "
        "válida (no es que esté sano, es que no hay dato)."
    )
