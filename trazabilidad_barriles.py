import streamlit as st
import pandas as pd
import gspread
import json
from oauth2client.service_account import ServiceAccountCredentials
from gspread_dataframe import set_with_dataframe, get_as_dataframe
from datetime import date, datetime


# Configuración de Streamlit
st.set_page_config(page_title="Trazabilidad de Barriles", layout="centered")

st.markdown("<div style='font-size:48px; font-weight:bold; color:#2cc6c1; text-align:center;'>🍺 TRAZABILIDAD BARRILES CASTIZA</div>", unsafe_allow_html=True)
st.markdown("---")

# ----------------------------------------
# CONEXIÓN CON GOOGLE SHEETS USANDO st.secrets
# ----------------------------------------

SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
# Cargar credenciales desde st.secrets
cred_json = json.dumps(st.secrets["gcp_service_account"])
credentials = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(cred_json), SCOPE)
client = gspread.authorize(credentials)

# Abre la hoja de cálculo por URL o nombre. Aquí uso la URL para evitar problemas de nombres.
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1FjQ8XBDwDdrlJZsNkQ6YyaygkHLhpKmfLBv6wd3uluY/edit?gid=0"
sheet = client.open_by_url(SPREADSHEET_URL).sheet1
st.write("Mis secrets:", st.secrets)
# ----------------------------------------
# FUNCIONES AUXILIARES PARA GOOGLE SHEETS
# ----------------------------------------

def leer_registros():
    """Lee todos los registros desde la hoja y retorna un DataFrame."""
    registros = sheet.get_all_records()
    return pd.DataFrame(registros)

def guardar_registro(df_nuevo):
    """Agrega un nuevo registro (DataFrame con una fila) a la hoja de cálculo."""
    try:
        df_existente = leer_registros()
        df_actualizado = pd.concat([df_existente, df_nuevo], ignore_index=True)
    except Exception:
        df_actualizado = df_nuevo
    sheet.clear()
    set_with_dataframe(sheet, df_actualizado)

def eliminar_barril(codigo):
    """Elimina del registro el barril cuyo 'Código' coincida."""
    df = leer_registros()
    df_filtrado = df[df["Código"].astype(str).str.strip() != codigo.strip()]
    sheet.clear()
    set_with_dataframe(sheet, df_filtrado)

def eliminar_todo():
    """Elimina todos los registros dejando solo los encabezados."""
    encabezados = ["Fecha", "Código", "Capacidad", "Estilo", "Estado", "Cliente", "Responsable", "Observaciones"]
    sheet.clear()
    sheet.append_row(encabezados)

# ----------------------------------------
# INTERFAZ DE STREAMLIT
# ----------------------------------------

st.subheader("📋 Registro de Barril")

fecha_registro = st.date_input("Fecha", date.today())
codigo_barril = st.text_input("Código del barril")

# Validación del código según capacidad
capacidad = ""
codigo_valido = False
if codigo_barril.startswith("20") and len(codigo_barril) == 5:
    capacidad = "20L"
    codigo_valido = True
elif codigo_barril.startswith("30") and len(codigo_barril) == 5:
    capacidad = "30L"
    codigo_valido = True
elif codigo_barril.startswith("58") and len(codigo_barril) == 5:
    capacidad = "58L"
    codigo_valido = True

estilos = ["Golden", "Amber", "Vienna Lager", "Brown Ale Cafe", "Stout", 
           "Session IPA", "IPA", "Maracuya", "Barley Wine", "Trigo", "Catharina Sour", 
           "Gose", "Imperial IPA", "NEIPA", "Imperial Stout", "Otros"]
estilo_cerveza = st.selectbox("Estilo", estilos)
estado_barril = st.selectbox("Estado del barril", ["Despachado", "Lavado en bodega", "Sucio", "En cuarto frío"])

clientes = ["Castiza Av. Estudiantes", "Bendita Birra CC sebastian Belalcazar", "Baruk", "Sandona Plaza", "El Barril", "La estiba las cuadras", "La estiba Villaflor"]
cliente = "Planta Castiza"
if estado_barril == "Despachado":
    cliente = st.selectbox("Cliente", clientes)

responsables = ["Pepe Vallejo", "Ligia Cajigas", "Erika Martinez", "Marcelo Martinez", "Operario 1", "Operario 2"]
responsable = st.selectbox("Responsable", responsables)

observaciones = ""
if estado_barril == "Sucio":
    observaciones = f"Último cliente: {cliente}"
else:
    observaciones = st.text_area("Observaciones", "")

if st.button("Guardar Registro"):
    if codigo_barril and estado_barril and fecha_registro and responsable and codigo_valido:
        nuevo_registro = pd.DataFrame({
            "Fecha": [str(fecha_registro)],
            "Código": [codigo_barril],
            "Capacidad": [capacidad],
            "Estilo": [estilo_cerveza],
            "Estado": [estado_barril],
            "Cliente": [cliente],
            "Responsable": [responsable],
            "Observaciones": [observaciones]
        })
        guardar_registro(nuevo_registro)
        st.success("✅ Registro guardado correctamente en Google Sheets")
    else:
        if not codigo_valido:
            st.warning("⚠️ El código del barril no cumple con el formato esperado.")
        else:
            st.warning("⚠️ Por favor, completa los campos obligatorios")

# Reporte General
st.markdown("---")
st.subheader("📑 Reporte General")
df = leer_registros()
if not df.empty:
    st.dataframe(df)
else:
    st.info("No hay registros para mostrar aún")

# Buscar Barril
st.markdown("---")
st.subheader("🔍 Buscar estado por código")
codigo_busqueda = st.text_input("Ingrese código del barril para buscar")
if st.button("Buscar estado"):
    df = leer_registros()
    codigo_busqueda = codigo_busqueda.strip().zfill(5)
    df["Código"] = df["Código"].astype(str).str.strip().str.zfill(5)
    resultado = df[df["Código"] == codigo_busqueda]
    if not resultado.empty:
        st.success("✅ Barril encontrado:")
        st.dataframe(resultado)
    else:
        st.warning("No se encontró ningún barril con ese código")

# Borrar un Barril
st.markdown("---")
st.subheader("🔒 Borrar un barril específico")
with st.expander("Eliminar un barril por código (solo autorizado)"):
    password_uno = st.text_input("Contraseña para eliminar un barril:", type="password")
    codigo_borrar = st.text_input("Código del barril a eliminar")
    if st.button("Eliminar barril"):
        if password_uno == "Babel2021":
            eliminar_barril(codigo_borrar)
            st.success(f"✅ Se eliminó el barril con código {codigo_borrar}, si existía.")
        else:
            st.error("❌ Contraseña incorrecta. Acceso denegado.")

# Borrar Todos los Registros
st.markdown("---")
st.subheader("🔒 Borrar toda la información")
with st.expander("Eliminar registros (solo autorizado)"):
    password_todo = st.text_input("Introduce la contraseña para borrar todo:", type="password")
    if st.button("Borrar todo"):
        if password_todo == "Babel2021":
            eliminar_todo()
            st.success("✅ Todos los registros han sido eliminados correctamente.")
        else:
            st.error("❌ Contraseña incorrecta. Acceso denegado.")

# Descargar Reporte
st.markdown("---")
st.subheader("⬇️ Descargar Reporte")
df = leer_registros()
if not df.empty:
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(label="Descargar reporte en formato CSV", data=csv, file_name="registro_barriles.csv", mime="text/csv")
else:
    st.info("No hay registros disponibles para descargar.")



