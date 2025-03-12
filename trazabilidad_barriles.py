import streamlit as st
import pandas as pd
import os
import base64
from datetime import date
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from gspread_dataframe import set_with_dataframe


st.set_page_config(page_title="Trazabilidad de Barriles", layout="centered")
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto&display=swap');
    .stApp {
        font-family: 'Roboto', sans-serif;
        color: #ffffff;
        padding: 1rem;
        font-size: 18px !important;
    }
    </style>
""", unsafe_allow_html=True)

def add_bg_from_local(image_file):
    with open(image_file, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode()
    st.markdown(f"""
        <style>
        .stApp {{
            background-image: url("data:image/jpeg;base64,{encoded_string}");
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            background-attachment: fixed;
        }}
        </style>
    """, unsafe_allow_html=True)

# Puedes cambiar la imagen si deseas
if os.path.exists('images/image (2).jpg'):
    add_bg_from_local('images/image (2).jpg')

# Estilo general con logo y botones
st.markdown("""
    <style>
    .big-title {
        font-size: 48px !important;
        font-weight: bold;
        color: #2cc6c1;
        text-align: center;
        margin-bottom: 30px;
        text-shadow: 2px 2px 4px #000000;
    }
    .stButton > button {
        background-color: #2cc6c1 !important;
        color: white !important;
        border-radius: 12px;
        padding: 14px 28px;
        font-size: 22px;
        font-weight: bold;
        border: none;
        width: 100%;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        transition: 0.3s ease-in-out;
    }
    .stButton > button:hover {
        background-color: #1ba8a3 !important;
        transform: scale(1.03);
    }
    </style>
""", unsafe_allow_html=True)

st.markdown("<div class='big-title'>🍺 TRAZABILIDAD BARRILES CASTIZA</div>", unsafe_allow_html=True)

st.markdown("<h2 style='font-size:32px;'>📋 Registro de Barril</h2>", unsafe_allow_html=True)
fecha_registro = st.date_input("Fecha")
codigo_barril = st.text_input("Código del barril")

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

clientes = ["Castiza Av. Estudiantes", "Bendita Birra CC sebastian Belalcazar", "Baruk", "Sandona Plaza",
            "El Barril", "La estiba las cuadras", "La estiba Villaflor"]
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
            "Fecha": [fecha_registro],
            "Código": [codigo_barril],
            "Capacidad": [capacidad],
            "Estilo": [estilo_cerveza],
            "Estado": [estado_barril],
            "Cliente": [cliente],
            "Responsable": [responsable],
            "Observaciones": [observaciones]
        })
        from gspread_dataframe import get_as_dataframe, set_with_dataframe

        try:
                df_existente = get_as_dataframe(sheet, evaluate_formulas=True)
                df_existente = df_existente.dropna(how='all')
        except:
                df_existente = pd.DataFrame()

                df_actualizado = pd.concat([df_existente, nuevo_registro], ignore_index=True)
                sheet.clear()
                set_with_dataframe(sheet, df_actualizado)

            

    
# Abre tu hoja por URL o nombre
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1FjQ8XBDwDdrlJZsNkQ6YyaygkHLhpKmfLBv6wd3uluY/edit#gid=0"
sheet = client.open_by_url(SPREADSHEET_URL).sheet1

        st.success("✅ Registro guardado correctamente")
    else:
        if not codigo_valido:
            st.warning("⚠️ El código del barril no cumple con el formato esperado.")
        else:
            st.warning("⚠️ Por favor, completa los campos obligatorios")

st.markdown("---")
st.markdown("<h2 style='font-size:32px;'>📑 Reporte General</h2>", unsafe_allow_html=True)
if os.path.exists("registro_barriles.csv"):
    df = pd.read_csv("registro_barriles.csv")
    st.dataframe(df)
else:
    st.info("No hay registros para mostrar aún")

st.markdown("---")
st.markdown("<h2 style='font-size:32px;'>🔍 Buscar estado por código</h2>", unsafe_allow_html=True)
codigo_busqueda = st.text_input("Ingrese código del barril para buscar")
if st.button("Buscar estado"):
    if os.path.exists("registro_barriles.csv"):
        df = pd.read_csv("registro_barriles.csv")
        codigo_busqueda = codigo_busqueda.strip().zfill(5)
        df["Código"] = df["Código"].astype(str).str.strip().str.zfill(5)
        resultado = df[df["Código"] == codigo_busqueda]
        if not resultado.empty:
            st.write(resultado)
        else:
            st.warning("No se encontró ningún barril con ese código")
    else:
        st.info("No hay registros disponibles")

st.markdown("---")
st.markdown("<h2 style='font-size:32px;'>🔒 Borrar un barril específico</h2>", unsafe_allow_html=True)
with st.expander("Eliminar un barril por código (solo autorizado)"):
    password_uno = st.text_input("Contraseña para eliminar un barril:", type="password")
    codigo_borrar = st.text_input("Código del barril a eliminar")
    if st.button("Eliminar barril"):
        if password_uno == "Babel2021":
            if os.path.exists("registro_barriles.csv"):
                df = pd.read_csv("registro_barriles.csv")
                df_filtrado = df[df["Código"] != codigo_borrar]
                df_filtrado.to_csv("registro_barriles.csv", index=False)
                st.success(f"✅ Se eliminó el barril con código {codigo_borrar}, si existía.")
            else:
                st.warning("No hay registros para eliminar.")
        else:
            st.error("❌ Contraseña incorrecta. Acceso denegado.")

st.markdown("---")
st.markdown("<h2 style='font-size:32px;'>🔒 Borrar toda la información</h2>", unsafe_allow_html=True)
with st.expander("Eliminar registros (solo autorizado)"):
    password_todo = st.text_input("Introduce la contraseña para borrar todo:", type="password")
    if st.button("Borrar todo"):
        if password_todo == "Babel2021":
            if os.path.exists("registro_barriles.csv"):
                os.remove("registro_barriles.csv")
                st.success("✅ Todos los registros han sido eliminados correctamente.")
            else:
                st.warning("No hay registros para eliminar.")
        else:
            st.error("❌ Contraseña incorrecta. Acceso denegado.")
