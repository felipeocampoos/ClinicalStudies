import io
import unicodedata

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Estudios clínicos Colombia",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Oculta el botón para colapsar la barra lateral
st.markdown("""
<style>
    [data-testid="collapsedControl"] {
        display: none;
    }
</style>
""", unsafe_allow_html=True)

# Ajusta este nombre si renombras el archivo en GitHub
DATA_PATH = "ctg-studies.csv"


def normalizar_texto(texto):
    texto = str(texto)
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("utf-8")
    return texto.lower().strip()


def normalizar_nombre_archivo(texto):
    texto = normalizar_texto(texto)
    texto = texto.replace(" ", "_")
    return texto


def limpiar_etiqueta_status(texto):
    return str(texto).replace("_", " ")


@st.cache_data
def cargar_datos():
    df = pd.read_csv(DATA_PATH)

    # Parsear Start Date
    df["Start Date Parsed"] = pd.to_datetime(df["Start Date"], errors="coerce")

    # Normalizar Locations
    df["Locations_norm"] = df["Locations"].fillna("").apply(normalizar_texto)

    return df


def filtrar_datos(df, fecha_inicio, fecha_fin, estados_seleccionados):
    # 1. Filtro por fecha
    mask_fecha = (
        df["Start Date Parsed"].notna()
        & (df["Start Date Parsed"].dt.date >= fecha_inicio)
        & (df["Start Date Parsed"].dt.date <= fecha_fin)
    )

    df_filtrado = df[mask_fecha].copy()

    # 2. Filtro por estados
    if estados_seleccionados:
        df_filtrado = df_filtrado[
            df_filtrado["Study Status"].fillna("Sin dato").isin(estados_seleccionados)
        ].copy()
    else:
        df_filtrado = df_filtrado.iloc[0:0].copy()

    # 3. Filtros por ubicación
    mask_valle = df_filtrado["Locations_norm"].str.contains("valle del cauca", regex=False)
    mask_lili = df_filtrado["Locations_norm"].str.contains("fundacion valle del lili", regex=False)

    df_colombia = df_filtrado.copy()
    df_valle = df_filtrado[mask_valle].copy()
    df_lili = df_filtrado[mask_lili].copy()

    # Quitar columnas auxiliares antes de mostrar/descargar
    columnas_aux = ["Start Date Parsed", "Locations_norm"]
    df_colombia = df_colombia.drop(columns=columnas_aux, errors="ignore")
    df_valle = df_valle.drop(columns=columnas_aux, errors="ignore")
    df_lili = df_lili.drop(columns=columnas_aux, errors="ignore")

    return df_colombia, df_valle, df_lili


def dataframe_a_excel_bytes(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="datos")
    output.seek(0)
    return output.getvalue()


def figura_a_png_bytes(fig):
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=300, bbox_inches="tight")
    buffer.seek(0)
    return buffer.getvalue()


def grafica_conteos(df_colombia, df_valle, df_lili):
    categorias = ["Colombia", "Valle del Cauca", "Fundación Valle del Lili"]
    valores = [len(df_colombia), len(df_valle), len(df_lili)]

    fig, ax = plt.subplots(figsize=(10, 5))
    colores = plt.cm.Pastel1(np.linspace(0, 1, len(valores)))
    bars = ax.bar(categorias, valores, color=colores)

    max_valor = max(valores) if len(valores) > 0 else 1

    for bar, valor in zip(bars, valores):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            valor + max_valor * 0.02,
            f"{valor}",
            ha="center",
            va="bottom",
            fontsize=11
        )

    ax.set_title("Número de estudios por sección")
    ax.set_ylabel("Cantidad de estudios")
    ax.set_ylim(0, max_valor * 1.18)

    fig.tight_layout()
    return fig


def grafica_barras_status(df_filtrado, titulo):
    serie_status = (
        df_filtrado["Study Status"]
        .fillna("Sin dato")
        .value_counts()
        .sort_values(ascending=True)
    )

    fig, ax = plt.subplots(figsize=(12, 6))

    if len(serie_status) == 0:
        ax.text(
            0.5, 0.5,
            "No hay datos para los filtros seleccionados",
            ha="center", va="center", fontsize=12
        )
        ax.set_title(titulo)
        ax.axis("off")
        fig.tight_layout()
        return fig

    etiquetas = [limpiar_etiqueta_status(x) for x in serie_status.index]
    valores = serie_status.values
    total = valores.sum()
    porcentajes = (valores / total) * 100

    colores = plt.cm.Pastel1(np.linspace(0, 1, len(valores)))
    ax.barh(etiquetas, valores, color=colores)

    max_valor = max(valores)

    for i, (valor, pct) in enumerate(zip(valores, porcentajes)):
        ax.text(
            valor + max_valor * 0.02,
            i,
            f"{valor} ({pct:.1f}%)",
            va="center",
            fontsize=11
        )

    ax.set_title(titulo)
    ax.set_xlabel("Número de estudios")
    ax.set_ylabel("Study Status")
    ax.set_xlim(0, max_valor * 1.25)

    fig.tight_layout()
    return fig


def tabla_status(df_filtrado):
    tabla = (
        df_filtrado["Study Status"]
        .fillna("Sin dato")
        .value_counts()
        .reset_index()
    )

    if tabla.empty:
        return pd.DataFrame(columns=["Study Status", "Número de estudios", "Porcentaje"])

    tabla.columns = ["Study Status", "Número de estudios"]
    tabla["Study Status"] = tabla["Study Status"].apply(limpiar_etiqueta_status)
    tabla["Porcentaje"] = (
        tabla["Número de estudios"] / tabla["Número de estudios"].sum() * 100
    ).round(1)

    return tabla


