import json
import os
import re

import numpy as np
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.patches import Polygon as MplPolygon
from matplotlib.cm import ScalarMappable
from matplotlib.ticker import FuncFormatter, ScalarFormatter
from scipy.stats import chi2_contingency
import geopandas as gpd
from shapely.geometry import shape

FECHA_DESCARGA = "07/07/2026"
FECHA_DESCARGA_POBLACION = "27/10/2026"
REPO_URL = "https://github.com/Greque90/Proyecto_Arboles_Modif"
F_ARB, F_SEG, F_BAR, F_CEN = "arboles.csv", "Seguimiento_Arboles.csv", "barrios_de_la_ciudad.csv", "Densidad_Poblacional.csv"
_FUENTE = {"txt": ""}


def fuente(*archivos):
    """Fija la fuente que se escribe al pie de cada gráfico que se dibuje a continuación."""
    descarga = FECHA_DESCARGA
    if F_CEN in archivos:
        descarga = (FECHA_DESCARGA + " (población: " + FECHA_DESCARGA_POBLACION + ")") if len(archivos) > 1 else FECHA_DESCARGA_POBLACION
    _FUENTE["txt"] = (
        "Fuente: Municipalidad de Corrientes, Portal de datos abiertos ("
        + ", ".join(archivos) + "). Descarga: " + descarga + ". Elaboración propia."
    )
MIN_POBLACION_ALERTA = 500
RIESGO_ALTO = "Con riesgo de caída (alto)"

# ==========================================================
# Configuración inicial
# ==========================================================
st.set_page_config(page_title="Arbolado urbano - Corrientes Capital", layout="wide")

# Tipografía grande para proyector (gráficos de matplotlib)
plt.rcParams.update({
    "font.size": 15, "axes.titlesize": 20, "axes.titleweight": "bold", "axes.labelsize": 16,
    "xtick.labelsize": 14, "ytick.labelsize": 14, "legend.fontsize": 14, "figure.titlesize": 20,
})

