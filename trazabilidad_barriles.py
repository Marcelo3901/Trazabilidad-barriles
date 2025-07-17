import streamlit as st
import pandas as pd
import requests
from urllib.parse import urlencode
import base64
import os
from datetime import datetime


# --- NUEVO: Función de validación de flujo de estados ---
def validar_flujo_estado(historial, nuevo_estado):
    orden_estados = ["Sucio", "Lavado en bodega", "En cuarto frío", "Despacho"]
    historial = historial[historial["Estado"].isin(orden_estados)]
    estados_previos = historial["Estado"].tolist()

    # Caso ya completó ciclo
    if estados_previos == orden_estados:
        return False, "⚠️ Este barril ya completó el ciclo completo. Debe iniciar nuevamente como 'Sucio'."

    # Inicio del flujo
    if not estados_previos:
        if nuevo_estado != "Sucio":
            return False, "⚠️ El barril debe comenzar en estado 'Sucio'."
    else:
        ultimo = estados_previos[-1]
        idx = orden_estados.index(ultimo)
        if idx + 1 >= len(orden_estados):
            return False, "⚠️ El barril ya completó el ciclo."
        esperado = orden_estados[idx + 1]
        if nuevo_estado != esperado:
            return False, f"⚠️ El siguiente estado debe ser '{esperado}', no '{nuevo_estado}'."

    # Evitar duplicados
    if nuevo_estado in estados_previos:
        return False, f"⚠️ El barril ya estuvo en estado '{nuevo_estado}'."

    return True, ""




# CONFIGURACIÓN DE LA PÁGINA
st.set_page_config(page_title="Trazabilidad Barriles Castiza", layout="centered")

# --- Lista de estilos global ---
estilos = ["Golden", "Amber", "Vienna Lager", "Brown Ale Cafe", "Stout",
           "Session IPA", "IPA", "Maracuyá", "Barley Wine", "Trigo", "Catharina Sour",
           "Gose", "Imperial IPA", "NEIPA", "Imperial Stout", "Otros"]

