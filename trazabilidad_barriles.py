import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd

# -----------------------------
# AUTENTICACIÓN CON GOOGLE SHEETS USANDO st.secrets
# -----------------------------
scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# Carga de credenciales desde secrets.toml
credentials_dict = st.secrets["gcp_service_account"]
credentials = Credentials.from_service_account_info(credentials_dict, scopes=scope)

# Autenticación con Google Sheets
gc = gspread.authorize(credentials)

# Abre la hoja de cálculo
SPREADSHEET_NAME = "Trazabilidad_Barriles"
sh = gc.open(SPREADSHEET_NAME)

# -----------------------------
# FUNCIONES AUXILIARES
# -----------------------------
def cargar_hoja(nombre):
    try:
        return sh.worksheet(nombre)
    except:
        return sh.add_worksheet(title=nombre, rows="1000", cols="20")


# -----------------------------
# PÁGINA PRINCIPAL
# -----------------------------
st.set_page_config(page_title="📦 Sistema de Trazabilidad de Barriles", layout="wide")
st.title("📦 Sistema de Trazabilidad de Barriles")

menu = ["Registro de Movimiento", "Consulta de Barriles", "Registro de Nuevo Cliente", "Eliminar Barril", "Eliminar Todos"]
opcion = st.sidebar.selectbox("Selecciona una opción", menu)

# -----------------------------
# ESTILOS Y LISTAS
# -----------------------------
estilos = ["IPA", "APA", "Lager", "Stout", "Amber Ale", "Blonde Ale", "Porter"]
estados = ["Despachado", "Lavado en bodega", "Sucio", "En cuarto frío"]

# -----------------------------
# HOJAS
# -----------------------------
hoja_movimientos = cargar_hoja("Movimientos")
hoja_clientes = cargar_hoja("Clientes")

# -----------------------------
# REGISTRO DE MOVIMIENTO
# -----------------------------
if opcion == "Registro de Movimiento":
    st.subheader("📋 Registrar Movimiento de Barril")

    codigo = st.text_input("Código del Barril (Ej: 20XXX, 30XXX, 58XXX)")
    estilo = st.selectbox("Estilo de Cerveza", estilos)

    clientes_data = hoja_clientes.get_all_records()
    clientes_df = pd.DataFrame(clientes_data)
    clientes = clientes_df["Cliente"].tolist() if not clientes_df.empty else []

    cliente = st.selectbox("Cliente", clientes)
    estado = st.selectbox("Estado del Barril", estados)

    if st.button("Guardar Registro"):
        if codigo.strip() == "" or cliente.strip() == "":
            st.warning("⚠️ Código y Cliente son obligatorios.")
        else:
            hoja_movimientos.append_row([codigo, estilo, cliente, estado])
            st.success("✅ Registro guardado correctamente.")

# -----------------------------
# CONSULTA DE BARRILES
# -----------------------------
elif opcion == "Consulta de Barriles":
    st.subheader("🔍 Consulta de Barriles")
    datos = hoja_movimientos.get_all_records()
    df = pd.DataFrame(datos)

    if not df.empty:
        filtro = st.text_input("Buscar por Código o Cliente")
        if filtro:
            df = df[df.apply(lambda row: filtro.lower() in row.to_string().lower(), axis=1)]
        st.dataframe(df)
    else:
        st.info("No hay registros aún.")

# -----------------------------
# REGISTRO DE NUEVO CLIENTE
# -----------------------------
elif opcion == "Registro de Nuevo Cliente":
    st.subheader("➕ Registrar Nuevo Cliente")
    nuevo_cliente = st.text_input("Nombre del Cliente")
    direccion = st.text_input("Dirección")

    if st.button("Guardar Cliente"):
        if nuevo_cliente.strip() == "":
            st.warning("⚠️ El nombre del cliente es obligatorio.")
        else:
            hoja_clientes.append_row([nuevo_cliente, direccion])
            st.success("✅ Cliente registrado correctamente.")

# -----------------------------
# ELIMINAR UN BARRIL ESPECÍFICO (CON CONTRASEÑA)
# -----------------------------
elif opcion == "Eliminar Barril":
    st.subheader("🗑️ Eliminar un Barril Específico")
    codigo_eliminar = st.text_input("Código del barril a eliminar")
    clave = st.text_input("Contraseña", type="password")

    if st.button("Eliminar"):
        if clave != "clave123":
            st.error("❌ Contraseña incorrecta")
        else:
            datos = hoja_movimientos.get_all_records()
            hoja_movimientos.clear()
            hoja_movimientos.append_row(["Código", "Estilo", "Cliente", "Estado"])
            eliminados = 0
            for row in datos:
                if row["Código"] != codigo_eliminar:
                    hoja_movimientos.append_row([row["Código"], row["Estilo"], row["Cliente"], row["Estado"]])
                else:
                    eliminados += 1
            st.success(f"✅ {eliminados} registro(s) eliminado(s).")

# -----------------------------
# ELIMINAR TODOS LOS REGISTROS (CON CONTRASEÑA)
# -----------------------------
elif opcion == "Eliminar Todos":
    st.subheader("⚠️ Eliminar Todos los Registros")
    clave = st.text_input("Contraseña", type="password")

    if st.button("Eliminar Todo"):
        if clave != "clave123":
            st.error("❌ Contraseña incorrecta")
        else:
            hoja_movimientos.clear()
            hoja_movimientos.append_row(["Código", "Estilo", "Cliente", "Estado"])
            st.success("✅ Todos los registros han sido eliminados.")
