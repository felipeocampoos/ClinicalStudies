import io
import unicodedata
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Estudios clínicos Colombia", layout="wide")

# Ruta del archivo base dentro del repositorio
DATA_PATH = "ctg-studies (3).csv"


def normalizar_texto(texto):
    texto = str(texto)
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("utf-8")
    return texto.lower().strip()


@st.cache_data
def cargar_y_preparar_datos():
    df = pd.read_csv(DATA_PATH)

    locations_norm = df["Locations"].fillna("").apply(normalizar_texto)

    mask_valle = locations_norm.str.contains("valle del cauca", regex=False)
    mask_lili = locations_norm.str.contains("fundacion valle del lili", regex=False)

    df_colombia = df.copy()
    df_valle = df[mask_valle].copy()
    df_lili = df[mask_lili].copy()

    return df_colombia, df_valle, df_lili


def dataframe_a_excel_bytes(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="datos")
    output.seek(0)
    return output.getvalue()


def grafica_conteos(df_colombia, df_valle, df_lili):
    categorias = ["Colombia", "Valle del Cauca", "Fundación Valle del Lili"]
    valores = [len(df_colombia), len(df_valle), len(df_lili)]

    fig, ax = plt.subplots(figsize=(10, 5))
    colores = plt.cm.Pastel1(np.linspace(0, 1, len(valores)))
    bars = ax.bar(categorias, valores, color=colores)

    max_valor = max(valores)

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

    return fig


def grafica_barras_status(df_filtrado, titulo):
    serie_status = (
        df_filtrado["Study Status"]
        .fillna("Sin dato")
        .value_counts()
        .sort_values(ascending=True)
    )

    etiquetas = serie_status.index.str.replace("_", " ", regex=False)
    valores = serie_status.values
    total = valores.sum()
    porcentajes = (valores / total) * 100 if total > 0 else np.zeros_like(valores, dtype=float)

    fig, ax = plt.subplots(figsize=(12, 6))
    colores = plt.cm.Pastel1(np.linspace(0, 1, len(valores)))
    ax.barh(etiquetas, valores, color=colores)

    max_valor = max(valores) if len(valores) > 0 else 1

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

    return fig


def tabla_status(df_filtrado):
    tabla = (
        df_filtrado["Study Status"]
        .fillna("Sin dato")
        .value_counts()
        .reset_index()
    )
    tabla.columns = ["Study Status", "Número de estudios"]
    tabla["Porcentaje"] = (tabla["Número de estudios"] / tabla["Número de estudios"].sum() * 100).round(1)
    return tabla


def render_seccion(nombre_seccion, df_seccion, nombre_archivo, df_colombia, df_valle, df_lili):
    st.header(nombre_seccion)

    st.metric("Número de estudios", len(df_seccion))

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Conteo general de estudios")
        fig1 = grafica_conteos(df_colombia, df_valle, df_lili)
        st.pyplot(fig1)

    with col2:
        st.subheader("Distribución de Study Status")
        fig2 = grafica_barras_status(df_seccion, f"Distribución de Study Status - {nombre_seccion}")
        st.pyplot(fig2)

    st.subheader("Descargar archivo")
    excel_bytes = dataframe_a_excel_bytes(df_seccion)

    st.download_button(
        label=f"Descargar {nombre_archivo}",
        data=excel_bytes,
        file_name=nombre_archivo,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    st.subheader("Distribución de Study Status en tabla")
    st.dataframe(tabla_status(df_seccion), use_container_width=True)

    with st.expander("Ver muestra de registros"):
        st.dataframe(df_seccion.head(100), use_container_width=True)


def main():
    st.title("Estudios clínicos aprobados en Colombia")
    st.write("Selecciona una sección para ver las gráficas y descargar el archivo en Excel.")

    df_colombia, df_valle, df_lili = cargar_y_preparar_datos()

    seccion = st.sidebar.radio(
        "Sección",
        ["Colombia", "Valle del Cauca", "Fundación Valle del Lili"]
    )

    if seccion == "Colombia":
        render_seccion(
            "Colombia",
            df_colombia,
            "estudios_colombia.xlsx",
            df_colombia,
            df_valle,
            df_lili
        )

    elif seccion == "Valle del Cauca":
        render_seccion(
            "Valle del Cauca",
            df_valle,
            "estudios_valle_del_cauca.xlsx",
            df_colombia,
            df_valle,
            df_lili
        )

    elif seccion == "Fundación Valle del Lili":
        render_seccion(
            "Fundación Valle del Lili",
            df_lili,
            "estudios_fundacion_valle_del_lili.xlsx",
            df_colombia,
            df_valle,
            df_lili
        )


if __name__ == "__main__":
    main()

