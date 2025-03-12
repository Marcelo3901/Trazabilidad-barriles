import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime
import json

# ------------------------ CONFIGURACIÓN INICIAL ------------------------
st.set_page_config(page_title="Trazabilidad de Barriles", layout="wide")
st.title("📦 Sistema de Trazabilidad de Barriles")

# ------------------------ CREDENCIALES DESDE SECRETS ------------------------
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials_dict = st.secrets["gcp_service_account"]
credentials = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)
gc = gspread.authorize(credentials)

# ------------------------ DATOS DESDE GOOGLE SHEETS ------------------------
SPREADSHEET_NAME = "TrazabilidadBarriles"
worksheet_registros = gc.open(SPREADSHEET_NAME).worksheet("Registros")
worksheet_clientes = gc.open(SPREADSHEET_NAME).worksheet("Clientes")

# ------------------------ FUNCIONES AUXILIARES ------------------------
def cargar_datos():
    data = worksheet_registros.get_all_records()
    return pd.DataFrame(data)

def cargar_clientes():
    data = worksheet_clientes.get_all_records()
    return pd.DataFrame(data)

def guardar_registro(registro):
    worksheet_registros.append_row(registro)

def guardar_cliente(cliente):
    worksheet_clientes.append_row(cliente)

# ------------------------ FORMULARIO PRINCIPAL ------------------------
st.subheader("Registrar movimiento de barril")

estilos = ["IPA", "APA", "Stout", "Lager", "Amber Ale", "Porter"]
estados = ["Despachado", "Lavado en bodega", "Sucio", "En cuarto frío"]

df_clientes = cargar_clientes()
clientes = df_clientes["Nombre"].tolist() if not df_clientes.empty else []

with st.form("formulario_registro"):
    codigo = st.text_input("Código del barril (Ej: 20XXX)")
    estilo = st.selectbox("Estilo de cerveza", estilos)
    cliente = st.selectbox("Cliente", clientes)
    estado = st.selectbox("Estado del barril", estados)
    fecha = st.date_input("Fecha", datetime.today())
    hora = st.time_input("Hora", datetime.now().time())
    enviado = st.form_submit_button("Guardar registro")

    if enviado:
        if codigo.startswith("20") or codigo.startswith("30") or codigo.startswith("58"):
            registro = [str(codigo), estilo, cliente, estado, str(fecha), str(hora)]
            guardar_registro(registro)
            st.success("✅ Registro guardado correctamente")
        else:
            st.error("❌ Código inválido. Debe comenzar con 20, 30 o 58")

# ------------------------ REGISTRO DE NUEVO CLIENTE ------------------------
st.subheader("Registrar nuevo cliente")

with st.form("formulario_cliente"):
    nuevo_cliente = st.text_input("Nombre del nuevo cliente")
    direccion = st.text_input("Dirección")
    registrar_cliente = st.form_submit_button("Guardar cliente")

    if registrar_cliente:
        if nuevo_cliente:
            guardar_cliente([nuevo_cliente, direccion])
            st.success("✅ Cliente guardado correctamente. Recarga la página para verlo en el formulario de registro.")
        else:
            st.error("❌ Ingresa al menos el nombre del cliente")

# ------------------------ VISUALIZAR REGISTROS ------------------------
st.subheader("📋 Registros actuales")
df = cargar_datos()
st.dataframe(df, use_container_width=True)

# ------------------------ BUSCAR POR CÓDIGO ------------------------
st.subheader("🔍 Buscar información de un barril por código")
codigo_busqueda = st.text_input("Buscar código de barril")
if codigo_busqueda:
    resultado = df[df["Código"] == codigo_busqueda]
    if not resultado.empty:
        st.table(resultado)
    else:
        st.warning("⚠️ No se encontró información para ese código")

# ------------------------ ELIMINAR REGISTROS (protección con contraseña) ------------------------
st.subheader("⚠️ Eliminar registros")
PASS_ELIMINAR = "1234"
PASS_ELIMINAR_TODO = "5678"

with st.expander("Eliminar un registro específico"):
    pass_input = st.text_input("Contraseña", type="password")
    codigo_eliminar = st.text_input("Código del barril a eliminar")
    if st.button("Eliminar"):
        if pass_input == PASS_ELIMINAR:
            df_filtrado = df[df["Código"] != codigo_eliminar]
            worksheet_registros.clear()
            worksheet_registros.append_row(df.columns.tolist())
            for row in df_filtrado.values.tolist():
                worksheet_registros.append_row(row)
            st.success("✅ Registro eliminado")
        else:
            st.error("❌ Contraseña incorrecta")

with st.expander("Eliminar TODOS los registros"):
    pass_all = st.text_input("Contraseña para eliminar todo", type="password")
    if st.button("Eliminar todos los registros"):
        if pass_all == PASS_ELIMINAR_TODO:
            worksheet_registros.clear()
            worksheet_registros.append_row(["Código", "Estilo", "Cliente", "Estado", "Fecha", "Hora"])
            st.success("✅ Todos los registros fueron eliminados")
        else:
            st.error("❌ Contraseña incorrecta")