# ==========================================================
# Estética: paleta de alto impacto para exposición (tema oscuro)
# ==========================================================
PALETA = {
    "fondo": "#000000",
    "fondo_secundario": "#0F2118",
    "verde_neon": "#00E676",
    "verde_oscuro": "#00C853",
    "amarillo": "#FFD600",
    "naranja": "#FF6D00",
    "rojo": "#FF1744",
    "azul": "#00B0FF",
    "texto": "#FFFFFF",
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
        font-size: 3rem;
        font-weight: 800;
        text-shadow: 0 2px 6px rgba(0,0,0,0.35);
    }}
    .encabezado-app p {{
        color: #E8FFF0 !important;
        margin-top: 0.5rem;
        margin-bottom: 0;
        font-size: 1.4rem;
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
        font-size: 2.8rem !important;
        font-weight: 800 !important;
    }}
    div[data-testid="stMetricLabel"] {{
        color: {PALETA['texto']} !important;
        opacity: 0.85;
    }}

    /* Pestañas grandes y bien visibles */
    button[data-baseweb="tab"] {{
        font-weight: 700;
        font-size: 1.4rem;
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
        font-size: 1.3rem;
    }}

    /* Fondo negro y texto grande de alto contraste (proyector) */
    .stApp {{ background-color: {PALETA['fondo']}; color: {PALETA['texto']}; }}
    section[data-testid="stSidebar"] {{ background-color: #0A140E; }}
    [data-testid="stMarkdownContainer"] p, [data-testid="stMarkdownContainer"] li {{
        font-size: 1.3rem; line-height: 1.55; color: {PALETA['texto']};
    }}
    [data-testid="stCaptionContainer"] p {{ font-size: 1.15rem !important; color: #E0F7EA !important; }}
    [data-testid="stWidgetLabel"] p {{ font-size: 1.25rem !important; color: {PALETA['texto']} !important; font-weight: 600; }}
    h2, h3 {{ font-size: 2.1rem !important; color: {PALETA['verde_neon']} !important; }}
    div[data-testid="stMetricLabel"] p {{ font-size: 1.3rem !important; }}
    div[data-testid="stMetricDelta"] {{ font-size: 1.2rem !important; }}
    [data-testid="stExpander"] summary p {{ font-size: 1.5rem !important; font-weight: 700; color: {PALETA['amarillo']} !important; }}
    [data-testid="stAlert"] p, [data-testid="stAlert"] li, [data-testid="stAlert"] strong {{ font-size: 1.3rem !important; color: #111111 !important; }}
    div[data-testid="stMetricLabel"], div[data-testid="stMetricLabel"] * {{ white-space: normal !important; overflow: visible !important; text-overflow: clip !important; -webkit-line-clamp: unset !important; display: block !important; font-size: 1.15rem !important; }}
    div[data-baseweb="select"] * {{ font-size: 1.2rem !important; }}
    section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
    section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] li {{ font-size: 1.2rem; }}
    section[data-testid="stSidebar"] h2 {{ font-size: 1.7rem !important; }}
    </style>

    <div class="encabezado-app">
        <h1>Arbolado urbano de Corrientes Capital</h1>
        <p>Fuente: los cuatro archivos fueron extraídos del Portal de datos abiertos de la
        Municipalidad de Corrientes. Descarga: {FECHA_DESCARGA} (árboles, seguimientos y barrios) y {FECHA_DESCARGA_POBLACION} (población).</p>
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
        for eje in (ax.xaxis, ax.yaxis):
            if isinstance(eje.get_major_formatter(), ScalarFormatter):
                eje.set_major_formatter(_formatter_ar(eje))
        for spine in ax.spines.values():
            spine.set_color(PALETA["texto"])
        leg = ax.get_legend()
        if leg is not None:
            leg.get_frame().set_facecolor(PALETA["fondo_secundario"])
            for text in leg.get_texts():
                text.set_color(PALETA["texto"])
    if _FUENTE["txt"]:
        import textwrap
        renderer = fig.canvas.get_renderer()
        y0 = min(a.get_tightbbox(renderer).y0 for a in fig.axes) / (fig.dpi * fig.get_figheight())
        fig.text(0.01, y0 - 0.015, textwrap.fill(_FUENTE["txt"], 100), ha="left", va="top",
                 fontsize=11, color="#E0F7EA", style="italic")
    return fig


def fmt_num(v, dec=0):
    """Formato argentino: punto para los miles, coma para los decimales (9.669 / 94,0)."""
    if v is None or pd.isna(v):
        return "—"
    return f"{v:,.{dec}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_pct(v, dec=1):
    return "—" if v is None or pd.isna(v) else f"{fmt_num(v, dec)}%"


formato_ar = fmt_num


def _formatter_ar(eje):
    ticks = np.asarray(eje.get_majorticklocs(), dtype=float)
    dec = 0
    if len(ticks) > 1 and np.min(np.abs(np.diff(ticks))) > 0:
        dec = int(min(4, max(0, np.ceil(-np.log10(np.min(np.abs(np.diff(ticks)))) - 1e-9))))
    return FuncFormatter(lambda v, _: fmt_num(v, dec))


def formatear_df(d):
    """Tablas con formato argentino (los números de st.dataframe dependen del navegador)."""
    d = d.copy()
    for c in d.columns:
        s = d[c]
        if pd.api.types.is_bool_dtype(s):
            d[c] = s.map({True: "Sí", False: "No"})
        elif pd.api.types.is_datetime64_any_dtype(s):
            d[c] = s.dt.strftime("%d/%m/%Y").fillna("—")
        elif pd.api.types.is_numeric_dtype(s):
            v = s.dropna()
            ent = len(v) == 0 or bool((v % 1 == 0).all())
            d[c] = s.map(lambda x, ent=ent: "—" if pd.isna(x) else fmt_num(x, 0 if ent else 2))
    return d


def mostrar(d):
    st.dataframe(formatear_df(d))


_CONECTORES = {"de", "del", "la", "las", "los", "el", "y"}
_ROMANO = re.compile(r"^(?=[IVXLC])(X{0,3})(IX|IV|V?I{0,3})$")


def _capitalizar(parte):
    parte = parte.lower()
    for k, c in enumerate(parte):
        if c.isalpha():
            return parte[:k] + c.upper() + parte[k + 1:]
    return parte


def normalizar_nombre_barrio(nombre):
    """Un solo criterio de mayúsculas: «17 DE agosto» -> «17 de Agosto»."""
    if not isinstance(nombre, str):
        return nombre
    out = []
    for k, w in enumerate(nombre.strip().split()):
        if _ROMANO.match(w.upper()):
            out.append(w.upper())
        elif k > 0 and w.lower() in _CONECTORES:
            out.append(w.lower())
        else:
            out.append("-".join(_capitalizar(x) for x in w.split("-")))
    return " ".join(out)


def estado_actual(df_in):
    """Una fila por árbol: su último seguimiento según fecha_hora."""
    d = df_in.copy()
    d["fecha_hora"] = pd.to_datetime(d["fecha_hora"], errors="coerce")
    d["prox_fecha_mante"] = pd.to_datetime(d["prox_fecha_mante"], errors="coerce")
    return d.sort_values("fecha_hora", na_position="first").drop_duplicates(subset="id_arbol", keep="last")


def senales_intervencion(d):
    """Índice v2: 5 señales de deterioro; requiere intervención con 2 o más."""
    d = d.copy()
    d["senal_riesgo_alto"] = d["riesgo"] == RIESGO_ALTO
    d["senal_estado_critico"] = d["estado_salud"].isin(["Malo", "Muerto"])
    d["senal_ahuecamiento"] = d["ahuecamiento"].isin(["Alto", "Mayor al 50% del diámetro del tronco"])
    d["senal_inclinacion"] = d["inclinacion"] == "Pronunciado"
    d["senal_fase_anosa"] = d["fase_vital"].isin(["Añoso", "Decrepito"])
    cols = ["senal_riesgo_alto", "senal_estado_critico", "senal_ahuecamiento", "senal_inclinacion", "senal_fase_anosa"]
    d["requiere_intervencion"] = d[cols].sum(axis=1) >= 2
    d["conflicto_vereda"] = d["levantamiento_vereda"].isin(["Considerable", "Leve"])
    d["parasitado"] = d["riesgo"].str.contains("Arbol parasitado", na=False)
    return d


def sup_ha_por_barrio(barrios_df):
    """
    Superficie por nombre_barrio (ha), calculada desde la geometría proyectada a EPSG:32721.
    Los polígonos duplicados (Collantes, Molina Punta) ya vienen unidos desde la carga.
    """
    return barrios_df.groupby("nombre_barrio")["sup_ha"].sum()


def grafico_ranking_horizontal(serie, color, titulo, xlabel):
    """
    Barras horizontales ordenadas de mayor a menor, con el valor más alto arriba.
    st.bar_chart sobre una Series ordena el eje por índice (alfabético), no por valor,
    así que para un ranking usamos matplotlib con orden explícito.
    """
    serie_ordenada = serie.sort_values(ascending=True)  # ascending: barh dibuja de abajo hacia arriba
    fig, ax = plt.subplots(figsize=(9, max(3, 0.55 * len(serie_ordenada))))
    ax.barh(serie_ordenada.index.astype(str), serie_ordenada.values, color=color)
    ax.set_xlabel(xlabel)
    ax.set_title(titulo)
    for i, v in enumerate(serie_ordenada.values):
        ax.text(v, i, " " + fmt_num(v, 0 if float(v).is_integer() else (2 if abs(v) < 10 else 1)),
                va="center", fontsize=13, color=PALETA["texto"])
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


def mapa_barrios_interactivo(barrios_geo, densidad, conteo, pct_interv=None, min_arboles=30):
    """Mapa coroplético sobre OpenStreetMap: al pasar el cursor por un barrio se muestra su nombre,
    su densidad (árboles por ha) y los árboles registrados. Los barrios sin dato se dibujan en gris."""
    import plotly.graph_objects as go
    from shapely.geometry import mapping

    b = barrios_geo.drop_duplicates("nombre_barrio")
    geo = {
        "type": "FeatureCollection",
        "features": [
            {"type": "Feature", "id": fila["nombre_barrio"], "properties": {}, "geometry": mapping(fila["geometry"])}
            for _, fila in b.iterrows()
        ],
    }
    dens = densidad.replace([np.inf, -np.inf], np.nan)
    dens = dens[~dens.index.duplicated()].reindex(b["nombre_barrio"])
    cont = conteo.reindex(b["nombre_barrio"]).fillna(0)
    con_dato = dens.notna() & (cont > 0)
    # % que requiere intervención: solo con un mínimo de árboles (si no, el porcentaje es ruido)
    pct = (pct_interv.reindex(b["nombre_barrio"]) if pct_interv is not None
           else pd.Series(np.nan, index=b["nombre_barrio"]))
    pct_txt = pd.Series(
        [fmt_pct(p) if (pd.notna(p) and c >= min_arboles) else f"sin dato (menos de {min_arboles} árboles)"
         for p, c in zip(pct, cont)],
        index=b["nombre_barrio"],
    )

    Mapa = getattr(go, "Choroplethmap", None) or go.Choroplethmapbox
    fig = go.Figure()
    sin = dens.index[~con_dato]
    if len(sin):
        fig.add_trace(Mapa(
            geojson=geo, locations=list(sin), z=[0] * len(sin), showscale=False,
            colorscale=[[0, "#9A9A9A"], [1, "#9A9A9A"]],
            marker=dict(opacity=0.45, line=dict(width=0.5, color="#555555")),
            hovertemplate="<b>%{location}</b><br>Sin árboles registrados<extra></extra>",
        ))
    con = dens.index[con_dato]
    fig.add_trace(Mapa(
        geojson=geo, locations=list(con), z=dens[con].values, customdata=[[c, p] for c, p in zip(cont[con], pct_txt[con])],
        colorscale="YlGn", marker=dict(opacity=0.85, line=dict(width=0.6, color="#333333")),
        colorbar=dict(title=dict(text="Árboles / ha", font=dict(color="#FFFFFF", size=15)),
                      tickfont=dict(color="#FFFFFF", size=14)),
        hovertemplate=("<b>%{location}</b><br>Árboles / ha: %{z:,.1f}<br>"
                       "% que requiere intervención: %{customdata[1]}<br>"
                       "Árboles registrados: %{customdata[0]:,.0f}<extra></extra>"),
    ))
    minx, miny, maxx, maxy = limites_totales(b["geometry"])
    zoom = float(np.log2(360 * 1.7 / max(maxx - minx, (maxy - miny) * 1.5))) - 0.3
    base_mapa = dict(style="open-street-map", center=dict(lon=(minx + maxx) / 2, lat=(miny + maxy) / 2), zoom=zoom)
    clave_mapa = "map" if hasattr(go, "Choroplethmap") else "mapbox"
    fig.update_layout(
        **{clave_mapa: base_mapa},
        height=620, margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor="rgba(0,0,0,0)", separators=",.",
        hoverlabel=dict(bgcolor="#0F2118", font=dict(color="#FFFFFF", size=16)),
    )
    return fig


# ==========================================================
# 1. Carga y preparación de datos
# ==========================================================
@st.cache_data
def cargar_datos(archivo_arboles, archivo_mantenimiento, archivo_barrios):
    arboles = pd.read_csv(archivo_arboles)
    mantenimiento = pd.read_csv(archivo_mantenimiento)
    crudo = pd.read_csv(archivo_barrios)

    # Barrios: se unen (dissolve) los polígonos con id_barrios repetido en lugar de descartarlos,
    # y la superficie se mide proyectando a EPSG:32721 (no se usa la columna sup_ha del CSV).
    crudo["geometry"] = crudo["the_geom"].apply(lambda g: shape(json.loads(g)))
    gdf = gpd.GeoDataFrame(crudo[["id_barrios", "nombre_barrio", "geometry"]], geometry="geometry", crs="EPSG:4326")
    n_filas_barrios = len(gdf)
    gdf = gdf.dissolve(by="id_barrios", aggfunc="first").reset_index()
    gdf["nombre_barrio"] = gdf["nombre_barrio"].map(normalizar_nombre_barrio)
    gdf["sup_ha"] = gdf.to_crs("EPSG:32721").geometry.area / 10_000

    # Unión espacial árbol -> barrio (sjoin, within)
    ga = gpd.GeoDataFrame(arboles.copy(), geometry=gpd.points_from_xy(arboles["lng"], arboles["lat"]), crs="EPSG:4326")
    unido = gpd.sjoin(ga, gdf[["nombre_barrio", "geometry"]], how="left", predicate="within").drop_duplicates("id_arbol")
    arboles = arboles.merge(unido[["id_arbol", "nombre_barrio"]], on="id_arbol", how="left")

    # Seguimientos huérfanos: se cuantifican antes de que el merge los descarte
    n_huerfanos = int((~mantenimiento["id_arbol"].isin(arboles["id_arbol"])).sum())

    df = pd.merge(arboles, mantenimiento, on="id_arbol", how="left")

    barrios = pd.DataFrame(gdf.drop(columns="geometry"))
    barrios["geometry"] = list(gdf.geometry)
    info = {"n_huerfanos": n_huerfanos, "n_filas_barrios": n_filas_barrios}
    return arboles, mantenimiento, barrios, df, info


@st.cache_data
def poblacion_barrios(archivo_censo, archivo_barrios, _barrios):
    """Población del Censo 2010 por barrio: cada radio se reparte según la fracción de su área
    que cae en cada barrio (EPSG:32721). Supone población uniforme dentro del radio."""
    cen = pd.read_csv(archivo_censo)
    radios = gpd.GeoDataFrame(cen.drop(columns="the_geom"),
                              geometry=cen["the_geom"].apply(lambda s: shape(json.loads(s))), crs="EPSG:4326")
    inval = ~radios.geometry.is_valid
    radios.loc[inval, "geometry"] = radios.loc[inval, "geometry"].buffer(0)
    rm = radios.to_crs("EPSG:32721")
    rm["area_radio_ha"] = rm.geometry.area / 10_000
    bm = gpd.GeoDataFrame(_barrios[["nombre_barrio"]].copy(), geometry=list(_barrios["geometry"]),
                          crs="EPSG:4326").to_crs("EPSG:32721")
    inter = gpd.overlay(rm[["gid", "total_poblacion", "area_radio_ha", "geometry"]], bm,
                        how="intersection", keep_geom_type=True)
    inter["pob"] = inter["total_poblacion"] * inter.geometry.area / 10_000 / inter["area_radio_ha"]
    return inter.groupby("nombre_barrio")["pob"].sum(), {"total_censo": float(cen["total_poblacion"].sum())}


st.sidebar.header("Datos de entrada")
modo = st.sidebar.radio("Origen de los datos", ["Usar archivos locales del repo", "Subir archivos"])

if modo == "Subir archivos":
    file_arboles = st.sidebar.file_uploader("arboles.csv", type="csv")
    file_mantenimiento = st.sidebar.file_uploader("Seguimiento_Arboles.csv", type="csv")
    file_barrios = st.sidebar.file_uploader("barrios_de_la_ciudad.csv", type="csv")
    file_censo = st.sidebar.file_uploader("Densidad_Poblacional.csv (para población por barrio)", type="csv")
else:
    file_arboles = "arboles.csv"
    file_mantenimiento = "Seguimiento_Arboles.csv"
    file_barrios = "barrios_de_la_ciudad.csv"
    file_censo = "Densidad_Poblacional.csv" if os.path.exists("Densidad_Poblacional.csv") else None

if not (file_arboles and file_mantenimiento and file_barrios):
    st.info("Cargá los tres archivos CSV desde la barra lateral para ver el tablero.")
    st.stop()

try:
    arboles, mantenimiento, barrios, df, info_carga = cargar_datos(file_arboles, file_mantenimiento, file_barrios)
except Exception as e:
    st.error(f"No se pudieron cargar/procesar los datos: {e}")
    st.stop()


# ==========================================================
# 1.b Cobertura y actualidad del padrón (indicadores globales,
#      NO dependen de los filtros de barrio: reflejan todo el dataset)
# ==========================================================
st.markdown("### Cobertura y actualidad del padrón")

total_arboles_catastro = len(arboles)
arboles_geo = int(arboles["nombre_barrio"].notna().sum())
pct_geo = (arboles_geo / total_arboles_catastro * 100) if total_arboles_catastro else 0

total_barrios = len(barrios)
barrios_con_reg = int(arboles["nombre_barrio"].dropna().nunique())

st.info(
    f"**{formato_ar(arboles_geo)} de {formato_ar(total_arboles_catastro)} árboles geolocalizados "
    f"({fmt_pct(pct_geo)})** · **{barrios_con_reg} de {total_barrios} barrios con registros**. "
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
    f"**Padrón desactualizado.** El último seguimiento registrado es del "
    f"**{_ultima_inspeccion.strftime('%d/%m/%Y') if pd.notna(_ultima_inspeccion) else 's/d'}**. "
    f"De los **{formato_ar(_n_programados)}** mantenimientos con fecha programada, "
    f"**{formato_ar(_n_vencidos)} ({fmt_pct(_pct_vencidos)})** ya están vencidos respecto de hoy "
    f"({_hoy.strftime('%d/%m/%Y')})."
)

_ult_txt = _ultima_inspeccion.strftime("%d/%m/%Y") if pd.notna(_ultima_inspeccion) else "s/d"
with st.sidebar:
    st.header("Cobertura de los datos")
    st.markdown(
        f"- **Seguimientos descartados:** {formato_ar(info_carga['n_huerfanos'])} de {formato_ar(len(mantenimiento))} "
        f"({fmt_pct(info_carga['n_huerfanos'] / len(mantenimiento) * 100)}) sin árbol en el padrón.\n"
        f"- **Árboles fuera de todo polígono:** {formato_ar(total_arboles_catastro - arboles_geo)}.\n"
        f"- **Barrios sin árboles:** {formato_ar(total_barrios - barrios_con_reg)}.\n"
        f"- **Polígonos unificados:** {formato_ar(info_carga['n_filas_barrios'] - total_barrios)} (Collantes y Molina Punta)."
    )
    st.caption(f"Descarga de los datos: {FECHA_DESCARGA}; población: {FECHA_DESCARGA_POBLACION}")
    st.link_button("Código en GitHub", REPO_URL, use_container_width=True)

with st.expander("Metodología y detalles del proyecto"):
    st.link_button("Ver el código en GitHub", REPO_URL)
    st.markdown(f"""
**Proyecto.** Tablero de la Tecnicatura en Ciencia de Datos e Inteligencia Artificial, Práctica Profesionalizante II (2026).
Autoras: Dolores Guadalupe Medina y Amalia Graciela Rodríguez. Objetivo: analizar la distribución espacial y el estado del
arbolado urbano de Corrientes Capital para identificar patrones de plantación por barrio, prácticas de mantenimiento y zonas
que requieren intervención prioritaria.

**Fuentes y fechas.** Los cuatro archivos fueron extraídos del Portal de datos abiertos de la Municipalidad de Corrientes:
árboles, seguimientos y barrios el {FECHA_DESCARGA}, y población el {FECHA_DESCARGA_POBLACION}. Una descarga nueva puede traer otros números.
- `arboles.csv`: inventario de {formato_ar(total_arboles_catastro)} árboles (Aplicación de Arbolado Urbano). Publicado el 13/03/2024, actualizado el 22/09/2025.
- `Seguimiento_Arboles.csv`: {formato_ar(len(mantenimiento))} registros de seguimiento, misma fuente. Publicado el 13/03/2024, actualizado el 13/08/2025.
- `barrios_de_la_ciudad.csv`: delimitación de barrios, Dirección General de Sistemas de Información Geográfica. Actualizado el 01/10/2025.
- `Densidad_Poblacional.csv`: población por radio censal (datos del Censo 2010 del INDEC publicados en el portal). Actualizado el 01/10/2025.

**Orden de las transformaciones.**
1. Lectura de los CSV y conversión de fechas.
2. Barrios: se unen (`dissolve`) los polígonos con `id_barrios` repetido (Collantes y Molina Punta) en lugar de descartarlos: {formato_ar(info_carga['n_filas_barrios'])} filas pasan a {formato_ar(total_barrios)} barrios. Los nombres se normalizan para mostrarlos.
3. Superficie: se calcula proyectando a EPSG:32721; no se usa la columna `sup_ha` del CSV.
4. Cruce espacial árbol → barrio (`within`): {formato_ar(arboles_geo)} de {formato_ar(total_arboles_catastro)} árboles quedan dentro de algún polígono.
5. Seguimientos sin árbol en el padrón: {formato_ar(info_carga['n_huerfanos'])}, cuantificados y descartados.
6. Estado actual: último seguimiento de cada árbol según `fecha_hora` (una fila por árbol).
7. «Registro de Árbol» se excluye del análisis de mantenimiento: es el alta, no una intervención.
8. Indicadores por barrio; población por intersección de radios censales con barrios.

**Indicadores.**
- *Árboles por ha* = árboles del barrio ÷ superficie calculada (ha).
- *Intervención* = % de árboles con 2 o más señales entre: riesgo de caída alto; salud Malo o Muerto; ahuecamiento severo; inclinación Pronunciada; fase vital Añosa o Decrépita. El umbral de 2 es un criterio del equipo, no una norma. Los rankings usan barrios con un mínimo de árboles (filtro ajustable, 30 por defecto).
- *Mantenimiento vencido* = `prox_fecha_mante` anterior a hoy ({_hoy.strftime('%d/%m/%Y')}), sobre el último seguimiento.
- *Conflicto con vereda* = levantamiento de vereda Considerable o Leve. *Parasitados* = riesgo que empieza con «Arbol parasitado».
- *Antigüedad del relevamiento* = hoy − fecha del seguimiento más reciente del barrio.
- *Diversidad* = índice de Shannon H = −Σ pᵢ·ln(pᵢ), con pᵢ la proporción de cada especie en el barrio.
- *Árboles cada 1.000 habitantes* = árboles del barrio ÷ población estimada × 1.000. La población de cada radio se reparte según la fracción de su área que cae en cada barrio.
- *Prioridad de plantación*: árboles por ha por debajo de la mediana y habitantes por ha por encima de la mediana, sobre los barrios con árboles registrados y población estimada (los barrios sin árboles quedan fuera). El índice de 0 a 1 (promedio de percentiles) solo ordena.

**Análisis exploratorio y estadístico.**
- *Zona Norte / Sur*: se divide la ciudad con la latitud del cruce de Av. 3 de Abril y Rioja (−27,472, ajustable en la pestaña).
- *Riesgo vs. otras variables*: prueba de independencia chi-cuadrado entre `riesgo` y cada variable, sobre la tabla árbol × seguimiento; se considera asociación significativa con p < 0,05.
- *MCA*: análisis de correspondencias múltiples sobre riesgo, estado de salud, inclinación, ahuecamiento, levantamiento de vereda y fase vital. Las categorías que aparecen juntas en un mismo árbol quedan cerca en el plano, lo que respalda combinar esas señales en un solo índice.

**Supuestos y límites.**
- La población es del Censo 2010 y se supone uniforme dentro de cada radio: es una aproximación territorial, no el acceso individual al arbolado. Con menos de {MIN_POBLACION_ALERTA} habitantes estimados el cociente es inestable y se marca.
- La última inspección registrada es del {_ult_txt}: el estado mostrado es el de la última vez que se inspeccionó cada árbol, no necesariamente el de hoy.
- Quedan fuera {formato_ar(total_arboles_catastro - arboles_geo)} árboles sin polígono y {formato_ar(total_barrios - barrios_con_reg)} barrios sin árboles.
- La categoría `ahuecamiento` tiene valores inconsistentes en la fuente, lo que debilita su aporte al índice.
- El padrón está concentrado en pocos barrios: «pocos árboles registrados» no equivale a «pocos árboles». La prioridad de plantación señala sobre todo barrios poco relevados; confirmar con el área municipal qué barrios tienen el relevamiento completo.
- La prioridad de plantación es una orientación preliminar: antes de plantar hay que verificar veredas, servicios, espacio y especie.

**Código y reproducibilidad.**
- Repositorio: [{REPO_URL}]({REPO_URL}).
- Incluye `app.py`, los CSV (fijan la versión de datos con la que se validó el tablero), `requirements.txt`, `README.md` y `METODOLOGIA.md`.
- Para correrlo: `pip install -r requirements.txt` y luego `streamlit run app.py`. Los CSV se leen desde la raíz del repositorio o se pueden subir desde la barra lateral.
- Cada gráfico lleva escrita su fuente al pie.
""")

_por_mes = (
    _mant_fechas.dropna(subset=["fecha_hora"])
    .set_index("fecha_hora")
    .resample("MS")
    .size()
)
fuente(F_SEG)
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
st.sidebar.header("Filtros globales")
barrios_disponibles = sorted(arboles["nombre_barrio"].dropna().unique())
barrios_sel = st.sidebar.multiselect("Barrios a incluir", options=barrios_disponibles, default=barrios_disponibles)

arboles_f = arboles[arboles["nombre_barrio"].isin(barrios_sel)]
df_f = df[df["nombre_barrio"].isin(barrios_sel)]

col1, col2, col3, col4 = st.columns(4)
col1.metric("Árboles", formato_ar(len(arboles_f)))
col2.metric("Especies", f"{arboles_f['especie'].nunique()}")
col3.metric("Barrios", f"{len(barrios_sel)}")
col4.metric("Seguimientos", formato_ar(df_f['id_seguimiento'].notna().sum()))

st.divider()

tabs = st.tabs(
    [
        "EDA general",
        "Distribución espacial",
        "Barrios con más árboles",
        "Tipos de mantenimiento",
        "Zona Norte / Sur",
        "Riesgo vs. otras variables",
        "Necesidad de intervención",
        "Análisis MCA",
        "Indicadores por barrio",
        "Equidad y plantación",
    ]
)

# ----------------------------------------------------------
# TAB 0: EDA general
# ----------------------------------------------------------
with tabs[0]:
    fuente(F_ARB)
    st.subheader("Exploración general del arbolado")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Especies más frecuentes**")
        top_especies = arboles_f["especie"].value_counts().head(10)
        st.pyplot(grafico_ranking_horizontal(top_especies, PALETA["verde_neon"], "", "Cantidad"))
    with c2:
        st.markdown("**Tipo de vereda**")
        st.pyplot(grafico_ranking_horizontal(arboles_f["tipo_vereda"].value_counts(), PALETA["azul"], "", "Cantidad"))

    c3, c4 = st.columns(2)
    with c3:
        st.markdown("**Lado de vereda**")
        st.pyplot(grafico_ranking_horizontal(arboles_f["lado_vereda"].value_counts(), PALETA["amarillo"], "", "Cantidad"))
    with c4:
        st.markdown("**Árboles activos**")
        st.pyplot(grafico_ranking_horizontal(arboles_f["activo"].value_counts(), PALETA["verde_oscuro"], "", "Cantidad"))

    if st.checkbox("Ver estadísticas descriptivas completas (describe)"):
        mostrar(arboles_f.describe(include="all"))

    st.caption(
        f"Duplicados detectados: {arboles_f.duplicated().sum()} · "
        f"Valores nulos totales: {int(arboles_f.isna().sum().sum())}"
    )

# ----------------------------------------------------------
# TAB 1: Distribución espacial
# ----------------------------------------------------------
with tabs[1]:
    fuente(F_ARB, F_BAR)
    st.subheader("Distribución espacial del arbolado urbano")

    st.markdown("**Densidad de arbolado por barrio (árboles por hectárea)**")
    st.caption(
        "Reemplaza el mapa de puntos: con miles de árboles superpuestos los puntos no se leen; "
        "el polígono coloreado por densidad sí."
    )

    _conteo_barrio = arboles_f["nombre_barrio"].value_counts()
    _sup_ha = sup_ha_por_barrio(barrios)
    _densidad_barrio = (
        _conteo_barrio.reindex(_sup_ha.index).fillna(0) / _sup_ha
    ).replace([np.inf, -np.inf], np.nan)

    _est_mapa = senales_intervencion(estado_actual(df_f))
    _pct_interv = _est_mapa.groupby("nombre_barrio")["requiere_intervencion"].mean() * 100
    st.plotly_chart(
        mapa_barrios_interactivo(barrios, _densidad_barrio, _conteo_barrio, _pct_interv),
        use_container_width=True,
    )
    st.caption(
        "Pasá el cursor sobre un barrio para ver su nombre, su densidad, el % de árboles que requiere intervención "
        "(2 o más señales de deterioro; solo para barrios con 30 o más árboles, porque con menos el porcentaje es ruido) "
        "y sus árboles registrados. "
        "Barrios en gris: sin árboles del padrón asignados en la selección actual. " + _FUENTE["txt"] + " Mapa base: © OpenStreetMap contributors."
    )

    st.markdown("**Mapa de densidad puntual (equivalente al heatmap del notebook)**")
    fuente(F_ARB)
    fig, ax = plt.subplots(figsize=(8, 7))
    hb = ax.hexbin(arboles_f["lng"], arboles_f["lat"], gridsize=40, cmap="viridis", mincnt=1)
    ax.set_xlabel("Longitud")
    ax.set_ylabel("Latitud")
    ax.set_title("Densidad de árboles por zona")
    cbar = fig.colorbar(hb, ax=ax, label="Cantidad de árboles")
    cbar.ax.yaxis.label.set_color(PALETA["texto"])
    cbar.ax.tick_params(colors=PALETA["texto"]); cbar.ax.yaxis.set_major_formatter(_formatter_ar(cbar.ax.yaxis))
    estilo_oscuro(fig, ax)
    st.pyplot(fig)

# ----------------------------------------------------------
# TAB 2: Barrios con más árboles
# ----------------------------------------------------------
with tabs[2]:
    fuente(F_ARB, F_BAR)
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
            f"con **{formato_ar(arboles_por_barrio.iloc[0])}** árboles."
        )

    if st.checkbox("Ver tabla completa por barrio"):
        mostrar(
            arboles_f["nombre_barrio"].value_counts().rename_axis("Barrio").reset_index(name="Cantidad de árboles")
        )

# ----------------------------------------------------------
# TAB 3: Tipos de mantenimiento
# ----------------------------------------------------------
with tabs[3]:
    fuente(F_SEG, F_ARB)
    st.subheader("¿Qué tipos de mantenimiento aparecen con mayor frecuencia?")

    # «Registro de Arbol» es el alta del árbol en el padrón, no una tarea de mantenimiento
    mant_f = mantenimiento[
        mantenimiento["id_arbol"].isin(arboles_f["id_arbol"]) & (mantenimiento["tipo_seguimiento"] != "Registro de Arbol")
    ]
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
            f"con **{formato_ar(frecuencia.iloc[0])}** registros ({fmt_pct(porcentaje.iloc[0])} del total, sin contar «Registro de Árbol»)."
        )

    if st.checkbox("Ver tabla de frecuencia y porcentaje"):
        mostrar(pd.DataFrame({"Frecuencia": frecuencia, "Porcentaje": porcentaje}))

# ----------------------------------------------------------
# TAB 4: Zona Norte / Sur
# ----------------------------------------------------------
with tabs[4]:
    fuente(F_ARB, F_SEG)
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
        st.pyplot(grafico_ranking_horizontal(df_zona.drop_duplicates("id_arbol")["zona"].value_counts(), PALETA["verde_neon"], "", "Cantidad"))

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
    mostrar(pd.crosstab(df_zona["zona"], df_zona[variable_zona]))

# ----------------------------------------------------------
# TAB 5: Riesgo vs. otras variables (bivariado + chi2)
# ----------------------------------------------------------
with tabs[5]:
    fuente(F_ARB, F_SEG)
    st.subheader("Análisis bivariado: riesgo según otras variables")

    variable = st.selectbox(
        "Elegí la variable a cruzar con 'riesgo'",
        ["estado_salud", "inclinacion", "ahuecamiento", "levantamiento_vereda", "fase_vital"],
    )

    tabla_cruzada = pd.crosstab(df_f["riesgo"], df_f[variable])
    mostrar(tabla_cruzada)

    fig, ax = plt.subplots(figsize=(8, 5))
    tabla_cruzada.plot(kind="bar", stacked=True, ax=ax, color=PALETA_VIVA[: len(tabla_cruzada.columns)])
    ax.set_title(f"Riesgo según {variable}")
    ax.set_xlabel("Nivel de riesgo")
    ax.set_ylabel("Cantidad de árboles")
    estilo_oscuro(fig, ax)
    st.pyplot(fig)

    try:
        chi2, p, gl, esperados = chi2_contingency(tabla_cruzada)
        st.markdown(f"**Chi-cuadrado:** {fmt_num(chi2, 2)}  |  **Grados de libertad:** {gl}  |  **Valor p:** {fmt_num(p, 6)}")
        if p < 0.05:
            st.info(
                f"Como el valor p ({fmt_num(p, 6)}) es menor a 0,05, se rechaza la hipótesis nula de independencia: "
                f"existe una asociación estadísticamente significativa entre **riesgo** y **{variable}**."
            )
        else:
            st.info(
                f"Como el valor p ({fmt_num(p, 6)}) no es menor a 0,05, no hay evidencia suficiente de asociación "
                f"entre **riesgo** y **{variable}**."
            )
    except Exception as e:
        st.warning(f"No se pudo calcular el chi-cuadrado para esta combinación: {e}")

# ----------------------------------------------------------
# TAB 6: Necesidad de intervención por barrio
# ----------------------------------------------------------
with tabs[6]:
    fuente(F_ARB, F_SEG, F_BAR)
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

    df_estado = senales_intervencion(estado_actual(df_f))

    min_arboles = st.slider("Mínimo de árboles por barrio para considerarlo", 0, 100, 30)

    # Índice v2: % de árboles con 2 o más de 5 señales de deterioro (ver «Metodología»).
    # Conflicto con vereda y parasitados se muestran como indicadores propios.
    g_est = df_estado.groupby("nombre_barrio")
    resumen = pd.DataFrame({"total_arboles": g_est["id_arbol"].nunique()})
    resumen["pct_intervencion_v2"] = g_est["requiere_intervencion"].mean() * 100
    resumen["pct_conflicto_vereda"] = g_est["conflicto_vereda"].mean() * 100
    resumen["pct_parasitados"] = g_est["parasitado"].mean() * 100
    resumen["pct_estado_critico"] = g_est["senal_estado_critico"].mean() * 100

    resumen = resumen.merge(
        sup_ha_por_barrio(barrios).rename("sup_ha"), left_index=True, right_index=True, how="left"
    )
    resumen["densidad_ha"] = resumen["total_arboles"] / resumen["sup_ha"]

    resumen_final = resumen[resumen["total_arboles"] >= min_arboles].sort_values(
        "pct_intervencion_v2", ascending=False
    )

    top_n_interv = st.slider("Cantidad de barrios a mostrar", 5, 30, 15, key="topn_interv")
    top_interv = resumen_final.head(top_n_interv)
    st.pyplot(
        grafico_ranking_horizontal(
            top_interv["pct_intervencion_v2"], PALETA["rojo"],
            "Barrios con mayor necesidad de intervención", "% de árboles con 2 o más señales de deterioro"
        )
    )

    if not top_interv.empty:
        st.warning(
            f"El barrio con mayor necesidad de intervención es **{top_interv.index[0]}**: "
            f"{fmt_pct(top_interv['pct_intervencion_v2'].iloc[0])} de sus árboles tiene 2 o más señales de deterioro "
            f"({fmt_pct(top_interv['pct_conflicto_vereda'].iloc[0])} con conflicto de vereda, "
            f"{fmt_pct(top_interv['pct_parasitados'].iloc[0])} parasitados y "
            f"{fmt_pct(top_interv['pct_estado_critico'].iloc[0])} en estado de salud crítico)."
        )

    if st.checkbox("Ver tabla completa de intervención por barrio"):
        mostrar(resumen_final)

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
                fontsize=11, color=PALETA["texto"], xytext=(4, 4), textcoords="offset points",
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
            "Para decidir dónde plantar, ver la pestaña «Equidad y plantación», que cruza densidad arbórea con población."
        )
    else:
        st.info("No hay suficientes barrios con datos de superficie/estado crítico para el scatter con este filtro.")

# ----------------------------------------------------------
# TAB 7: Análisis de Correspondencias Múltiples (MCA)
# ----------------------------------------------------------
NOMBRES_VAR_MCA = {
    "riesgo": "Riesgo", "estado_salud": "Estado de salud", "inclinacion": "Inclinación",
    "ahuecamiento": "Ahuecamiento", "levantamiento_vereda": "Levantamiento de vereda", "fase_vital": "Fase vital",
}


def _categoria_corta(nombre, n=28):
    cat = nombre.split("__", 1)[1] if "__" in nombre else nombre
    return cat if len(cat) <= n else cat[: n - 1] + "…"


def grafico_mca(coord, colores):
    """Puntos coloreados por variable (leyenda) y etiquetas solo con la categoría, repartidas para no pisarse."""
    fig, ax = plt.subplots(figsize=(13, 10))
    grupos = {}
    for nombre in coord.index:
        grupos.setdefault(nombre.split("__")[0] if "__" in nombre else nombre, []).append(nombre)
    textos = []
    for var, nombres in grupos.items():
        color = colores.get(var, PALETA["texto"])
        ax.scatter(coord.loc[nombres, 0], coord.loc[nombres, 1], color=color, s=80, edgecolors="white",
                   linewidths=0.5, label=NOMBRES_VAR_MCA.get(var, var), zorder=3)
        for nombre in nombres:
            textos.append(ax.text(coord.loc[nombre, 0], coord.loc[nombre, 1], _categoria_corta(nombre),
                                  fontsize=12, color=color, zorder=4))
    ax.axhline(0, color=PALETA["texto"], linestyle="--", alpha=0.4)
    ax.axvline(0, color=PALETA["texto"], linestyle="--", alpha=0.4)
    ax.margins(x=0.22, y=0.12)
    ax.set_xlabel("Dimensión 1")
    ax.set_ylabel("Dimensión 2")
    ax.set_title("MCA - Categorías de variables del arbolado")
    leg = ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1.0), framealpha=0.85, title="Variable")
    leg.get_title().set_color(PALETA["texto"])
    fig.canvas.draw()
    try:
        from adjustText import adjust_text
        adjust_text(textos, ax=ax, expand=(1.6, 2.0), force_text=(0.5, 0.8), force_static=(0.3, 0.5), iter_lim=600,
                    arrowprops=dict(arrowstyle="-", color="#BBBBBB", lw=0.7))
    except Exception:
        for k, tx in enumerate(textos):  # sin adjustText: separa verticalmente de forma alterna
            x, y = tx.get_position()
            tx.set_position((x + 0.02, y + (0.04 if k % 2 == 0 else -0.06)))
    return fig
