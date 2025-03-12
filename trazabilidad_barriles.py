import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime
import json

# Definir el alcance de acceso a Google Sheets
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# Cargar credenciales desde secrets.toml o panel de Streamlit Cloud
credentials_dict = st.secrets["gcp_service_account"]
credentials = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, SCOPE)
gc = gspread.authorize(credentials)

# Nombre de la hoja de cálculo
SPREADSHEET_NAME = "TrazabilidadBarriles"

# Abrir hoja de cálculo
sh = gc.open(SPREADSHEET_NAME)
worksheet = sh.worksheet("Registros")
clientes_sheet = sh.worksheet("Clientes")

# Función para cargar registros existentes
def cargar_datos():
    try:
        data = worksheet.get_all_records()
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Error al cargar los datos: {e}")
        return pd.DataFrame()

# Función para guardar nuevo registro
def guardar_registro(registro):
    worksheet.append_row(registro)

# Función para cargar lista de clientes
def cargar_clientes():
    clientes = clientes_sheet.get_all_records()
    return [f"{c['Cliente']} - {c['Dirección']}" for c in clientes]

# Función para guardar nuevo cliente
def guardar_cliente(cliente, direccion):
    clientes_sheet.append_row([cliente, direccion])

# Encabezado
st.title("📦 Trazabilidad de Barriles - Cervecería")

# Menú principal
menu = st.sidebar.selectbox("Seleccionar opción", ["Registro de Barril", "Ver Registros", "Buscar Barril", "Eliminar Barril", "Eliminar Todos los Registros", "Registro de Nuevo Cliente"])

# Listado de estilos
estilos = ["IPA", "APA", "Porter", "Stout", "Lager", "Amber Ale", "Honey", "Red Ale"]

# Listado de estados posibles
estados = ["Despachado", "Lavado en Bodega", "Sucio", "En Cuarto Frío"]

# Registro de Barril
if menu == "Registro de Barril":
    st.subheader("Registrar Movimiento de Barril")

    codigo = st.text_input("Código del Barril")
    estilo = st.selectbox("Estilo de Cerveza", estilos)
    cliente = st.selectbox("Cliente", cargar_clientes())
    estado = st.selectbox("Estado del Barril", estados)
    fecha = datetime.today().strftime('%Y-%m-%d')

    if st.button("Guardar Registro"):
        if codigo and estilo and cliente and estado:
            if codigo.startswith("20") or codigo.startswith("30") or codigo.startswith("58"):
                guardar_registro([fecha, codigo, estilo, cliente, estado])
                st.success("✅ Registro guardado exitosamente")
            else:
                st.warning("⚠️ El código debe comenzar con 20, 30 o 58 según el tipo de barril")
        else:
            st.warning("⚠️ Complete todos los campos")

# Ver registros
elif menu == "Ver Registros":
    st.subheader("📄 Registros de Barriles")
    df = cargar_datos()
    st.dataframe(df)

# Buscar barril
elif menu == "Buscar Barril":
    st.subheader("🔍 Buscar Barril por Código")
    codigo_buscar = st.text_input("Ingrese el código del barril a buscar")
    if st.button("Buscar"):
        df = cargar_datos()
        resultado = df[df["Código"] == codigo_buscar]
        if not resultado.empty:
            st.dataframe(resultado)
        else:
            st.warning("⚠️ No se encontró ese código")

# Eliminar un barril específico
elif menu == "Eliminar Barril":
    st.subheader("🗑 Eliminar Barril por Código")
    password = st.text_input("Ingrese contraseña para eliminar", type="password")
    if password == "eliminar123":
        codigo_eliminar = st.text_input("Código del barril a eliminar")
        if st.button("Eliminar"):
            df = cargar_datos()
            nuevo_df = df[df["Código"] != codigo_eliminar]
            if len(nuevo_df) < len(df):
                worksheet.clear()
                worksheet.append_row(df.columns.tolist())
                for i in nuevo_df.itertuples(index=False):
                    worksheet.append_row(list(i))
                st.success("✅ Barril eliminado")
            else:
                st.warning("⚠️ Código no encontrado")
    else:
        st.info("🔐 Ingrese contraseña válida para continuar")

# Eliminar todos los registros
elif menu == "Eliminar Todos los Registros":
    st.subheader("⚠️ Eliminar TODOS los Registros")
    password = st.text_input("Ingrese contraseña de administrador", type="password")
    if password == "admin123":
        if st.button("Eliminar Todo"):
            worksheet.clear()
            worksheet.append_row(["Fecha", "Código", "Estilo", "Cliente", "Estado"])
            st.success("✅ Todos los registros han sido eliminados")
    else:
        st.info("🔐 Ingrese contraseña válida para continuar")

# Registro de nuevo cliente
elif menu == "Registro de Nuevo Cliente":
    st.subheader("👤 Agregar Nuevo Cliente")
    nuevo_cliente = st.text_input("Nombre del cliente")
    direccion = st.text_input("Dirección del cliente")
    if st.button("Guardar Cliente"):
        if nuevo_cliente and direccion:
            guardar_cliente(nuevo_cliente, direccion)
            st.success("✅ Cliente agregado")
        else:
            st.warning("⚠️ Complete todos los campos")