def resumen_filtros_texto(fecha_inicio, fecha_fin, estados_seleccionados):
    if not estados_seleccionados:
        texto_estados = "Ninguno"
    elif len(estados_seleccionados) == 1:
        texto_estados = limpiar_etiqueta_status(estados_seleccionados[0])
    elif len(estados_seleccionados) <= 4:
        texto_estados = ", ".join([limpiar_etiqueta_status(x) for x in estados_seleccionados])
    else:
        texto_estados = f"{len(estados_seleccionados)} estados seleccionados"

    return f"Rango de fechas: {fecha_inicio} a {fecha_fin} | Estados: {texto_estados}"


def render_seccion(
    nombre_seccion,
    df_seccion,
    nombre_archivo_excel,
    df_colombia,
    df_valle,
    df_lili,
    fecha_inicio,
    fecha_fin,
    estados_seleccionados
):
    st.header(nombre_seccion)
    st.caption(resumen_filtros_texto(fecha_inicio, fecha_fin, estados_seleccionados))
    st.metric("Número de estudios", len(df_seccion))

    nombre_base = normalizar_nombre_archivo(nombre_seccion)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Conteo general de estudios")
        fig1 = grafica_conteos(df_colombia, df_valle, df_lili)
        st.pyplot(fig1)

        png_conteo = figura_a_png_bytes(fig1)
        st.download_button(
            label="Descargar imagen de conteo general",
            data=png_conteo,
            file_name=f"grafica_conteo_general_{nombre_base}_{fecha_inicio}_{fecha_fin}.png",
            mime="image/png",
        )
        plt.close(fig1)

    with col2:
        st.subheader("Distribución de Study Status")
        fig2 = grafica_barras_status(
            df_seccion,
            f"Distribución de Study Status - {nombre_seccion}"
        )
        st.pyplot(fig2)

        png_status = figura_a_png_bytes(fig2)
        st.download_button(
            label="Descargar imagen de Study Status",
            data=png_status,
            file_name=f"grafica_study_status_{nombre_base}_{fecha_inicio}_{fecha_fin}.png",
            mime="image/png",
        )
        plt.close(fig2)

    st.subheader("Descargar archivo")
    excel_bytes = dataframe_a_excel_bytes(df_seccion)

    st.download_button(
        label=f"Descargar {nombre_archivo_excel}",
        data=excel_bytes,
        file_name=nombre_archivo_excel,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    st.subheader("Distribución de Study Status en tabla")
    st.dataframe(tabla_status(df_seccion), use_container_width=True)

    with st.expander("Ver muestra de registros"):
        st.dataframe(df_seccion.head(100), use_container_width=True)


def main():
    st.title("Estudios clínicos aprobados en Colombia")
    st.write(
        "Selecciona una sección, un rango de fechas y uno o varios estados "
        "para actualizar las gráficas y descargar los archivos filtrados."
    )

    df = cargar_datos()

    fechas_validas = df["Start Date Parsed"].dropna()

    if fechas_validas.empty:
        st.error("La columna 'Start Date' no tiene fechas válidas.")
        return

    fecha_min = fechas_validas.min().date()
    fecha_max = fechas_validas.max().date()

    estados_disponibles = sorted(df["Study Status"].fillna("Sin dato").unique().tolist())

    st.sidebar.header("Filtros")

    seccion = st.sidebar.radio(
        "Sección",
        ["Colombia", "Valle del Cauca", "Fundación Valle del Lili"]
    )

    fecha_inicio = st.sidebar.date_input(
        "Fecha de inicio",
        value=fecha_min,
        min_value=fecha_min,
        max_value=fecha_max
    )

    fecha_fin = st.sidebar.date_input(
        "Fecha de fin",
        value=fecha_max,
        min_value=fecha_min,
        max_value=fecha_max
    )

    estados_seleccionados = st.sidebar.multiselect(
        "Study Status",
        options=estados_disponibles,
        default=estados_disponibles,
        format_func=limpiar_etiqueta_status
    )

    if fecha_inicio > fecha_fin:
        st.error("La fecha de inicio no puede ser mayor que la fecha de fin.")
        return

    df_colombia, df_valle, df_lili = filtrar_datos(
        df,
        fecha_inicio,
        fecha_fin,
        estados_seleccionados
    )

    if seccion == "Colombia":
        render_seccion(
            "Colombia",
            df_colombia,
            f"estudios_colombia_{fecha_inicio}_{fecha_fin}.xlsx",
            df_colombia,
            df_valle,
            df_lili,
            fecha_inicio,
            fecha_fin,
            estados_seleccionados
        )

    elif seccion == "Valle del Cauca":
        render_seccion(
            "Valle del Cauca",
            df_valle,
            f"estudios_valle_del_cauca_{fecha_inicio}_{fecha_fin}.xlsx",
            df_colombia,
            df_valle,
            df_lili,
            fecha_inicio,
            fecha_fin,
            estados_seleccionados
        )

    elif seccion == "Fundación Valle del Lili":
        render_seccion(
            "Fundación Valle del Lili",
            df_lili,
            f"estudios_fundacion_valle_del_lili_{fecha_inicio}_{fecha_fin}.xlsx",
            df_colombia,
            df_valle,
            df_lili,
            fecha_inicio,
            fecha_fin,
            estados_seleccionados
        )


if __name__ == "__main__":
    main()