# IMAGEN DE FONDO PERSONALIZADA Y ESTILOS GENERALES
if os.path.exists("background.jpg"):
    with open("background.jpg", "rb") as img:
        encoded = base64.b64encode(img.read()).decode()
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Roboto&display=swap');
        html, body, [class*="st"]  {{
            font-family: 'Roboto', sans-serif;
            color: #fff3aa;
        }}
        .stApp {{
            background-image: url("data:image/jpeg;base64,{encoded}");
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            background-attachment: fixed;
        }}
        .stTextInput > div > div > input,
        .stSelectbox > div > div,
        .stTextArea > div > textarea {{
            background-color: #ffffff10 !important;
            color: #fff3aa !important;
            border-radius: 10px;
        }}
        .stButton > button {{
            background-color: #55dcad !important;
            color: #fff3aa !important;
            border: none;
            border-radius: 10px;
            font-weight: bold;
        }}
        .stDataFrame, .stTable {{
            background-color: rgba(0,0,0,0.6);
            border-radius: 10px;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

# TÍTULO PRINCIPAL
st.markdown("<h1 style='text-align:center; color:#fff3aa;'>🍺 Sistema de Trazabilidad de Barriles y Latas - Castiza</h1>", unsafe_allow_html=True)

import streamlit as st
import pandas as pd
import requests

# ---------- TÍTULO ----------
st.markdown("<h2 style='color:#fff3aa;'>📋🛢️ Registro Movimiento Barriles</h2>", unsafe_allow_html=True)

# ---------- SELECCIÓN ESTADO DEL BARRIL ----------
estado_barril = st.selectbox("Estado del barril", ["Despacho", "Lavado en bodega", "Sucio", "En cuarto frío"])

# ---------- INGRESO CÓDIGO DEL BARRIL ----------
codigo_barril = ""
if estado_barril:
    codigo_barril = st.text_input("Código del barril (Debe tener 5 dígitos y empezar por 20, 30 o 58)", value="").strip()

# ---------- INGRESO DE LOTE Y ESTILO SI ESTÁ EN CUARTO FRÍO ----------
lote_producto = ""
estilo_cerveza = ""

if estado_barril == "En cuarto frío":
    lote_producto = st.text_input("Lote del producto (9 dígitos - formato DDMMYYXXX)")
    estilos = ["Golden", "Amber", "Vienna Lager", "Brown Ale Cafe", "Stout", "Session IPA", "IPA", "Maracuyá",
               "Barley Wine", "Trigo", "Catharina Sour", "Gose", "Imperial IPA", "NEIPA", "Imperial Stout", "Otros"]
    estilo_cerveza = st.selectbox("Estilo", estilos)

# ---------- AUTOCOMPLETAR LOTE Y ESTILO + CONTROL DE CICLO SI EL ESTADO ES DESPACHO ----------
if estado_barril == "Despacho" and codigo_barril:
    try:
        url_datos = "https://docs.google.com/spreadsheets/d/1FjQ8XBDwDdrlJZsNkQ6YyaygkHLhpKmfLBv6wd3uluY/gviz/tq?tqx=out:csv&sheet=DatosM"
        df_datos = pd.read_csv(url_datos)

        # Limpieza de columnas
        df_datos.columns = df_datos.columns.str.strip()

        # Convertir 'Código' a string sin decimales (eliminar .0)
        if "Código" in df_datos.columns:
            df_datos["Código"] = df_datos["Código"].apply(lambda x: str(int(float(x))) if pd.notnull(x) else "").str.strip()

        # Asegurarse de que Estado también esté limpio
        if "Estado" in df_datos.columns:
            df_datos["Estado"] = df_datos["Estado"].astype(str).str.strip()

        # ➕ Validar si el último estado de ese barril fue "Despacho"
        historial_barril = df_datos[df_datos["Código"] == codigo_barril]
        if not historial_barril.empty:
            ultimo_estado = historial_barril.iloc[-1]["Estado"]

            if ultimo_estado == "Despacho":
                st.error("🚫 Este barril ya fue despachado previamente. Debe pasar primero por 'Lavado en bodega' antes de volver a despacharse.")
            else:
                # Autocompletar Lote y Estilo si hay registros previos en "En cuarto frío"
                df_cuarto_frio = historial_barril[historial_barril["Estado"] == "En cuarto frío"]
                if not df_cuarto_frio.empty:
                    ultimo_cf = df_cuarto_frio.iloc[-1]
                    lote_producto = ultimo_cf.get("Lote", "No disponible")
                    estilo_cerveza = ultimo_cf.get("Estilo", "No disponible")
                    st.success(f"✅ Lote asignado automáticamente: {lote_producto}")
                    st.success(f"✅ Estilo asignado automáticamente: {estilo_cerveza}")
                else:
                    st.warning("⚠️ No se encontró un registro anterior en 'En cuarto frío' para este barril. Se asignó 'No disponible'.")
                    lote_producto = "No disponible"
                    estilo_cerveza = "No disponible"
        else:
            st.warning("⚠️ Este barril no tiene historial previo. Se permitirá el despacho inicial.")
            lote_producto = "No disponible"
            estilo_cerveza = "No disponible"

    except Exception as e:
        st.warning(f"⚠️ No se pudo consultar registros previos: {e}")
        lote_producto = "No disponible"
        estilo_cerveza = "No disponible"


# ---------- AJUSTE: CAMBIAR ESTADO A 'Vacío' si se selecciona 'Sucio' o 'Lavado en bodega' ----------
estado_para_guardar = estado_barril
if estado_barril in ["Sucio", "Lavado en bodega"]:
    estado_para_guardar = "Vacío"
    st.info("ℹ️ Estado registrado como Vacío para este barril.")

# ---------- CARGAR CLIENTES DESDE GOOGLE SHEETS ----------
try:
    url_clientes = "https://docs.google.com/spreadsheets/d/1FjQ8XBDwDdrlJZsNkQ6YyaygkHLhpKmfLBv6wd3uluY/gviz/tq?tqx=out:csv&sheet=Rclientes"
    df_clientes = pd.read_csv(url_clientes)
    df_clientes.columns = df_clientes.columns.str.strip()
    df_clientes.dropna(subset=["Nombre"], inplace=True)
    df_clientes = df_clientes[df_clientes["Nombre"].str.strip() != ""]
    lista_clientes = df_clientes["Nombre"].dropna().astype(str).tolist()
    dict_direcciones = df_clientes.set_index("Nombre")["Dirección"].to_dict()
except Exception as e:
    lista_clientes = []
    dict_direcciones = {}
    st.warning(f"⚠️ No se pudieron cargar los clientes: {e}")

# ---------- SELECCIÓN DE CLIENTE Y AUTOCOMPLETADO DE DIRECCIÓN ----------
cliente = "Planta Castiza"
direccion_cliente = ""
if estado_barril == "Despacho" and lista_clientes:
    cliente = st.selectbox("Cliente", lista_clientes)
    direccion_cliente = dict_direcciones.get(cliente, "")
    st.text_input("Dirección del cliente", value=direccion_cliente, disabled=True)

# ---------- DESPACHO DE LATAS (DINÁMICO) ----------
latas = []
incluye_latas = "No"

if estado_barril == "Despacho":
    incluye_latas = st.selectbox("¿🚚 Incluye despacho de latas?", ["No", "Sí"])
    if incluye_latas == "Sí":
        st.markdown("<h4 style='color:#fff3aa;'>🚚 Detalles de despacho de latas</h4>", unsafe_allow_html=True)

        if "num_latas" not in st.session_state:
            st.session_state.num_latas = 1

        for i in range(st.session_state.num_latas):
            st.markdown(f"**[ORDEN {i+1}]**")
            cantidad = st.number_input(f"Cantidad (Orden {i+1})", min_value=1, key=f"cantidad_lata_{i}")
            lote = st.text_input(f"Lote (Orden {i+1})", key=f"lote_lata_{i}")
            latas.append((cantidad, lote))

        if st.button("➕ Agregar lata diferente lote"):
            st.session_state.num_latas += 1

# ---------- RESPONSABLE Y OBSERVACIONES ----------
responsables = ["Pepe Vallejo", "Ligia Cajigas", "Erika Martinez", "Marcelo Martinez", "Yimer Luna", "Operario 2"]
responsable = st.selectbox("Responsable", responsables)
observaciones = st.text_area("Observaciones")

# ---------- GUARDAR FORMULARIO ----------
if st.button("Guardar Registro"):
    if not codigo_barril.strip():
        st.warning("⚠️ Debes ingresar un código de barril antes de enviar el formulario.")
    else:
        # Enviar formulario principal
        form_url = "https://docs.google.com/forms/d/e/1FAIpQLSedFQmZuDdVY_cqU9WdiWCTBWCCh1NosPnD891QifQKqaeUfA/formResponse"
        payload = {
            "entry.311770370": codigo_barril,
            "entry.1283669263": estilo_cerveza,
            "entry.1545499818": estado_barril,
            "entry.91059345": cliente,
            "entry.1661747572": responsable,
            "entry.1465957833": observaciones,
            "entry.1234567890": lote_producto if estado_barril in ["Despacho", "En cuarto frío"] else "",
            "entry.1122334455": incluye_latas,
            "entry.1437332932": lote_producto
        }
        response = requests.post(form_url, data=payload)
        if response.status_code in [200, 302]:
            st.success("✅ Registro enviado correctamente")
            st.balloons()
        else:
            st.error(f"❌ Error al enviar el formulario. Código: {response.status_code}")

        # Enviar formulario de latas (si corresponde)
        if incluye_latas == "Sí" and latas:
            form_latas_url = "https://docs.google.com/forms/d/e/1FAIpQLSerxxOI1npXAptsa3nvNNBFHYBLV9OMMX-4-Xlhz-VOmitRfQ/formResponse"
            for idx, (cant, lot) in enumerate(latas):
                payload_latas = {
                    "entry.457965266": str(cant),
                    "entry.689047838": estilo_cerveza,
                    "entry.2096096606": lot,
                    "entry.1478892985": cliente,
                    "entry.1774006398": responsable
                }
                r_latas = requests.post(form_latas_url, data=payload_latas)
                if r_latas.status_code not in [200, 302]:
                    st.warning(f"❌ Error al enviar lata {idx+1}. Código: {r_latas.status_code}")

# FORMULARIO NUEVO CLIENTE
st.markdown("---")
st.markdown("<h2 style='color:#fff3aa;'>➕ Registrar Nuevo Cliente</h2>", unsafe_allow_html=True)

nuevo_cliente = st.text_input("Nombre del nuevo cliente")
direccion_nuevo_cliente = st.text_input("Dirección del cliente")

if st.button("Agregar Cliente"):
    if nuevo_cliente.strip() != "":
        form_cliente_url = "https://docs.google.com/forms/d/e/1FAIpQLScllMMM33p5F--_I6Y80gsLUsusGMTk0OA3XDVC9ocngoc2Hw/formResponse"
        payload_cliente = {
            "entry.1250409245": nuevo_cliente,
            "entry.82359015": direccion_nuevo_cliente
        }
        response = requests.post(form_cliente_url, data=payload_cliente)
        if response.status_code in [200, 302]:
            st.success("✅ Cliente agregado correctamente")
        else:
            st.error(f"❌ Error al agregar cliente. Código: {response.status_code}")

# ----------------------------------------
# ÚLTIMOS MOVIMIENTOS
# ----------------------------------------
st.markdown("---")
st.markdown("<h2 style='color:#fff3aa;'>📑 Últimos 10 Movimientos</h2>", unsafe_allow_html=True)

try:
    url_datos = "https://docs.google.com/spreadsheets/d/1FjQ8XBDwDdrlJZsNkQ6YyaygkHLhpKmfLBv6wd3uluY/gviz/tq?tqx=out:csv&sheet=DatosM"
    df_mov = pd.read_csv(url_datos)
    df_mov.columns = df_mov.columns.str.strip()
    if not df_mov.empty:
        df_mov = df_mov[df_mov["Código"].notna()]
        st.dataframe(df_mov.tail(10)[["Código", "Estilo", "Estado", "Cliente", "Responsable", "Observaciones"]])
    else:
        st.warning("⚠️ La hoja está vacía.")
except Exception as e:
    st.error(f"⚠️ No se pudo cargar la hoja de movimientos: {e}")

# FORMULARIO PARA INGRESAR LATAS AL CUARTO FRÍO
st.markdown("---")
st.markdown("<h2 style='color:#fff3aa;'>❄️ Ingreso de Latas al Cuarto Frío</h2>", unsafe_allow_html=True)
estilo_lata_cf = st.selectbox("Estilo de las latas", estilos, key="estilo_cf")
cantidad_lata_cf = st.number_input("Cantidad de latas", min_value=1, key="cantidad_cf")
lote_lata_cf = st.text_input("Lote", key="lote_cf")

if st.button("Guardar Ingreso de Latas al Cuarto Frío"):
    # ✅ URL CORRECTA para enviar POST
    form_cf_url = "https://docs.google.com/forms/d/e/1FAIpQLScWQqIe6atpchC8I4nxFRxzLa17AgQfA4v1v86Gtz_3nYg60Q/formResponse"

    # ✅ Asegúrate que estos entry IDs SON LOS CORRECTOS
    payload_cf = {
        "entry.1771049143": estilo_lata_cf,
        "entry.251410382": str(cantidad_lata_cf),
        "entry.122481390": lote_lata_cf,
        "entry.268194084": responsable
    }

    response = requests.post(form_cf_url, data=payload_cf)

    if response.status_code in [200, 302]:
        st.success("✅ Ingreso de latas al cuarto frío guardado correctamente")
        st.balloons()
    else:
        st.error(f"❌ Error al guardar ingreso al cuarto frío. Código: {response.status_code}")

# BUSCAR REGISTROS
# ----------------------------------------
st.markdown("---")
st.markdown("<h2 style='color:#fff3aa;'>🔍 Buscar Barriles</h2>", unsafe_allow_html=True)

try:
    df_search = pd.read_csv(url_datos)
    df_search.columns = df_search.columns.str.strip()

    filtro_codigo = st.text_input("🔎 Buscar por código de barril")
    filtro_cliente = st.text_input("🔎 Buscar por cliente")
    filtro_estado = st.selectbox("🔎 Buscar por estado", ["", "Despachado", "Lavado en bodega", "Sucio", "En cuarto frío"])

    df_filtrado = df_search.copy()
    if filtro_codigo:
        df_filtrado = df_filtrado[df_filtrado["Código"].astype(str).str.contains(filtro_codigo)]
    if filtro_cliente:
        df_filtrado = df_filtrado[df_filtrado["Cliente"].astype(str).str.contains(filtro_cliente, case=False)]
    if filtro_estado:
        df_filtrado = df_filtrado[df_filtrado["Estado"] == filtro_estado]

    if not df_filtrado.empty:
        st.dataframe(df_filtrado[["Código", "Estilo", "Estado", "Cliente", "Responsable", "Observaciones"]])
    else:
        st.warning("⚠️ No se encontraron registros con los filtros aplicados.")

except Exception as e:
    st.error(f"⚠️ No se pudo cargar la hoja de búsqueda: {e}")
           
# ------------------ FORMULARIO GENERAL ------------------
tipo_devolucion = st.selectbox("Selecciona tipo de devolución:", ["", "Barril", "Latas"])
cliente = st.text_input("Cliente que devuelve")
responsable = st.text_input("Responsable que recibe")
observaciones = st.text_area("Observaciones (opcional)")
fecha_actual = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

# ------------------ CAMPOS ESPECÍFICOS ------------------
if tipo_devolucion == "Barril":
    codigo_barril = st.text_input("Código del barril")
    estilo_cerveza = st.text_input("Estilo de cerveza (opcional)")
    lote_producto = st.text_input("Lote del producto (opcional)")

elif tipo_devolucion == "Latas":
    cantidad_latas = st.number_input("Cantidad de latas devueltas", min_value=1, step=1)
    estilo_cerveza = st.text_input("Estilo de cerveza")
    lote_latas = st.text_input("Lote de producto")

# ------------------ BOTÓN DE ENVÍO ------------------
if st.button("Registrar devolución"):
    if tipo_devolucion == "Barril":
        try:
            # ✅ URL del formulario de Google Forms para barriles
            url_form_barril = "https://docs.google.com/forms/d/e/1FAIpQLSedFQmZuDdVY_cqU9WdiWCTBWCCh1NosPnD891QifQKqaeUfA/formResponse"

            # 📤 Datos a enviar (asegúrate que los entry.xxx coincidan con tu formulario real)
            form_data_barril = {
                "entry.311770370": codigo_barril,          # Código del barril
                "entry.1283669263": estilo_cerveza,        # Estilo (opcional)
                "entry.1545499818": "Devolución",          # Estado fijo al devolver
                "entry.91059345": cliente,                 # Cliente
                "entry.1661747572": responsable,           # Responsable
                "entry.1465957833": observaciones,         # Observaciones
                "entry.1234567890": lote_producto,         # Lote (opcional, cambia si tienes otro ID)
                "entry.1437332932": lote_producto          # Lote repetido si tu formulario lo necesita
            }

            response = requests.post(url_form_barril, data=form_data_barril)

            if response.status_code in [200, 302]:
                st.success("✅ Devolución de barril registrada correctamente.")
            else:
                st.warning(f"⚠️ Error al enviar devolución. Código: {response.status_code}")
        except Exception as e:
            st.error(f"❌ Error al registrar devolución de barril: {e}")

    elif tipo_devolucion == "Latas":
        try:
            url_form_latas = "https://docs.google.com/forms/d/e/1FAIpQLSerxxOI1npXAptsa3nvNNBFHYBLV9OMMX-4-Xlhz-VOmitRfQ/formResponse"

            form_data_latas = {
                "entry.457965266": str(cantidad_latas),        # Cantidad
                "entry.689047838": estilo_cerveza,             # Estilo
                "entry.2096096606": lote_latas,                # Lote
                "entry.1478892985": cliente,                   # Cliente
                "entry.1774006398": responsable,               # Responsable
                "entry.1179145668": "Devolución"               # NUEVO CAMPO - Tipo de movimiento
            }

            response = requests.post(url_form_latas, data=form_data_latas)
            if response.status_code in [200, 302]:
                st.success("✅ Devolución de latas registrada correctamente.")
                st.toast("🍺 Devolución registrada")
            else:
                st.warning(f"⚠️ Error al enviar devolución. Código: {response.status_code}")
        except Exception as e:
            st.error(f"❌ Error al registrar devolución de latas: {e}")

# ------------------ REGISTRO DE BAJA DE PRODUCTO ------------------
st.markdown("---")
st.title("🗑️ Registro de Baja de Producto (Barril o Latas)")

tipo_baja = st.selectbox("Selecciona tipo de baja:", ["", "Barril", "Latas"])
responsable_baja = st.text_input("Responsable que da de baja")
observaciones_baja = st.text_area("Observaciones de baja (opcional)")
fecha_actual_baja = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

# Campos específicos
if tipo_baja == "Barril":
    codigo_barril_baja = st.text_input("Código del barril a dar de baja")
    estilo_baja_barril = st.text_input("Estilo de cerveza (opcional)")
    lote_barril_baja = st.text_input("Lote del producto (opcional)")

elif tipo_baja == "Latas":
    cantidad_latas_baja = st.number_input("Cantidad de latas a dar de baja", min_value=1, step=1)
    estilo_latas_baja = st.text_input("Estilo de cerveza")
    lote_latas_baja = st.text_input("Lote del producto")

# Botón para registrar baja
if st.button("Registrar Baja de Producto"):

    if tipo_baja == "Barril":
        try:
            url_form_barril_baja = "https://docs.google.com/forms/d/e/1FAIpQLSedFQmZuDdVY_cqU9WdiWCTBWCCh1NosPnD891QifQKqaeUfA/formResponse"

            form_data_baja_barril = {
                "entry.311770370": codigo_barril_baja,                      # Código del barril
                "entry.1283669263": estilo_baja_barril,                    # Estilo
                "entry.1545499818": "Baja",                                # Estado automático "Baja"
                "entry.1661747572": responsable_baja,                      # Responsable
                "entry.1465957833": observaciones_baja,                    # Observaciones
                "entry.1234567890": lote_barril_baja,                      # Lote (opcional)
                "entry.1437332932": lote_barril_baja                       # Repetido si es necesario
            }

            response = requests.post(url_form_barril_baja, data=form_data_baja_barril)
            if response.status_code in [200, 302]:
                st.success("✅ Baja de barril registrada correctamente.")
                st.balloons()
            else:
                st.warning(f"⚠️ Error al registrar baja. Código: {response.status_code}")
        except Exception as e:
            st.error(f"❌ Error al registrar baja de barril: {e}")

    elif tipo_baja == "Latas":
        try:
            url_form_latas_baja = "https://docs.google.com/forms/d/e/1FAIpQLSerxxOI1npXAptsa3nvNNBFHYBLV9OMMX-4-Xlhz-VOmitRfQ/formResponse"

            form_data_baja_latas = {
                "entry.457965266": str(cantidad_latas_baja),              # Cantidad
                "entry.689047838": estilo_latas_baja,                     # Estilo
                "entry.2096096606": lote_latas_baja,                      # Lote
                "entry.1774006398": responsable_baja,                     # Responsable
                "entry.1179145668": "Baja"                                # Campo adicional para indicar baja
            }

            response = requests.post(url_form_latas_baja, data=form_data_baja_latas)
            if response.status_code in [200, 302]:
                st.success("✅ Baja de latas registrada correctamente.")
                st.snow()
            else:
                st.warning(f"⚠️ Error al registrar baja. Código: {response.status_code}")
        except Exception as e:
            st.error(f"❌ Error al registrar baja de latas: {e}")
