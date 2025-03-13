import streamlit as st
import pandas as pd
import requests
from urllib.parse import urlencode

st.set_page_config(page_title="Trazabilidad Barriles Castiza", layout="centered")
st.title("🍺 Sistema de Trazabilidad de Barriles - Castiza")

# ------------------------------
# FORMULARIO DE REGISTRO DE BARRILES
# ------------------------------

st.header("📋 Registro de Barril")

codigo_barril = st.text_input("Código del barril (Debe tener 5 dígitos y empezar por 20, 30 o 58)")

# Validación del código del barril
codigo_valido = False
if codigo_barril and len(codigo_barril) == 5 and codigo_barril[:2] in ["20", "30", "58"]:
    codigo_valido = True

estilos = ["Golden", "Amber", "Vienna Lager", "Brown Ale Cafe", "Stout",
           "Session IPA", "IPA", "Maracuya", "Barley Wine", "Trigo", "Catharina Sour",
           "Gose", "Imperial IPA", "NEIPA", "Imperial Stout", "Otros"]
estilo_cerveza = st.selectbox("Estilo", estilos)

estado_barril = st.selectbox("Estado del barril", ["Despachado", "Lavado en bodega", "Sucio", "En cuarto frío"])

# Carga dinámica de clientes desde archivo local
try:
    df_clientes = pd.read_csv("clientes.csv")
    lista_clientes = df_clientes.iloc[:, 0].tolist()
except:
    lista_clientes = []

cliente = "Planta Castiza"
if estado_barril == "Despachado":
    cliente = st.selectbox("Cliente", lista_clientes)

responsables = ["Pepe Vallejo", "Ligia Cajigas", "Erika Martinez", "Marcelo Martinez", "Operario 1", "Operario 2"]
responsable = st.selectbox("Responsable", responsables)

observaciones = st.text_area("Observaciones")

# Envío al formulario de Google Forms
if st.button("Guardar Registro"):
    if codigo_valido:
        form_url = "https://docs.google.com/forms/d/e/1FAIpQLSedFQmZuDdVY_cqU9WdiWCTBWCCh1NosPnD891QifQKqaeUfA/formResponse"
        payload = {
            "entry.311770370": codigo_barril,
            "entry.1283669263": estilo_cerveza,
            "entry.1545499818": estado_barril,
            "entry.91059345": cliente,
            "entry.1661747572": responsable,
            "entry.1465957833": observaciones
        }
        response = requests.post(form_url, data=payload)
        if response.status_code in [200, 302]:
            st.success("✅ Registro enviado correctamente")
        else:
            st.error(f"❌ Error al enviar el formulario. Código de estado: {response.status_code}")
    else:
        st.warning("⚠️ Código de barril inválido. Debe tener 5 dígitos y comenzar por 20, 30 o 58.")

# ------------------------------
# REGISTRAR NUEVO CLIENTE
# ------------------------------
st.markdown("---")
st.header("➕ Registrar Nuevo Cliente")
nuevo_cliente = st.text_input("Nombre del nuevo cliente")
direccion_cliente = st.text_input("Dirección (opcional)")

if st.button("Agregar Cliente"):
    if nuevo_cliente.strip() != "":
        try:
            df_nuevo = pd.DataFrame([[nuevo_cliente, direccion_cliente]])
            if lista_clientes:
                df_clientes = pd.concat([df_clientes, df_nuevo], ignore_index=True)
            else:
                df_clientes = df_nuevo
            df_clientes.drop_duplicates(subset=0, keep="first", inplace=True)
            df_clientes.to_csv("clientes.csv", index=False, header=False)
            st.success("✅ Cliente agregado correctamente")
        except:
            st.error("❌ Error al guardar el nuevo cliente")
    else:
        st.warning("⚠️ El nombre del cliente no puede estar vacío")

# ------------------------------
# ELIMINAR CLIENTE
# ------------------------------
st.markdown("---")
st.header("🗑️ Eliminar Cliente")
if lista_clientes:
    cliente_eliminar = st.selectbox("Selecciona cliente a eliminar", lista_clientes)
    if st.button("Eliminar Cliente"):
        try:
            df_clientes = df_clientes[df_clientes.iloc[:, 0] != cliente_eliminar]
            df_clientes.to_csv("clientes.csv", index=False, header=False)
            st.success("✅ Cliente eliminado correctamente")
        except:
            st.error("❌ Error al eliminar el cliente")

# ------------------------------
# FILTROS Y REPORTE
# ------------------------------
st.markdown("---")
st.header("📁 Últimos Movimientos de Barriles")

try:
    sheet_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQPl9RtGqUuW3r1MCt4P3sR9Bl7npFrxjvmYuC5qK9SKljBGr1O_l8zsnR9ob5bPoHzhKfr2UmJRT68/pub?output=csv"
    df_movimientos = pd.read_csv(sheet_url)

    filtro_codigo = st.text_input("🔍 Buscar por código de barril:")
    filtro_cliente = st.selectbox("🔍 Filtrar por cliente:", ["Todos"] + sorted(df_movimientos.iloc[:, 7].dropna().unique()))
    filtro_estado = st.selectbox("🔍 Filtrar por estado:", ["Todos"] + sorted(df_movimientos.iloc[:, 6].dropna().unique()))

    df_filtrado = df_movimientos.copy()
    if filtro_codigo:
        df_filtrado = df_filtrado[df_filtrado.iloc[:, 1].astype(str).str.contains(filtro_codigo.strip())]
    if filtro_cliente != "Todos":
        df_filtrado = df_filtrado[df_filtrado.iloc[:, 7] == filtro_cliente]
    if filtro_estado != "Todos":
        df_filtrado = df_filtrado[df_filtrado.iloc[:, 6] == filtro_estado]

    st.subheader("📄 Últimos 10 registros")
    reporte = df_filtrado.iloc[:, [1, 5, 6, 7, 8, 9]].rename(columns={
        df_filtrado.columns[1]: "Código",
        df_filtrado.columns[5]: "Estilo",
        df_filtrado.columns[6]: "Estado",
        df_filtrado.columns[7]: "Cliente",
        df_filtrado.columns[8]: "Responsable",
        df_filtrado.columns[9]: "Observaciones"
    })
    st.dataframe(reporte.tail(10))

    csv = reporte.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Descargar últimos registros en CSV", csv, "reporte_barriles.csv", "text/csv")

except Exception as e:
    st.warning(f"⚠️ No se pudo cargar la hoja de cálculo: {e}")
