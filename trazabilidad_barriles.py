import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime

# ✅ Configuración inicial de la app
st.set_page_config(page_title="📦 Sistema de Trazabilidad de Barriles", layout="wide")
st.title("📦 Sistema de Trazabilidad de Barriles")

# ✅ Autenticación con Google Sheets usando secrets.toml
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
credentials_dict = st.secrets["gcp_service_account"]
credentials = Credentials.from_service_account_info(credentials_dict, scopes=scope)

# ✅ Conexión con Google Sheets
gc = gspread.authorize(credentials)
spreadsheet_name = "trazabilidad_barriles"
sh = gc.open(spreadsheet_name)

# ✅ Hojas de trabajo
sheet_registros = sh.worksheet("Registros")
sheet_clientes = sh.worksheet("Clientes")

# ✅ Cargar datos existentes
def cargar_datos():
    registros = pd.DataFrame(sheet_registros.get_all_records())
    clientes = pd.DataFrame(sheet_clientes.get_all_records())
    return registros, clientes

registros_df, clientes_df = cargar_datos()

# ✅ Formulario para ingreso de nuevo registro
st.subheader("➕ Ingreso de Nuevo Registro")

codigo_barril = st.text_input("Código del Barril")
if codigo_barril and not (codigo_barril.startswith("20") or codigo_barril.startswith("30") or codigo_barril.startswith("58")):
    st.warning("El código del barril debe comenzar con 20, 30 o 58.")

estilos_cerveza = ["IPA", "APA", "Pilsner", "Stout", "Amber Ale", "Porter", "Weiss"]
cerveza = st.selectbox("Estilo de Cerveza", estilos_cerveza)

cliente = st.selectbox("Cliente", clientes_df["Nombre"].unique())
estado = st.selectbox("Estado del Barril", ["Despachado", "Lavado en bodega", "Sucio", "En cuarto frío"])

if st.button("Guardar Registro"):
    if codigo_barril == "" or cliente == "" or cerveza == "" or estado == "":
        st.error("Por favor completa todos los campos.")
    else:
        fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        nuevo_registro = [fecha, codigo_barril, cerveza, cliente, estado]
        sheet_registros.append_row(nuevo_registro)
        st.success("✅ Registro guardado correctamente.")

# ✅ Registro de nuevo cliente
st.subheader("🧾 Registro de Nuevo Cliente")
with st.form("nuevo_cliente"):
    nombre_cliente = st.text_input("Nombre del Cliente")
    direccion_cliente = st.text_input("Dirección")
    submitted = st.form_submit_button("Agregar Cliente")
    if submitted:
        if nombre_cliente != "" and direccion_cliente != "":
            sheet_clientes.append_row([nombre_cliente, direccion_cliente])
            st.success("Cliente agregado exitosamente.")
        else:
            st.warning("Completa todos los campos.")

# ✅ Mostrar registros actuales
st.subheader("📋 Registros Actuales")
st.dataframe(registros_df, use_container_width=True)

# ✅ Buscar barril por código
st.subheader("🔍 Buscar Barril por Código")
codigo_busqueda = st.text_input("Ingresar código a buscar")
if st.button("Buscar"):
    resultado = registros_df[registros_df["Codigo"] == codigo_busqueda]
    if not resultado.empty:
        st.write(resultado)
    else:
        st.warning("No se encontró ningún barril con ese código.")

# ✅ Eliminar un barril específico (requiere contraseña)
st.subheader("❌ Eliminar Registro Específico")
password_delete = st.text_input("Contraseña para eliminar un registro", type="password")
codigo_eliminar = st.text_input("Código del barril a eliminar")

if st.button("Eliminar Registro"):
    if password_delete == "1234":  # Cambiar esta contraseña desde el código si se desea
        df_filtrado = registros_df[registros_df["Codigo"] != codigo_eliminar]
        sheet_registros.clear()
        sheet_registros.append_row(["Fecha", "Codigo", "Cerveza", "Cliente", "Estado"])
        for index, row in df_filtrado.iterrows():
            sheet_registros.append_row(row.tolist())
        st.success("Registro eliminado correctamente.")
    else:
        st.error("Contraseña incorrecta.")

# ✅ Eliminar todos los registros (requiere otra contraseña)
st.subheader("⚠️ Eliminar TODOS los Registros")
password_total_delete = st.text_input("Contraseña para eliminar todos los registros", type="password")
if st.button("Eliminar Todos los Registros"):
    if password_total_delete == "admin123":  # Cambiar esta contraseña si se desea
        sheet_registros.clear()
        sheet_registros.append_row(["Fecha", "Codigo", "Cerveza", "Cliente", "Estado"])
        st.success("Todos los registros han sido eliminados.")
    else:
        st.error("Contraseña incorrecta para eliminación total.")