with tabs[7]:
    fuente(F_ARB, F_SEG)
    st.subheader("Análisis de Correspondencias Múltiples (MCA)")
    st.caption(
        "Visualiza conjuntamente las variables categóricas relacionadas con el estado y riesgo del arbolado. "
        "Cada color es una variable y cada punto una categoría: los puntos cercanos corresponden a categorías "
        "que suelen aparecer en los mismos árboles."
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

            fig = grafico_mca(coord, colores_mca)
            estilo_oscuro(fig, fig.axes[0])
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
    fuente(F_ARB, F_SEG, F_BAR)
    st.subheader("Indicadores por barrio")

    st.caption(
        "Superficie calculada desde la geometría de cada barrio (EPSG:32721), con los polígonos duplicados "
        "de Collantes y Molina Punta unificados; no se usa la columna `sup_ha` del CSV."
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
        sup_ha_por_barrio(barrios).rename("sup_ha"), left_index=True, right_index=True, how="left"
    )

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

    # 7) Índice de intervención v2: % de árboles con 2 o más de 5 señales de deterioro
    df_estado_ind = senales_intervencion(df_estado_ind)
    resumen_ind["pct_intervencion_v2"] = (
        df_estado_ind.groupby("nombre_barrio")["requiere_intervencion"].mean() * 100
    )

    resumen_ind_final = resumen_ind[resumen_ind["total_arboles"] >= min_arboles_ind].sort_values(
        "pct_intervencion_v2", ascending=False
    )

    st.markdown("**Índice de intervención v2** (% de árboles con 2 o más señales de deterioro)")
    st.caption(
        "Señales (último seguimiento): riesgo de caída alto, salud Malo o Muerto, ahuecamiento severo, "
        "inclinación pronunciada y fase vital Añosa o Decrépita. Un árbol requiere intervención con 2 o más. "
        "Al combinar cinco señales en lugar de depender de los pocos casos de riesgo alto, el ranking es más estable."
    )
    top_n_ind = st.slider("Cantidad de barrios a mostrar", 5, 30, 15, key="topn_ind_v2")
    st.pyplot(
        grafico_ranking_horizontal(
            resumen_ind_final["pct_intervencion_v2"].head(top_n_ind), PALETA["rojo"],
            "Barrios con mayor índice de intervención v2", "% de árboles con 2 o más señales"
        )
    )

    _con_seguimiento = resumen_ind_final["pct_sin_seguimiento"] > 30
    if _con_seguimiento.any():
        st.warning(
            "Los siguientes barrios tienen más del 30% de sus árboles sin ningún seguimiento "
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
    fuente(F_ARB, F_BAR)
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
        "pct_intervencion_v2",
    ]
    mostrar(resumen_ind_final[columnas_tabla])
    st.caption(
        "`dias_desde_ultima_inspeccion` en blanco = el barrio no tiene ningún seguimiento con fecha "
        "válida (no es que esté sano, es que no hay dato)."
    )


# ----------------------------------------------------------
# TAB 9: Equidad territorial y prioridad de plantación
# ----------------------------------------------------------
with tabs[9]:
    fuente(F_ARB, F_SEG, F_BAR, F_CEN)
    st.subheader("Equidad territorial y prioridad de plantación")
    st.caption(
        "Esta pestaña usa todos los barrios con árboles registrados y no responde al filtro de barrios de la barra lateral. "
        "Población: Censo 2010 repartida por superficie de intersección con los radios censales (estimación)."
    )
    if not file_censo:
        st.info("Falta `Densidad_Poblacional.csv` en el repositorio (o cargarlo desde la barra lateral) para calcular esta pestaña.")
    else:
        try:
            pob, info_pob = poblacion_barrios(file_censo, file_barrios, barrios)
        except Exception as e:
            st.error(f"No se pudo calcular la población por barrio: {e}")
            st.stop()

        nombres = barrios["nombre_barrio"].drop_duplicates()
        pr = pd.DataFrame(index=pd.Index(nombres, name="nombre_barrio"))
        pr["total_arboles"] = arboles["nombre_barrio"].value_counts().reindex(pr.index).fillna(0).astype(int)
        pr["sup_ha"] = sup_ha_por_barrio(barrios).reindex(pr.index)
        pr["arboles_por_ha"] = pr["total_arboles"] / pr["sup_ha"]
        pr["poblacion"] = pob.reindex(pr.index)
        con_pob = pr["poblacion"] > 0
        pr["poblacion_por_ha"] = (pr["poblacion"] / pr["sup_ha"]).where(con_pob)
        pr["arboles_1000_hab"] = (pr["total_arboles"] / pr["poblacion"] * 1000).where(con_pob)
        pr["base_poblacional_baja"] = pr["poblacion"] < MIN_POBLACION_ALERTA
        est_all = estado_actual(df)
        pr["pct_estado_critico"] = (
            est_all["estado_salud"].isin(["Malo", "Muerto"]).groupby(est_all["nombre_barrio"]).mean() * 100
        ).reindex(pr.index)

        n_sin_arboles = int((pr["total_arboles"] == 0).sum())
        pr_ok = pr[pr["total_arboles"] > 0].dropna(subset=["arboles_por_ha", "poblacion_por_ha"]).copy()
        med_a, med_p = pr_ok["arboles_por_ha"].median(), pr_ok["poblacion_por_ha"].median()
        pr_ok["indice_prioridad"] = (
            0.5 * (1 - pr_ok["arboles_por_ha"].rank(pct=True)) + 0.5 * pr_ok["poblacion_por_ha"].rank(pct=True)
        ).round(3)
        pr_ok["prioritario"] = (pr_ok["arboles_por_ha"] < med_a) & (pr_ok["poblacion_por_ha"] > med_p)
        med_c = pr_ok["pct_estado_critico"].median()
        pr_ok["lectura"] = np.select(
            [pr_ok["prioritario"] & pr_ok["pct_estado_critico"].isna(),
             pr_ok["prioritario"] & (pr_ok["pct_estado_critico"] < med_c),
             pr_ok["prioritario"]],
            ["Evaluar: faltan datos de estado",
             "Plantar; deterioro observado relativamente bajo",
             "Combinar plantación con intervención del arbolado existente"],
            default="No prioritario según el cruce de medianas",
        )

        c1, c2, c3 = st.columns(3)
        c1.metric("Barrios evaluables", f"{formato_ar(len(pr_ok))} de {formato_ar(len(pr))}")
        c2.metric("Barrios prioritarios", formato_ar(int(pr_ok["prioritario"].sum())))
        c3.metric("Barrios sin árboles", formato_ar(n_sin_arboles))

        top8 = pr["total_arboles"].nlargest(8)
        st.warning(
            f"Pocos árboles registrados no es lo mismo que pocos árboles. El {fmt_pct(top8.sum() / pr['total_arboles'].sum() * 100, 0)} "
            f"de los árboles geolocalizados ({formato_ar(top8.sum())} de {formato_ar(pr['total_arboles'].sum())}) está en 8 barrios; "
            f"{top8.index[0]} tiene {formato_ar(top8.iloc[0])}, y {formato_ar(int((pr['arboles_por_ha'] < 1).sum()))} de "
            f"{formato_ar(len(pr))} barrios tienen menos de un árbol registrado por hectárea. Eso se parece más a un relevamiento "
            "que avanzó por zonas que a una diferencia real de arbolado: la lista de prioridad señala, sobre todo, barrios "
            "que todavía no fueron relevados."
        )
        st.markdown("**Prioridad de plantación: baja densidad arbórea y alta densidad poblacional**")
        fig_p, ax_p = plt.subplots(figsize=(9, 6))
        sc = ax_p.scatter(pr_ok["arboles_por_ha"], pr_ok["poblacion_por_ha"], c=pr_ok["indice_prioridad"],
                          cmap="YlOrRd", s=55, edgecolors="white", linewidths=0.4)
        ax_p.axvline(med_a, color=PALETA["amarillo"], linestyle="--", linewidth=1.2)
        ax_p.axhline(med_p, color=PALETA["amarillo"], linestyle="--", linewidth=1.2)
        for nombre, fila in pr_ok[pr_ok["prioritario"]].sort_values("indice_prioridad", ascending=False).head(10).iterrows():
            ax_p.annotate(nombre, (fila["arboles_por_ha"], fila["poblacion_por_ha"]), fontsize=11,
                          color=PALETA["texto"], xytext=(4, 4), textcoords="offset points")
        for k, (nombre, fila) in enumerate(pr_ok.nlargest(8, "arboles_por_ha").iterrows()):
            ax_p.annotate(nombre, (fila["arboles_por_ha"], fila["poblacion_por_ha"]), fontsize=11,
                          color=PALETA["amarillo"], xytext=(6, 8 if k % 2 == 0 else -16), textcoords="offset points")
        ax_p.set_xlabel("Árboles registrados por hectárea")
        ax_p.set_ylabel("Habitantes estimados por hectárea (Censo 2010)")
        ax_p.set_title("Prioridad territorial de plantación")
        cb = fig_p.colorbar(sc, ax=ax_p, label="Índice de prioridad (0 a 1)")
        cb.ax.yaxis.label.set_color(PALETA["texto"])
        cb.ax.tick_params(colors=PALETA["texto"])
        cb.ax.yaxis.set_major_formatter(_formatter_ar(cb.ax.yaxis))
        estilo_oscuro(fig_p, ax_p)
        st.pyplot(fig_p)
        st.caption(
            f"Líneas punteadas: medianas ({fmt_num(med_a, 2)} árboles/ha y {fmt_num(med_p, 2)} hab./ha). "
            "Arriba a la izquierda: barrios prioritarios (rótulos blancos: los 10 con mayor índice). "
            "En amarillo: los 8 barrios con más árboles registrados por hectárea, que concentran el padrón."
        )

        st.markdown("**Árboles cada 1.000 habitantes**")
        incluir_bajos = st.checkbox(f"Incluir barrios con menos de {MIN_POBLACION_ALERTA} habitantes estimados")
        h = pr[pr["total_arboles"] > 0].dropna(subset=["arboles_1000_hab"])
        if not incluir_bajos:
            h = h[~h["base_poblacional_baja"]]
        n_h = st.slider("Cantidad de barrios a mostrar", 5, 30, 15, key="topn_1000")
        st.pyplot(
            grafico_ranking_horizontal(
                h["arboles_1000_hab"].sort_values().head(n_h), PALETA["verde_neon"],
                "Barrios con menos árboles por habitante", "Árboles cada 1.000 habitantes"
            )
        )

        st.caption(
            f"Los {formato_ar(n_sin_arboles)} barrios sin árboles registrados quedan fuera de este análisis, igual que en el resto del tablero: "
            "puede ser falta de relevamiento y no ausencia de arbolado."
        )
        pr_ok["poblacion"] = pr_ok["poblacion"].round(0)
        st.markdown("**Lista de barrios prioritarios**")
        lista = pr_ok[pr_ok["prioritario"]].sort_values("indice_prioridad", ascending=False)
        mostrar(lista[["total_arboles", "arboles_por_ha", "poblacion", "poblacion_por_ha", "arboles_1000_hab",
                       "pct_estado_critico", "indice_prioridad", "base_poblacional_baja", "lectura"]])
        st.caption(
            "Conclusión: esta lista orienta dónde relevar y plantar primero, pero no mide un déficit real de arbolado, "
            "porque el padrón está concentrado en pocos barrios. Antes de definir sitios hay que verificar veredas, servicios, "
            "espacio disponible y especies. Una base poblacional baja hace inestable el cociente por habitante."
        )
        with st.expander(f"Barrios sin árboles registrados ({formato_ar(n_sin_arboles)}): pendientes de relevamiento"):
            sin = pr[pr["total_arboles"] == 0].sort_values("poblacion", ascending=False)[["poblacion", "poblacion_por_ha"]]
            sin["poblacion"] = sin["poblacion"].round(0)
            mostrar(sin.rename(columns={"poblacion": "Población estimada (2010)", "poblacion_por_ha": "Habitantes por ha"}))
