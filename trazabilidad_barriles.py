import streamlit as st
import pandas as pd
import requests
from urllib.parse import quote
import base64
import os
from datetime import datetime
import unicodedata
import hashlib
import html as html_lib
import io
import json
import re
import time
import uuid
from copy import copy

from openpyxl import load_workbook


# La validación de estados se realiza justo antes de guardar y nuevamente en Apps Script.

# CONFIGURACIÓN DE LA PÁGINA
st.set_page_config(page_title="Trazabilidad Barriles Castiza", layout="centered")


# ---------- CONFIGURACIÓN DE GOOGLE SHEETS PARA INVENTARIO DE LATAS ----------
SPREADSHEET_ID = "1FjQ8XBDwDdrlJZsNkQ6YyaygkHLhpKmfLBv6wd3uluY"
HOJA_INGRESOS_LATAS = "IngresoLatas"
HOJA_MOVIMIENTOS_LATAS = "VLatas"


def normalizar_clave(valor):
    """Normaliza texto para comparar estilos, lotes y estados sin errores de mayúsculas o tildes."""
    if pd.isna(valor):
        return ""
    texto = " ".join(str(valor).strip().split())
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(caracter for caracter in texto if not unicodedata.combining(caracter))
    return texto.casefold()


def limpiar_cantidades(serie):
    """Convierte cantidades de latas a enteros y elimina separadores de miles."""
    texto = serie.fillna("").astype(str).str.strip()
    texto = texto.str.replace(r"[^0-9-]", "", regex=True)
    return pd.to_numeric(texto, errors="coerce").fillna(0).astype(int)


@st.cache_data(ttl=30, show_spinner=False)
def cargar_hoja_csv(nombre_hoja):
    """Carga una pestaña pública del Google Sheet y conserva el resultado por 30 segundos."""
    url = (
        f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq"
        f"?tqx=out:csv&sheet={quote(nombre_hoja)}"
    )
    try:
        df = pd.read_csv(url)
    except pd.errors.EmptyDataError:
        return pd.DataFrame()

    df.columns = df.columns.astype(str).str.strip()
    return df


def calcular_inventario_latas():
    """
    Calcula inventario por estilo y lote:
    IngresoLatas - VLatas.

    En VLatas:
    - Despacho, Baja o Estado vacío: restan inventario.
    - Devolución: vuelve a sumar inventario.
    """
    ingresos = cargar_hoja_csv(HOJA_INGRESOS_LATAS).copy()
    movimientos = cargar_hoja_csv(HOJA_MOVIMIENTOS_LATAS).copy()

    columnas_necesarias = {"Estilo", "Cantidad", "Lote"}
    faltantes_ingresos = columnas_necesarias.difference(ingresos.columns)
    if faltantes_ingresos:
        raise ValueError(
            f"Faltan columnas en {HOJA_INGRESOS_LATAS}: {', '.join(sorted(faltantes_ingresos))}"
        )

    # VLatas puede estar sin registros, pero debe conservar sus encabezados.
    if movimientos.empty and not columnas_necesarias.issubset(movimientos.columns):
        movimientos = pd.DataFrame(columns=["Estilo", "Cantidad", "Lote", "Estado"])

    faltantes_movimientos = columnas_necesarias.difference(movimientos.columns)
    if faltantes_movimientos:
        raise ValueError(
            f"Faltan columnas en {HOJA_MOVIMIENTOS_LATAS}: "
            f"{', '.join(sorted(faltantes_movimientos))}"
        )

    ingresos["Estilo"] = ingresos["Estilo"].fillna("").astype(str).str.strip()
    ingresos["Lote"] = ingresos["Lote"].fillna("").astype(str).str.strip().str.upper()
    ingresos["Cantidad"] = limpiar_cantidades(ingresos["Cantidad"])
    ingresos["_estilo_key"] = ingresos["Estilo"].map(normalizar_clave)
    ingresos["_lote_key"] = ingresos["Lote"].map(normalizar_clave)
    ingresos = ingresos[
        (ingresos["_estilo_key"] != "")
        & (ingresos["_lote_key"] != "")
        & (ingresos["Cantidad"] != 0)
    ]

    ingresos_agrupados = (
        ingresos.groupby(["_estilo_key", "_lote_key"], as_index=False)
        .agg(
            Estilo=("Estilo", "last"),
            Lote=("Lote", "last"),
            Ingresado=("Cantidad", "sum"),
        )
    )

    movimientos["Estilo"] = movimientos["Estilo"].fillna("").astype(str).str.strip()
    movimientos["Lote"] = movimientos["Lote"].fillna("").astype(str).str.strip().str.upper()
    movimientos["Cantidad"] = limpiar_cantidades(movimientos["Cantidad"])
    movimientos["_estilo_key"] = movimientos["Estilo"].map(normalizar_clave)
    movimientos["_lote_key"] = movimientos["Lote"].map(normalizar_clave)

    if "Estado" in movimientos.columns:
        movimientos["_estado_key"] = movimientos["Estado"].map(normalizar_clave)
    else:
        movimientos["_estado_key"] = ""

    # Al restar un movimiento negativo, una devolución vuelve a sumar existencias.
    movimientos["Movimiento_neto"] = movimientos["Cantidad"]
    es_devolucion = movimientos["_estado_key"].eq("devolucion")
    movimientos.loc[es_devolucion, "Movimiento_neto"] *= -1

    movimientos = movimientos[
        (movimientos["_estilo_key"] != "")
        & (movimientos["_lote_key"] != "")
        & (movimientos["Movimiento_neto"] != 0)
    ]

    movimientos_agrupados = (
        movimientos.groupby(["_estilo_key", "_lote_key"], as_index=False)["Movimiento_neto"]
        .sum()
    )

    inventario = ingresos_agrupados.merge(
        movimientos_agrupados,
        on=["_estilo_key", "_lote_key"],
        how="left",
    )
    inventario["Movimiento_neto"] = inventario["Movimiento_neto"].fillna(0).astype(int)
    inventario["Disponible"] = inventario["Ingresado"] - inventario["Movimiento_neto"]
    inventario["Disponible"] = inventario["Disponible"].astype(int)

    # Solo se ofrecen lotes que todavía tienen unidades disponibles.
    inventario = inventario[inventario["Disponible"] > 0].copy()
    inventario.sort_values(["Estilo", "Lote"], inplace=True, key=lambda s: s.astype(str).str.casefold())
    inventario.reset_index(drop=True, inplace=True)
    return inventario


def validar_existencias_latas(latas_solicitadas, inventario):
    """Valida el total solicitado por estilo/lote, incluso si el mismo lote se repite en varias órdenes."""
    if not latas_solicitadas:
        return ["Debes completar al menos una orden de latas."]

    pedido = pd.DataFrame(latas_solicitadas).copy()
    pedido["_estilo_key"] = pedido["estilo"].map(normalizar_clave)
    pedido["_lote_key"] = pedido["lote"].map(normalizar_clave)
    pedido_agrupado = (
        pedido.groupby(["_estilo_key", "_lote_key"], as_index=False)
        .agg(
            Estilo=("estilo", "last"),
            Lote=("lote", "last"),
            Solicitado=("cantidad", "sum"),
        )
    )

    disponibles = inventario[["_estilo_key", "_lote_key", "Disponible"]].copy()
    comparacion = pedido_agrupado.merge(
        disponibles,
        on=["_estilo_key", "_lote_key"],
        how="left",
    )
    comparacion["Disponible"] = comparacion["Disponible"].fillna(0).astype(int)

    errores = []
    for fila in comparacion.itertuples(index=False):
        if int(fila.Solicitado) > int(fila.Disponible):
            errores.append(
                f"{fila.Estilo} / lote {fila.Lote}: solicitaste {int(fila.Solicitado)} "
                f"y solo hay {int(fila.Disponible)} disponibles."
            )
    return errores


# ---------- SEGURIDAD E IDEMPOTENCIA PARA MOVIMIENTOS DE BARRILES ----------
HOJA_BARRILES = "DatosM"
HOJA_CLIENTES = "RClientes"
FORM_BARRILES_URL = "https://docs.google.com/forms/d/e/1FAIpQLSedFQmZuDdVY_cqU9WdiWCTBWCCh1NosPnD891QifQKqaeUfA/formResponse"
FORM_LATAS_URL = "https://docs.google.com/forms/d/e/1FAIpQLSerxxOI1npXAptsa3nvNNBFHYBLV9OMMX-4-Xlhz-VOmitRfQ/formResponse"
URL_DATOS_BARRILES_PUBLICA = (
    f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq"
    f"?tqx=out:csv&sheet={quote(HOJA_BARRILES)}"
)


def leer_secreto(nombre):
    """Lee un secreto sin impedir que la app arranque cuando aún no existe secrets.toml."""
    try:
        valor = st.secrets.get(nombre, "")
    except Exception:
        return ""
    return "" if valor is None else str(valor).strip()


APPS_SCRIPT_MOVIMIENTOS_URL = leer_secreto("APPS_SCRIPT_MOVIMIENTOS_URL")
APPS_SCRIPT_MOVIMIENTOS_TOKEN = leer_secreto("APPS_SCRIPT_MOVIMIENTOS_TOKEN")
BACKEND_SEGURO_ACTIVO = bool(
    APPS_SCRIPT_MOVIMIENTOS_URL and APPS_SCRIPT_MOVIMIENTOS_TOKEN
)


def normalizar_codigo_barril(valor):
    """Convierte códigos numéricos de Sheets (por ejemplo 30275.0) a texto limpio."""
    if pd.isna(valor):
        return ""
    texto = str(valor).strip()
    if re.fullmatch(r"\d+\.0+", texto):
        texto = texto.split(".", 1)[0]
    return texto


def combinar_columnas(df, candidatos):
    """Combina columnas duplicadas de Google Sheets conservando el primer valor no vacío."""
    salida = pd.Series("", index=df.index, dtype="object")
    for nombre in candidatos:
        if nombre not in df.columns:
            continue
        valores = df[nombre].fillna("").astype(str).str.strip()
        vacios = salida.fillna("").astype(str).str.strip().eq("")
        salida.loc[vacios & valores.ne("")] = valores.loc[vacios & valores.ne("")]
    return salida


def convertir_fechas_sheet(serie):
    """Admite fechas DD/MM/AAAA y números seriales de Google Sheets."""
    texto = serie.fillna("").astype(str).str.strip()
    fechas = pd.to_datetime(texto, dayfirst=True, errors="coerce")
    numeros = pd.to_numeric(texto.str.replace(",", ".", regex=False), errors="coerce")
    seriales = fechas.isna() & numeros.between(20000, 80000, inclusive="both")
    if seriales.any():
        fechas.loc[seriales] = pd.to_datetime(
            numeros.loc[seriales], unit="D", origin="1899-12-30", errors="coerce"
        )
    return fechas


def preparar_datos_barriles(df_original):
    """Deja una sola estructura de columnas aunque DatosM tenga encabezados repetidos."""
    if df_original is None or df_original.empty:
        return pd.DataFrame(
            columns=[
                "Marca temporal", "Código", "Lote", "Estilo", "Estado", "Cliente",
                "Responsable", "Observaciones", "Operación ID", "_estado_key", "_orden_fila"
            ]
        )

    df = df_original.copy()
    df.columns = df.columns.astype(str).str.strip()
    salida = pd.DataFrame(index=df.index)
    salida["Marca temporal"] = combinar_columnas(
        df, ["Marca temporal", "Marca temporal.1"]
    )
    salida["Código"] = combinar_columnas(df, ["Código", "Codigo", "Código.1", "Codigo.1"])
    salida["Lote"] = combinar_columnas(
        df, ["Lote", "lote", "Lote.1", "lote.1"]
    )
    salida["Estilo"] = combinar_columnas(df, ["Estilo", "Estilo.1"])
    salida["Estado"] = combinar_columnas(df, ["Estado", "Estado.1"])
    salida["Cliente"] = combinar_columnas(df, ["Cliente", "Cliente.1"])
    salida["Responsable"] = combinar_columnas(df, ["Responsable", "Responsable.1"])
    salida["Observaciones"] = combinar_columnas(
        df, ["Observaciones", "Observaciones.1"]
    )
    salida["Operación ID"] = combinar_columnas(
        df,
        [
            "Operación ID", "Operacion ID", "Operación ID.1", "Operacion ID.1",
            "ID Operación", "ID Operacion"
        ],
    )

    salida["Código"] = salida["Código"].map(normalizar_codigo_barril)
    salida["Marca temporal"] = convertir_fechas_sheet(salida["Marca temporal"])
    salida["Lote"] = salida["Lote"].fillna("").astype(str).str.strip()
    salida["Estilo"] = salida["Estilo"].fillna("").astype(str).str.strip()
    salida["Estado"] = salida["Estado"].fillna("").astype(str).str.strip()
    salida["Cliente"] = salida["Cliente"].fillna("").astype(str).str.strip()
    salida["Responsable"] = salida["Responsable"].fillna("").astype(str).str.strip()
    salida["Observaciones"] = salida["Observaciones"].fillna("").astype(str).str.strip()
    salida["Operación ID"] = salida["Operación ID"].fillna("").astype(str).str.strip()
    salida["_estado_key"] = salida["Estado"].map(normalizar_clave)
    salida["_orden_fila"] = range(len(salida))
    return salida


def cargar_csv_publico_fresco(nombre_hoja, timeout=30):
    """Consulta la hoja sin caché para validar el estado real antes de guardar."""
    nonce = int(time.time() * 1000)
    url = (
        f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq"
        f"?tqx=out:csv&sheet={quote(nombre_hoja)}&_={nonce}"
    )
    respuesta = requests.get(
        url,
        timeout=timeout,
        headers={"Cache-Control": "no-cache", "Pragma": "no-cache"},
    )
    respuesta.raise_for_status()
    try:
        df = pd.read_csv(io.StringIO(respuesta.text))
    except pd.errors.EmptyDataError:
        return pd.DataFrame()
    df.columns = df.columns.astype(str).str.strip()
    return df


@st.cache_data(ttl=10, show_spinner=False)
def cargar_datos_barriles_ui():
    """Carga rápida para construir la interfaz; al guardar siempre se consulta de nuevo."""
    return preparar_datos_barriles(cargar_csv_publico_fresco(HOJA_BARRILES))


def cargar_datos_barriles_frescos():
    return preparar_datos_barriles(cargar_csv_publico_fresco(HOJA_BARRILES))


def obtener_ultimos_movimientos(df):
    """Obtiene la última fila registrada de cada código, usando el orden real de la hoja."""
    if df is None or df.empty:
        return pd.DataFrame(columns=df.columns if isinstance(df, pd.DataFrame) else [])
    validos = df[df["Código"].astype(str).str.strip().ne("")].copy()
    if validos.empty:
        return validos
    validos.sort_values("_orden_fila", inplace=True)
    return validos.drop_duplicates(subset="Código", keep="last").copy()


def obtener_ultimo_movimiento(df, codigo):
    codigo = normalizar_codigo_barril(codigo)
    if not codigo or df is None or df.empty:
        return None
    historial = df[df["Código"] == codigo].sort_values("_orden_fila")
    if historial.empty:
        return None
    return historial.iloc[-1]


def barriles_actualmente_en_cuarto_frio(df):
    ultimos = obtener_ultimos_movimientos(df)
    if ultimos.empty:
        return ultimos
    return ultimos[ultimos["_estado_key"].eq("en cuarto frio")].copy()


def validar_formato_codigo_barril(codigo):
    codigo = normalizar_codigo_barril(codigo)
    if not re.fullmatch(r"(?:20|30|58)\d{3}", codigo):
        return False, "El código debe tener 5 dígitos y empezar por 20, 30 o 58."
    return True, ""


def operacion_ya_registrada(df, operacion_id):
    if not operacion_id or df is None or df.empty:
        return False
    op = str(operacion_id).strip()
    if "Operación ID" in df.columns and df["Operación ID"].eq(op).any():
        return True
    patron = f"[OP:{op}]"
    return df["Observaciones"].fillna("").astype(str).str.contains(
        re.escape(patron), regex=True
    ).any()


def validar_movimiento_barril_local(df, codigo, nuevo_estado, estilo="", lote=""):
    """
    Reglas principales:
    - nunca permite repetir consecutivamente el mismo estado;
    - Despacho solo se autoriza si el último estado real es En cuarto frío;
    - En cuarto frío exige estilo y lote.
    """
    valido, mensaje = validar_formato_codigo_barril(codigo)
    if not valido:
        return False, mensaje, None

    ultimo = obtener_ultimo_movimiento(df, codigo)
    estado_nuevo_key = normalizar_clave(nuevo_estado)

    if ultimo is not None and ultimo.get("_estado_key", "") == estado_nuevo_key:
        cliente_anterior = str(ultimo.get("Cliente", "")).strip()
        extra = f" para {cliente_anterior}" if cliente_anterior and estado_nuevo_key == "despacho" else ""
        return (
            False,
            f"El último estado del barril ya es '{nuevo_estado}'{extra}. "
            "El registro repetido fue bloqueado.",
            ultimo,
        )

    if estado_nuevo_key == "despacho":
        if ultimo is None:
            return (
                False,
                "Este barril no tiene historial. Solo se puede despachar un barril cuyo último estado sea 'En cuarto frío'.",
                None,
            )
        if ultimo.get("_estado_key", "") != "en cuarto frio":
            estado_actual = str(ultimo.get("Estado", "Sin estado")).strip() or "Sin estado"
            cliente_actual = str(ultimo.get("Cliente", "")).strip()
            detalle_cliente = f" (cliente: {cliente_actual})" if cliente_actual else ""
            return (
                False,
                f"No se puede despachar. El estado actual es '{estado_actual}'{detalle_cliente}; "
                "debe estar actualmente en 'En cuarto frío'.",
                ultimo,
            )

    if estado_nuevo_key == "en cuarto frio":
        if not str(estilo).strip():
            return False, "Debes seleccionar el estilo para ingresar el barril al cuarto frío.", ultimo
        if not str(lote).strip():
            return False, "Debes ingresar el lote para ingresar el barril al cuarto frío.", ultimo

    return True, "", ultimo


def construir_huella_operacion(datos):
    serializado = json.dumps(datos, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(serializado.encode("utf-8")).hexdigest()


def obtener_operacion_id_para_huella(huella):
    op_anterior = st.session_state.get("movimiento_operacion_id", "")
    huella_anterior = st.session_state.get("movimiento_huella", "")
    if op_anterior and huella_anterior == huella:
        return op_anterior
    nuevo = uuid.uuid4().hex
    st.session_state.movimiento_operacion_id = nuevo
    st.session_state.movimiento_huella = huella
    return nuevo


def limpiar_operacion_pendiente():
    st.session_state.pop("movimiento_operacion_id", None)
    st.session_state.pop("movimiento_huella", None)


def movimiento_local_reciente(codigo, estado, segundos=600):
    """Capa adicional para cubrir el retraso con que Google Forms refleja una respuesta."""
    if not codigo:
        return False
    confirmados = st.session_state.get("movimientos_confirmados_localmente", {})
    llave = f"{normalizar_codigo_barril(codigo)}|{normalizar_clave(estado)}"
    registro = confirmados.get(llave)
    if not registro:
        return False
    return (time.time() - float(registro.get("momento", 0))) <= segundos


def marcar_movimiento_local_confirmado(codigo, estado, operacion_id):
    if not codigo:
        return
    confirmados = dict(st.session_state.get("movimientos_confirmados_localmente", {}))
    ahora = time.time()
    confirmados = {
        k: v for k, v in confirmados.items()
        if ahora - float(v.get("momento", 0)) <= 1800
    }
    llave = f"{normalizar_codigo_barril(codigo)}|{normalizar_clave(estado)}"
    confirmados[llave] = {"momento": ahora, "operacion_id": operacion_id}
    st.session_state.movimientos_confirmados_localmente = confirmados


def enviar_backend_apps_script(payload):
    """Envía una operación atómica. El Apps Script vuelve a validar bajo LockService."""
    cuerpo = dict(payload)
    cuerpo["token"] = APPS_SCRIPT_MOVIMIENTOS_TOKEN
    cuerpo["accion"] = "registrar_movimiento"
    try:
        respuesta = requests.post(
            APPS_SCRIPT_MOVIMIENTOS_URL,
            json=cuerpo,
            timeout=45,
        )
    except requests.RequestException as exc:
        return False, f"No se recibió respuesta del servidor seguro: {exc}", True, {}

    try:
        datos = respuesta.json()
    except ValueError:
        return (
            False,
            f"El servidor seguro devolvió una respuesta no válida (HTTP {respuesta.status_code}).",
            respuesta.status_code >= 500,
            {},
        )

    if datos.get("ok"):
        mensaje = datos.get("message") or "Operación registrada correctamente."
        return True, mensaje, False, datos

    mensaje = datos.get("message") or "La operación fue rechazada por el servidor seguro."
    reintentable = bool(datos.get("retryable", False))
    return False, mensaje, reintentable, datos


def esperar_confirmacion_operacion_formulario(operacion_id, intentos=3, pausa=2):
    for _ in range(intentos):
        time.sleep(pausa)
        try:
            datos = cargar_datos_barriles_frescos()
        except Exception:
            continue
        if operacion_ya_registrada(datos, operacion_id):
            return True
    return False


def enviar_por_formularios_compatibilidad(payload):
    """
    Modo compatible con la app antigua. Evita dobles clics por sesión e incluye un ID
    en Observaciones, pero no sustituye el bloqueo transaccional de Apps Script.
    """
    operacion_id = payload["operacion_id"]
    codigo = payload.get("codigo", "")
    registrar_barril = bool(codigo)

    if registrar_barril:
        try:
            datos = cargar_datos_barriles_frescos()
            if operacion_ya_registrada(datos, operacion_id):
                return True, "La operación ya estaba registrada; no se volvió a enviar.", False, {"duplicate": True}
        except Exception:
            pass

        observaciones = str(payload.get("observaciones", "")).strip()
        etiqueta = f"[OP:{operacion_id}]"
        observaciones_con_id = f"{observaciones}\n{etiqueta}".strip()
        datos_formulario = {
            "entry.311770370": codigo,
            "entry.1283669263": payload.get("estilo", ""),
            "entry.1545499818": payload.get("estado", ""),
            "entry.91059345": payload.get("cliente", ""),
            "entry.1661747572": payload.get("responsable", ""),
            "entry.1465957833": observaciones_con_id,
            "entry.1234567890": payload.get("lote", "") if payload.get("estado") in ["Despacho", "En cuarto frío"] else "",
            "entry.1122334455": payload.get("incluye_latas", "No"),
            "entry.1437332932": payload.get("lote", ""),
        }
        try:
            respuesta = requests.post(FORM_BARRILES_URL, data=datos_formulario, timeout=25)
        except requests.RequestException as exc:
            if esperar_confirmacion_operacion_formulario(operacion_id):
                return True, "El registro sí llegó a Google Sheets y no se duplicó.", False, {"verified_after_error": True}
            return False, f"No se pudo confirmar si Google recibió el barril: {exc}", True, {}

        if respuesta.status_code not in (200, 302):
            return False, f"Google Forms rechazó el barril (HTTP {respuesta.status_code}).", False, {}

    errores_latas = []
    for indice, item in enumerate(payload.get("latas", []), start=1):
        datos_latas = {
            "entry.457965266": str(item["cantidad"]),
            "entry.689047838": item["estilo"],
            "entry.2096096606": item["lote"],
            "entry.1478892985": payload.get("cliente", ""),
            "entry.1774006398": payload.get("responsable", ""),
            "entry.1179145668": "Despacho",
        }
        try:
            respuesta_latas = requests.post(FORM_LATAS_URL, data=datos_latas, timeout=25)
        except requests.RequestException as exc:
            errores_latas.append(f"Orden {indice}: {exc}")
            continue
        if respuesta_latas.status_code not in (200, 302):
            errores_latas.append(f"Orden {indice}: HTTP {respuesta_latas.status_code}")

    if errores_latas:
        return (
            False,
            "El barril pudo quedar registrado, pero fallaron órdenes de latas: " + "; ".join(errores_latas),
            True,
            {"partial": registrar_barril},
        )

    return True, "Operación registrada correctamente.", False, {}


def solicitar_guardado_movimiento():
    """Callback: el primer clic bloquea inmediatamente cualquier clic posterior."""
    if not st.session_state.get("movimiento_guardando", False):
        st.session_state.movimiento_guardando = True
        st.session_state.movimiento_solicitado = True


def guardar_resultado_y_reiniciar(tipo, mensaje, detalles=None, conservar_operacion=False):
    st.session_state.resultado_movimiento = {
        "tipo": tipo,
        "mensaje": mensaje,
        "detalles": detalles or [],
    }
    st.session_state.movimiento_guardando = False
    st.session_state.movimiento_solicitado = False
    if not conservar_operacion:
        limpiar_operacion_pendiente()
    st.rerun()


def limpiar_widgets_movimiento():
    claves = [
        "mov_codigo_despacho", "mov_codigo_manual", "mov_lote", "mov_estilo",
        "mov_observaciones", "incluye_latas_despacho"
    ]
    cantidad_ordenes = int(st.session_state.get("num_latas", 1))
    for indice in range(cantidad_ordenes):
        claves.extend(
            [f"estilo_lata_{indice}", f"lote_lata_{indice}", f"cantidad_lata_{indice}"]
        )
    for clave in claves:
        st.session_state.pop(clave, None)
    st.session_state.num_latas = 1


# ---------- GENERACIÓN AUTOMÁTICA DE ORDEN Y FORMATOS DE DESPACHO ----------
# La plantilla oficial está incorporada dentro de este archivo. No es necesario
# subir FORMATOS DE DESPACHOS.xlsx al repositorio ni cargarlo desde la interfaz.
MAX_LINEAS_FORMATO_DESPACHO = 27
PLANTILLA_DESPACHO_XLSX_B64 = (
    "UEsDBBQABgAIAAAAIQBrK/rSlgEAAK8GAAATAAgCW0NvbnRlbnRfVHlwZXNdLnhtbCCiBAIooAACAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAADEVctOwzAQvCPxD5GvKHHbA0KoKQceR0ACPsCNt4lp"
    "YlveBdq/Z+OmFUJ9ELUSl7zsnZmd9W7GN4umTj4hoHE2F8NsIBKwhdPGlrl4e31Ir0SCpKxWtbOQiyWguJmcn41flx4w4WiLuaiI"
    "/LWUWFTQKMycB8srMxcaRfwaSulVMVclyNFgcCkLZwkspdRiiMn4Dmbqo6bkfsGfV0qmxorkdrWvpcqF8r42hSIWKj+t/kWSutnM"
    "FKBd8dEwdIY+gNJYAVBTZz4YZgwvQMSJoZBbOd99+YvTNK3mdw/ljpAANfbT2RmRcWTMBSvj8YLd2sHQruw2oot74goGoyF5VoEe"
    "VcN2yUUtv1yYT52bZ/tB+roZXc0aZexa9x7+uBllvA1PLKTNLwL31DH6Jx3E7QEyXo+3IsIcSBxpWQOeuvwR9BBzpQLoF+LGK08u"
    "4Cf2AR06qK9Wguwejve9A+rJe/yR+wMvT7/n4DzygA3Qv+rr0dRGp56BIJCBzXDa1uQbRp7ORx8zaMe/Br2FW8bfzeQbAAD//wMA"
    "UEsDBBQABgAIAAAAIQC1VTAj9AAAAEwCAAALAAgCX3JlbHMvLnJlbHMgogQCKKAAAgAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAArJJNT8MwDIbvSPyHyPfV3ZAQQkt3QUi7IVR+gEncD7WNoyQb3b8n"
    "HBBUGoMDR3+9fvzK2908jerIIfbiNKyLEhQ7I7Z3rYaX+nF1ByomcpZGcazhxBF21fXV9plHSnkodr2PKqu4qKFLyd8jRtPxRLEQ"
    "zy5XGgkTpRyGFj2ZgVrGTVneYviuAdVCU+2thrC3N6Dqk8+bf9eWpukNP4g5TOzSmRXIc2Jn2a58yGwh9fkaVVNoOWmwYp5yOiJ5"
    "X2RswPNEm78T/XwtTpzIUiI0Evgyz0fHJaD1f1q0NPHLnXnENwnDq8jwyYKLH6jeAQAA//8DAFBLAwQUAAYACAAAACEAw7PHlygD"
    "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"
    "t7D4q3p0PZ794bvgVCujGjuhSoSqaThl4x5hi3Eaet890afdej3PpotFkG2TXZBuy0Uwj9dpsIsvZps4yublJnp2skPPfvz1KoaF"
    "ONHnlQB0biAIScP0DeuA7JHdMMMfwQvvnu/5zbXbjvcV72CtJHf4rOyf0jmIKxW9E0zaIaLaX6ukaXlvMNI5E7cMdqKv6hh2Ce+G"
    "BTK95tI6XSQ3VjNLWwcb4HHDqB30vhQ86VeeLoemd6pJfmo0hJTkwARBZHwcMXKBccEcLvh7nsDYcUivjf3AlAADjQXGwMTHhhzB"
    "74HT+Bd3p1TON3f+ysjDl3jSjoMvJbEENdeK/jDfuG0/u7f313W8eff8CPelWP0EAAD//wMAUEsDBAoAAAAAAAAAIQDMpUPjLB8A"
    "ACwfAAATAAAAeGwvbWVkaWEvaW1hZ2UxLmpwZ//Y/+AAEEpGSUYAAQIAAAEAAQAA/9sAQwAIBgYHBgUIBwcHCQkICgwUDQwLCwwZ"
    "EhMPFB0aHx4dGhwcICQuJyAiLCMcHCg3KSwwMTQ0NB8nOT04MjwuMzQy/9sAQwEJCQkMCwwYDQ0YMiEcITIyMjIyMjIyMjIyMjIy"
    "MjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIy/8AAEQgAyQDJAwEiAAIRAQMRAf/EAB8AAAEFAQEBAQEBAAAAAAAA"
    "AAABAgMEBQYHCAkKC//EALUQAAIBAwMCBAMFBQQEAAABfQECAwAEEQUSITFBBhNRYQcicRQygZGhCCNCscEVUtHwJDNicoIJChYX"
    "GBkaJSYnKCkqNDU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6g4SFhoeIiYqSk5SVlpeYmZqio6Slpqeoqaqy"
    "s7S1tre4ubrCw8TFxsfIycrS09TV1tfY2drh4uPk5ebn6Onq8fLz9PX29/j5+v/EAB8BAAMBAQEBAQEBAQEAAAAAAAABAgMEBQYH"
    "CAkKC//EALURAAIBAgQEAwQHBQQEAAECdwABAgMRBAUhMQYSQVEHYXETIjKBCBRCkaGxwQkjM1LwFWJy0QoWJDThJfEXGBkaJico"
    "KSo1Njc4OTpDREVGR0hJSlNUVVZXWFlaY2RlZmdoaWpzdHV2d3h5eoKDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5"
    "usLDxMXGx8jJytLT1NXW19jZ2uLj5OXm5+jp6vLz9PX29/j5+v/aAAwDAQACEQMRAD8A96SNCikqpOB2p/lp/cX8qE+4v0FOoAb5"
    "af3F/Kjy0/uL+VOooAb5af3F/Kjy0/uL+VOooAb5af3F/Kjy0/uL+VOooAb5af3F/Kjy0/uL+VOooAb5af3F/Kjy0/uL+VOooAb5"
    "af3F/Kjy0/uL+Vctd+ONGs/Gdr4Yku4vttxC8n3+FcEbYzxgMw3nBI+6P7wrq6AG+Wn9xfyo8tP7i/lTqKAG+Wn9xfyo8tP7i/lT"
    "qKAG+Wn9xfyo8tP7i/lTqKAG+Wn9xfyo8tP7i/lTqKAG+Wn9xfyo8tP7i/lTqKAG+Wn9xfyqjmtCs+gC8n3F+gp1NT7i/QU6gAoo"
    "ooAKKKKACiiigAooooAKzodQs7y8vbGKeOW4tSqXMAOWj3KGXcPQg8djz6GtGvln4ieJNV8KfHPV9W0q4MNwnkKwIykiGCLKOO6n"
    "H5gEYIBABv6r8FdUu/Flzq1rpVnFoi6gpXSkudsk1uGG8qR8q7hkgbgQDjjAFe5z3GnaHa2UDtb2cLSR2ltEAEBY8JGij+Q6AE9A"
    "a4TS/i3aXfwxvfF8+mypNZSfZ5bVHGHmO3btY9FO9SSRkc8NgZ8b0zxvrHjX4r+G7zVZwVj1CFYLeMYjhUyAkKPU8ZJyTgc8DAB9"
    "Z0UUUAFFFFABRRRQAUUUUAFFFFABWfWhWfQBeT7i/QU6mp9xfoKdQAUUUUAFFFFABRRRQAUUVSv72303T7q+upPLgtommmfaTtRQ"
    "STgcnAB6UAea/HXU7zRvCmk6jp9xJbXcGrRtHLG2Cp8mYfkRkEdCCQa5DTNZ8M/GjTk0vxKItO8Vwp5dpeRDaJx1GAeDz1jJ7kqR"
    "k7el+PhN/wDDOxvLTFxbC/hnM0Pzp5bRyAPuHG0llAPQ7h618xAkHIoA+hLD4beJLL4S674XazjfUbjVUeEpIPLkjHlZcMcYHyt1"
    "APHTOKqsnhf4J6OCfs+seN3T5e6WxYdf9hQD7O+f4QfltaD8SPEQ+BepazJcpLqWn3S2UN1Km5yp8vDNnhnG88nrgZyck+CXFxNd"
    "3EtxcSvNNKxeSSRizOxOSSTyST3oA+iPgRr2p+JtT8U6jq1091cv9lG5uir++wqjooGTwPWvba8D/Ztt5lt/EVw0Uggd7eNJCp2s"
    "yiQsAehIDLkdtw9a9q0vVbHWLNL7Trlbq1kd0SaPlWKMUbB7jcp5HB6jI5oA0qKKKACiiigAooooAKKKKACs+tCs+gC8n3F+gp1N"
    "T7i/QU6gAooooAKKKKACiiigArn/AB3/AMk98S/9gq6/9FNXQVz/AI7/AOSe+Jf+wVdf+imoA+YvAnxNv/CZGmX6/wBpeHJiyXFj"
    "IA+1W+8U3cdzlT8rZPQncOm8X/Cqy1vTz4o+Hckd7p8iFpbCJiXRgMnywec46xn5gemcgDxeuq8F+ONX8Daut9p8geCQBbm1kJ8u"
    "dff0YdmHI9wSCAdXog/4xt8Sg/8AQYj/APaNSeBvhWl5p6eKPGE8emeHYx52yRtj3Cdueqoxxg/eYfd+8Gr1uw8ZeC9R8AX3iyXT"
    "kisVuRLfWzW4ZmuxtwMfddiSmG6cgkqQceB+PviPq3ju7jF0BbabAxaCyjYlQem5j/E2OM9ucAZOQDa8f/E/+1ID4c8Kx/2Z4agU"
    "xBIk8trn1JA+6nX5epyS3JwvtvwT/wCSR6F/28f+lElfIFfX/wAE/wDkkehf9vH/AKUSUAegUUUUAFFFFABRRRQAUUUUAFZ9aFZ9"
    "AF5PuL9BTqan3F+gp1ABRRRQAUUUUAFFFFABXH3utaX4qXxJ4NS9FtqawSWsiSAE7ZI+JEGRvADcjIII5wCCewr5B+Kt1cWXxg1m"
    "6tZ5ILiKeN45YmKshEaYII5BoAw/FfgvWvBmoCy1a2CeZkwzod0UwHUq3txkHBGRkciuar6L8HfEnQfiLp0XhbxtaQG9lISOR1Cx"
    "3L9FIIx5cpyemASTjGQtcB8Q/hNqfgmSTUbUtfaGZMLOB+8gB6CUD8tw4J/ukgUAW9E/5No8R/8AYZj/APaFeUV6von/ACbR4j/7"
    "DMf/ALQrC8A/DbV/Hl07wEWmmwkCW8lUlc/3EH8TY5x0A6kZGQDC8N+G9U8VavFpej2zTXD/ADMeiRqOruewH8yAMkgV9QaBNpfw"
    "y8LeHfC+q6lHNqU8y28MUK/NI80xOQCeEUvyxxkL0yQtcz4h8XeGfg1pY8PeGrGK41gxgybjkqccPOwwSxzkIMcH+EFc+NeHdXv9"
    "Z+Kmh3+o3kl1dXGr2rSSueSfNXj0AHQAcAcDigD7NooooAKKKKACiiigAooooAKz60Kz6ALyfcX6CnU1PuL9BTqACiiigAooooAK"
    "KKKACvjn4xf8lY17/rrH/wCikr7Gr45+MX/JWNe/66x/+ikoA4avc/hr8Z3j26D4yn+0Wcq+XFfzDcUzxtmz95T/AHuo75ByvhlF"
    "AH2Snw+8MXXhy90q2iYaRqd2moPBby4jJ+Q4QjojbAcA9ztIGMedfET4xWWkaePDvgeSFCg8uS8t0AigQcbIccE/7Q4A6ZJyvPaJ"
    "qV9F+zX4hCXlwAmoi3QCQ/LE3lbkHop3NkDg7j6mvHKALM08t1PJPNI8s0jF3d2LMzE5JJPUk1r+BP8AkoXhr/sK2v8A6NWqGnaT"
    "qGr3DW+mWFxezKhdo7aFpGCggE4UE45HPvWh4E/5KH4Z/wCwra/+jVoA+3qKKKACiiigAooooAKKKKACs+tCs+gC8n3F+gp1NT7i"
    "/QU6gAooooAKKKKACiiigArg/iB8NNJ8dWm+RRaarGP3V7GgJI/uuP4l/UdjyQe8ooA+H/E3hfVvCOryabq1qYnUnZKuTHMv95G7"
    "j9R0IByKwK+4/EvhrS/FWjy6VqtsJoH+ZW6PE46Oh7MP1BIOQSD8v/EL4Xap4JupJ4kkvdHYgx3qj/V5ONsgH3TnjPRsjGDlQAam"
    "if8AJtHiP/sMx/8AtCvKK9X0T/k2jxH/ANhmP/2hXN+Bvh7rXjm/C2MZh0+OQJcX0g+SLjJAH8TY/hHqMkA5oA9y/Z/0m2s/AL6j"
    "GgNzf3LmVz12odqr9B8x+rGrvw5+E2neC9mo3TJf6yUwZiv7uDPURA9+248kdNoJB67wt4ZsPCegwaPp3nG3iyd0rbmZicknt19A"
    "BW/QAUUUUAFFFFABRRRQAUUUUAFZ9aFZ9AF5PuL9BTqan3F+gp1ABRRRQAUUUUAFFeEfHTx/daXd2fh/RdQntbpcXF5PazFHQEEJ"
    "HuVsjIJYgjpsI6mvGP8AhO/GH/Q165/4MJf/AIqgD7eorzL4K+KtR8T+CJG1W4NxdWVybYTMPneMIpUuf4m5Iz1OBnJyT2PibxLp"
    "nhTRZtW1SfyYI/lVRy8rnoiDuxx+ABJwASADcqrcW8N1bS29xEk0MqlJI5FDK6kYIIPBBHavl7xb8cPEuuzSw6XL/Y9geFSAgzMO"
    "OWkxkHIP3dvBwc9a7TwV4j1hfgN4n1fUdUv5rpZJ0t7qa5dpEzHGq7WJyMOTjB65oA72P4XeHYfDl54dhS4j0q8vFvJYBLkgrs+V"
    "WPIU7BnqeTgjjHU6Xpdno+nQ2FhbxQWsC7Y4o02qozn8ycknuTmvjL/hO/GH/Q165/4MJf8A4qvRvhh8YNVsNat9I8R6jJe6ZdMI"
    "1ubqTMls5PDFzyUJODuPAwQRgggH0xRXgvx+1LWtD1bRbzS9d1KyjuoJIngtrp4kzGwO7CkZJ8zH/ARXjf8AwnfjD/oa9c/8GEv/"
    "AMVQB9vUV8+/CjxDrHjHw54k8L3WuXf9qtD9psLx7qbzkPCn94DkIrCPgdd7dcmsX4WfEHW9N+IEekeJNT1GeC8c2Tx3s0khgnzh"
    "DhskHcNhHA+bJ+7QB9OUUUUAFFFFABRRRQAVn1oVn0AXk+4v0FOpqfcX6CnUAFFFFABWRr+s2vh7QL3V79isFpEZHwRlvRRnA3E4"
    "A9yK16+d/wBoHxgZ7y38J2sn7u323N5ju5HyIfop3dwdy9xQBwXhvS7/AOKXxK23zyZvZmub2WPJ8qIckKTnAxhFzkDKipPin4U0"
    "XwZ4mh0rR7u4nxbLLcC4kR2jck4U7QMfLtOCM4IPeuT03WdS0aZ59L1G7sZnXYz2szRMy5zglSOMgcV0fgLw0fH3jiOx1DUjH5m6"
    "5uZZX3TTgEFlQnq5znJ6AM3OMEA90+B+mNoXwza+v3S3ju55L3MvyeXEFVQWJxgYQtnphga8O+JHjm48d+JXuk3pp1tmKygY/dTu"
    "5HZmxk+gwMnbmvZPjn4jXw54ItPDWmKtu18PJ2RfKIraMDKjBGM/KuMEFd4rjPgN4Kj1fW5vEl7EHttNcJbK6ghp8Z3fVBtPTqyk"
    "HigDy/XPD2oeHZoLbVIRb3M1utx5BPzxqxOA4/hbAztPIBGcHivaXjeD9kzDKVYgNgjGQb7IP5EV5p8WdQi1P4pa9PCGCJOIMH+9"
    "Eixt+GUNe0eMU8v9mOBNuwjTNPyuMYO+HP60AeP/AAo8G6f458UXWm6lNdQwxWTXCtbsqtuDouPmVhjDnt6Vl+PvDVv4S8Zajotr"
    "O89vbshjeXG/DIrYbHGRux2z1wKxtO1bUdHuGuNM1C7sp2TY0ltM0TFcg4JUg4yBx7Cor6+utSu5Lu9uZrm5kxvmnkLu2BgZY8ng"
    "AfhQB9AfFOK58Q/AnQNbkKT3EC2lzcznAb549j4+ruuQPT2rzv4TeCvD/jnUdQ07WLm/guYYUngW1ZV3Jkq5YsrDgtHjp1PWvb9Q"
    "0q01P4DtYQTC+gTREaCS2U/vnijDIQCM8ug+UjPY818s6dq2paRcNcaXfXVlOyFGktpmiYrkHGVIOMgcewoA+pvCvwe0Pwhr0Osa"
    "ZqWsGdFZDHLNGY5FYYIYKgJHQ9eoB7V498dPDC6F43/tSCMJa6uhmG0AATLgSDAOecqxJ6lz6Gn/AAl+IOtJ8QbC01fWr67s74Na"
    "lby5klVXblCoJOGLhVz6Ma9m+Lnhc+J/AN5DCm+9sv8AS7cAEligO5QACSShYAd220AXPhp4s/4TPwPZ6jI7Nexf6Nd8f8tkAy3Q"
    "D5gVfA4G7Hauzr5U+B/iz/hH/Gi6ZcSAWWrhbc/7MwP7o9CeSSuOB8+T0r6roAKKKKACiiigArPrQrPoAvJ9xfoKdTU+4v0FOoAK"
    "KKKAMHxVr8Hhfw1f63cktHaxFljyR5jnhFyAcZYgZxxnJ4FfI+h6bqHj7xxb2sspe51O6aS5nAUYBJeR8cDgBiBx0wK9D+PnjEan"
    "rMPhi2lDW2nnzrkjB3TleB/wFSeh6uQR8teU6Jr+qeHbx7vR72WzuHjMTSRHkqSDj8wPyoA9N+Knww8OeBvDltfadfX0l5NcCJYb"
    "qWNgybWLEBVU8ELzyOcdxVD4CaW1/wDEyK7DlV0+1lnPy5DFh5e32/1hP/Aa4bUdY1zxTqEP2+8vdTu3YRQI7NI2SQAqL7nHAHJr"
    "6M8EeGf+FU/DrVtW1FYjqjwtdXCeZhRsUmOHPQnJIyByXIGQAaAPGPi9r7a98SNT+ZjBYt9hhDKAVEZIYcdR5m8gnnBH0qfwr8YN"
    "c8H6DDo2mabo5gRmcySQyGSRmOcsVcAnoOnQAdq4uwsrjXdctbGKRTdX1ykKvMxwXdgAWPJ6nk813fiL4KeIvC+gXes6hqGkfZbV"
    "QziOaQsckKAAYwMkkDr3oA4DUr+fWNXvNRuMG4vJ3nk2DA3uxY4Hpk19SfHGVLT4UXsCYVZZYIlUegcNj/x2vm3wPGsvj/w7GyB1"
    "bU7YMpGQR5q5r6A/aKdh8PbIA4DapGD7jypT/SgDxz4VeENM8ceKZ9L1Oa5hiSzedGtmVWLh0GPmVhjDN29KvfFr4dWHgGfSm068"
    "up4b5Jcpc7SyMhXJ3KACDvHGOMdTnjhtG1zUvD94b3Sb2W0uShQyRHB2nqP0FT614m1rxG0Umsalc3rQ5EfnPkJnrgdBnAz64HpQ"
    "B7z+zrrM174a1PR5CzR6fOkkTM2QFlDfIB2AZGb3Lmvn/W9NbR9e1HS3cSNZXUlszqMByjFc47ZxXvP7OekXVvpesatNCVt7t4ob"
    "dzkbvL37yPUZZRn1BHavN/jRpZ034o6oywCKG8Ed1Fj+PcgDN+Lh/wAaAPVNA+B/hG5s9M13TtU8QQmWOK8t38+EOmQHU/6vgjiv"
    "Z6+H7fxj4ntLdLe18R6tBBEoWOKK9lVUUdAAGwBW54W+JPiPSfE+m32o69qt1YxTr9phnupJlaI8P8jNgnaSR6HBoAh+JPho+EPH"
    "l9YwqY7V3FzZlRtAickgDkn5TlM9Tsz3r6c+HnitfGHgyx1RmDXYXybsDHEy4DHA4GeGx2DCuM+PvhhNT8KQa/Co+1aW+JD3aFyA"
    "egySG2kcgAFzXztpviHW9HSSPTNY1Cxjc7nW1uXiDH1IUjNAH3VRXzJ8IviTqtv4wi07XtWvb6z1Pbbobqd5fKmz8hGckZJ2nGB8"
    "wJPy19N0AFFFFABWfWhWfQBeT7i/QU6mp9xfoKdQAVQvL2KyspLqRZmSIjiC3eZ+TjhEBY9ew6c9Kv1natqcejaLfapOjvFZ28lx"
    "IqY3FUUsQM45wKAPCrr4V+Fb27mu7rVvF8txPI0ksj6DdEuxOST+46kmmxfCHwUsgM194wdO4TQrlT+Ztz/Kuuj+L93Fpl7can4W"
    "e0ni0qLV7WP7eki3Fu8ioCWC5Q5YEAgng5xxm/efETxHpehrqWpeCfs0k91b21nD/akb/aDKG53Kp242r1HO7tigCHwno/gbwawl"
    "03R9bkvQMG9udEvZJu/Q+TheGIO0DIxnNaXi+70bxd4budEuB4gt4LkoZHj0G8LYVgwAzD6qKpW/xSkMlvaX2hm01P8Atm30m6s2"
    "uw/2fzgSkocJtcfK3Ax069KNR+J1xbJdyWHh/wC2GLX10G3RrwRNPPtJY8oQo3BQMnnOSRjFAHK+Gvh74Q8OeIrLWVn8TXb2j+Yk"
    "M2gXewtg7TxD2OCPcCu68WXui+LfDV3olyviCCG52bpI9CvCw2urjGYcdVFVdT8e69p76Vp6+ETLr15BNcTaf/aSAW8cbYDeZt2t"
    "uGTgYI6VSg+Kmo61cabb+GvCx1WW90sag6/2gtv5P71onT50w211xnvnOMUAc74Z+H/hLw34is9ZjuPE909o5dIptAu9pbaQCcQ9"
    "ic/UV1XjmLQvHuiQ6XeHxFbRxXK3AeHQbwkkKy45h6fOfyqDXvileaJrGrW0vhWSfTtFa1/tC8jv0DRCdVIxGVG45Yjg4OOSAavp"
    "4pWPxN45vHjvHPh6yj2wtd/uZF8t5TtjCgKxK4LNuPTBA4IB5v8A8Kf8Hf8AQS8Xf+E/df8Axirdj8KPAkE6SXcni26VGDeV/Y10"
    "iuAeVbEGcH2IPvXrvgrxKfGHhKx177J9k+1eZ+58zzNu2Rk+9gZ+7np3rPsfG/2/4mat4NXT9jWFotz9r87O/IjO3Zt4/wBb1yen"
    "SgCxYeIdB0uxisrDTdYt7aJdscUeg3oVR/35riPHfhjw1471mDVLyfxNbSxW4t9sOhXZUqGZgeYeuWP6VoaV8Vr2+vbT7V4Za10y"
    "7v3063vRfrJvuBnahTaCNxGMngZpLX4neIJLrXIrvwV9mXRLaSe/b+1o38oiF5EXAT5t20DK5xnJ6YoA4f8A4U/4O/6CXi7/AMJ+"
    "6/8AjFH/AAp/wd/0EvF3/hP3X/xivQE+JGtJ4Xi1i98H/Z2v5bWLSYRqcb/bWnyRlgv7vC4PzDnOOKuWHxEMvhrxHqepaWum32hs"
    "6XFk92HDMEBQCQLjLE7RgHn1yKAJrXUdGh8LRaBc2+uXVotkLKQtol6plj2bOcRdSvUjv6V5b/wp/wAHf9BLxd/4T91/8Yr0p/ij"
    "YR+DPDvieW0aO01e9Szl3ygfZSd4dicfMqtGfTI546U9PiPCNE8WarPYCFPD95NaBTPn7SyHC87fk3MQO+M96APMv+FP+Dv+gl4u"
    "/wDCfuv/AIxXueiXgu9LiKyX8rQgRPLeWcltJIwUZbY6r1znIGM5A6YrnB8RLeXwx4W1q2sfNj17UILIx+dt+zvIWDHO35trIw6D"
    "PXIru6ACiiigArPrQrPoAvJ9xfoKdTU+4v0FOoAK5/x3/wAk98S/9gq6/wDRTV0FFAHz/rPjOzv/AIV/8Iva+TObfwtaXU1zDcB/"
    "LkWSKMwsoHDDOTk5Hp3q14jh08/D/SNP0XxbNq1y2t2Ttcz3qXklo7qVUYHRQVJCnvur1q38LaBbWlzawaHpkVtc7RcQJZxqk2Dk"
    "b1Aw2M8Z6UkHhTw9aIVtvD+lxIZElKx2cagumdjcDquTg9Rk460AeNxaVdyfDDx1eb2u/EllrjvNqDEBma1dG3r/AHQqGTA9yB1A"
    "qK7hSf4V+FdS1C5l06bWfFa399dpL5TRmRph5qseEwiqQegxmvdE0jTUS8jXT7VY70s10ggUCcsMMXGPmyODnOajuNC0m9sYdPvN"
    "Ksbiygx5NvNbo8ce0bV2qRgYBIGOg4oA8zv9X0jRviL4Y1STWI7nSk0We2i1Ke5WRbh4zg5lHDOcc+pPqcVkw67aeJPiXoviDWdQ"
    "n8MRy6AtwiDUFg83bePtjZ2C70dRu24GRj0zXrsnhnQZtOh06XRNOexhYvFbNaRmKNjnJVcYBOT09TS33hjQNTkjlv8AQtNuXijE"
    "SNcWschRBnCgkHAGTx05oA8K8d2811418YTSahLH4fF7pCaxFAgJkt2jGJA3J+UgYAByXHpzY8XXr2198UrSBpvteo3Wl2dskIJe"
    "V2DEoAOTlFcY79O9e4zaDo9wt2s2kWMq3gjFyHtkInCfc35HzbcDGenakfQdGkumu30iwe5eZJ2ma3QuZUyEctjO5cnB6jJxQBxH"
    "wi1FZH8V6ebO7sZItXe7W0uoDE8MM4DRrs/h4UnHvnvXn2g64z/E/S9cktNQaxu/EF+kWpNbsIbiOdFht41f+LaY2+XsB7HH0DFY"
    "WtveXN3DaQR3Nzt8+ZIwry7RhdzDlsDgZ6VXj0LSI7S2s10qyS2tJRPbQrboEhkBJDouMK2STkc5JoA8E8FWU8/i/wALx317JPpc"
    "+rahPb2P3EhngXcJCR985Ix6H2JB66X/AI//AI0/9eKf+kklenLoWjwGAx6TYqYJWmh22yDy5G+868cMe5HJp/8AZOnFr5jp1puv"
    "htuz5K/6QMFcScfOMEjnPBxQB49a3Hh2H4Oafpt5fS65Z3klml+X1FXfSPNRRuBCny0jZOEYYzkEnJFZus+I7m9+HOsaFPd3mu2b"
    "6/DpdpfxYmlmiyJQFIwJXHl4z/EXHavarbwxoFnb3Nva6FpsFvdKFuIorSNVmAzgOAMMBk9fWpI/DuiQwW1vHo1gkNrL59vGtsgW"
    "GTOd6DGFbPcc0AeCSpDr3gew8OSxXFjaJ42WzhtZYxHcW1tMHZQynOG/eP1z074qlbJfaR8PNZ0LVYLi4mvPFMNjeiBTJPJgCRjE"
    "DjczGMYz13e9fRMmhaRNdtdyaTZPctNHO0zW6FzJGCEctjO5QSAeoycU+TSNNluVu3060kuVlEwlaBS4kChQ+7GdwUAZ64AFAHg9"
    "jqkEXgzQLaSNrCw0fx1HDGl5iOSCDLy/vsn5WG9s9htPpXvthqFnqdol1p95BdWzkhZYJBIpwcHDAkHmqU3hnQLwT/atE02fz5RN"
    "N5tpG3mSAEBmyOWAJGTzyfWrthp9npdotrYWdva2yElYYIxGgycnCgADmgC9RRRQAVn1oVn0AXk+4v0FOrPooA0KKz6KANCis+ig"
    "DQorPooA0KKz6KANCis+igDQorPooA0KKz6KANCis+igDQorPooA0KKz6KANCis+igDQrPopKAP/2VBLAwQUAAYACAAAACEAPzTK"
    "8GACAABwBAAAGAAAAHhsL2RyYXdpbmdzL2RyYXdpbmcyLnhtbJxUW2+bMBR+n7T/YPmdcCcpCqlGAlOlaqu6TXt2jQnewEa2m6at"
    "+t93bEKzizRNe+LDBx9/l2PWl8ehRwemNJeiwOEiwIgJKhsu9gX+8rn2VhhpQ0RDeilYgR+Zxpebt2/Wx0blD3qnEDQQOofXAnfG"
    "jLnva9qxgeiFHJmAaivVQAy8qr3fKPIArYfej4Ig8/WoGGl0x5jZTRV86kf+o9tAuMAbxwy4blnfvxO0k2paapUcJkRlvwnWvlVg"
    "odsA4GPbbpYZ8Hot2RVXVfJh3mHhvGbr0SpdptMOKLkdrvP5OHY0iB4LnK7CIEoxoo8FzsKLELA/tRo5nYA43HB6cyJMPxxuFOJN"
    "gSOMBBnAfT6QPQsX38Y96CQ5dL7W5oTQveIFfq7rqEyrOvFqQF4SlIlXVsmFV0fxqoqW9TaKsxe7O8xyCu4bCP6qmV0Psz98HzhV"
    "UsvWLKgcfNm2nLI5R0gxTHznuyP6nKRVUKaryFsmy62XxNvQK+Ok8rZVFZZ1epElu/LFyvYd+/npVEyBWNGnSABaNxAMScvULeuB"
    "7IHdMs2fwIvAtbEh/uLaXc/HmvcQK8ktPin7p+mcxO0kvR+YMNOIKnesFLrjo8ZI5Wy4Y5CJumpCyBLuhgEyo+LCWEIk10YxQzsL"
    "W+Bxy6iZ9L4WnNAzTytBj1Y1yY+tgiElOTBBMDJuHDGCgYnjOFwlqRPtrPvLSIG3c59RafOeyQE81AZIAxk3OeQAlk+05k/ssUJa"
    "6+z6mZSDrxNKew7W7IghqL2W9Lv+yk33yV7gnxP57fq5FvZnsfkBAAD//wMAUEsDBBQABgAIAAAAIQA5MbWR2wAAANABAAAjAAAA"
    "eGwvd29ya3NoZWV0cy9fcmVscy9zaGVldDEueG1sLnJlbHOskc1qwzAMgO+DvoPRvXbSwxijTi9j0OvaPYBnK4lZIhtLW9e3n3co"
    "LKWwy276QZ8+oe3ua57UJxaOiSy0ugGF5FOINFh4PT6vH0CxOApuSoQWzsiw61Z32xecnNQhHmNmVSnEFkaR/GgM+xFnxzplpNrp"
    "U5md1LQMJjv/7gY0m6a5N+U3A7oFU+2DhbIPG1DHc66b/2anvo8en5L/mJHkxgoTijvVyyrSlQHFgtaXGl+CVldlMLdt2v+0ySWS"
    "YDmgSJXihdVVz1zlrX6L9CNpFn/ovgEAAP//AwBQSwMEFAAGAAgAAAAhAD50UOPbAAAA0AEAACMAAAB4bC93b3Jrc2hlZXRzL19y"
    "ZWxzL3NoZWV0Mi54bWwucmVsc6yRzWrDMAyA74O+g9G9dprDGKNOL2PQ69o9gGcriVkiG0tb17efdygspbDLbvpBnz6h7e5rntQn"
    "Fo6JLGx0AwrJpxBpsPB6fF4/gGJxFNyUCC2ckWHXre62Lzg5qUM8xsyqUogtjCL50Rj2I86OdcpItdOnMjupaRlMdv7dDWjaprk3"
    "5TcDugVT7YOFsg8tqOM5181/s1PfR49PyX/MSHJjhQnFneplFenKgGJB60uNL0GrqzKY2zab/7TJJZJgOaBIleKF1VXPXOWtfov0"
    "I2kWf+i+AQAA//8DAFBLAwQUAAYACAAAACEAspc8br4AAAAkAQAAIwAAAHhsL2RyYXdpbmdzL19yZWxzL2RyYXdpbmcxLnhtbC5y"
    "ZWxzhI/LigIxEEX3gv8Qam+q24UM0mk3MuB20A8okup0tPMgyQz69wbcjDAwy7qXew41HO5+ET+ci4tBQS87EBx0NC5YBZfz5+YD"
    "RKkUDC0xsIIHFziM69XwxQvVNiqzS0U0SigK5lrTHrHomT0VGROH1kwxe6rtzBYT6RtZxm3X7TD/ZsD4xhQnoyCfTA/i/EjN/D87"
    "TpPTfIz623OofyjQ+eZuQMqWqwIp0bNx9Mp7eU0WcBzw7bfxCQAA//8DAFBLAwQUAAYACAAAACEAspc8br4AAAAkAQAAIwAAAHhs"
    "L2RyYXdpbmdzL19yZWxzL2RyYXdpbmcyLnhtbC5yZWxzhI/LigIxEEX3gv8Qam+q24UM0mk3MuB20A8okup0tPMgyQz69wbcjDAw"
    "y7qXew41HO5+ET+ci4tBQS87EBx0NC5YBZfz5+YDRKkUDC0xsIIHFziM69XwxQvVNiqzS0U0SigK5lrTHrHomT0VGROH1kwxe6rt"
    "zBYT6RtZxm3X7TD/ZsD4xhQnoyCfTA/i/EjN/D87TpPTfIz623OofyjQ+eZuQMqWqwIp0bNx9Mp7eU0WcBzw7bfxCQAA//8DAFBL"
    "AwQUAAYACAAAACEAg6cIbcICAABcCgAAJwAAAHhsL3ByaW50ZXJTZXR0aW5ncy9wcmludGVyU2V0dGluZ3MxLmJpbuxWzW7TQBD+"
    "nFBEBRI8QsWJS5qkTVvKLY1T5Co/JnYqjl2abWM1tS3baRoQEgeegmdAAgkOPXDsgSMPwCtw5gjfOg4kadUfSFUO7Go969ndb74d"
    "z4xchgkLddQwhwqWsMIxR41EAIfPEGc37Ub65le8mk2/QyqFGby5XbjVgoa7aGspyraW5rOIwjk4l1nWks1KpjiU/MH22LDGzOhG"
    "rXkfW9qn9PFMavbbh7Ns3ElwBthDC1Mk/R/qn/fAZb76FjdbVXtDXeoeTO0F1pg7eSyz57HOeM/EUa+jxFkBi9CpzXBXKd6VoWaV"
    "ukX2Fco8865IzRJeEtFw/W605rioCj4aZUuvVNB0nUCGamYKXwaW81yiUrbtcgNV2XKE3fclLLtY04sNHfVulGCsi23Z9LHhPTPF"
    "rqwHLRmgIQ9kEErUA0e6kYgcz4VZb9iNomETntvi40+6ouNEfdS8YF90UPI6HRHxVC3eY21z1d3lqiuJGHqdbgykm8bicu6QQ53w"
    "gqrXkoPZxUPgeAbYLOjV4TfZNE3j85fvzQeEeMu1Iw7VXlPOUqr8PeJwWbFySR+11kbE7uMRsuwhttFmdduH4Hye0qEmgMc3Dzvc"
    "Oc93j/oselxz0eJbj6tZLBA9j4ec5fhds8RUldLlGfXcHdOM2tmjvT4xPO5vxUgGz/ok+ZHDp2bnFPdMl3eO0aZ4K/YX5b1DvoKe"
    "kAn3vZjlb84LJ1hP29eKc55+/xvOiuX7xM+DG4zTvn4/T8bHIJ5VXOzx9vkJL1+Fj3OsPn8ezwe/WKo8HPKejI7rj41JPyveA5Zt"
    "8j5kpHfOzcMec6HHGtFjPs3HGa3y/imq/IdSsbrKrnLMTTInpD8EK4qMkbdiOyGrwMk27p/T7agKpGrQ0KI1Us0Uop/gO1eAn4mr"
    "XMhqJ3i7wY1U7VVNydH5TwAAAP//AwBQSwMEFAAGAAgAAAAhAPPu5+vCAgAAXAoAACcAAAB4bC9wcmludGVyU2V0dGluZ3MvcHJp"
    "bnRlclNldHRpbmdzMi5iaW7sVs1u00AQ/pxQRAQSPELFiUuapE1byi2tU+QqPyZ2Ko5Zmm1jNbUt22laEBIHnoJnQAIJDj1w7IEj"
    "D8ArcOYI3zoOJGnVH0hVDuxqPevZ3W++Hc+MXIYJC3XUMIsKFrHMMUuNRACHzxBnN+1G+uZXvMqk3yGVQgZvbhdvtaHhLjpairKj"
    "pfksoXgOzmWWtWSzkikOJX+wPTasMTO6UWveR0v7lD6eSWW+fTjLxp0EZ4A9tDBF0v+h/nkPXOart7jZqtob6lL3YGovsMrcKWCJ"
    "vYB1xns2jnoda5wVsQCd2ix3rcW7stSsULfAvkxZYN6VqFnESyIart+LVh0XVcFHo2zplQqarhPIUM1M4cvAcp5LVMq2XW6gKtuO"
    "sA99Ccsu1fRSQ0e9FyUY62JLNn1seM9MsSPrQVsGaMh9GYQS9cCRbiQix3Nh1ht2o2TYhOe2+PiTnug60SFqXrAnuljzul0R8VQt"
    "3mNtcdXd4aoriRh63V4MpJvGwlL+gEOd8IKq15aD2cVD4HgG2Czq1eE32TRN4/OX780HhHjLtSMO1V5TZihV/h5xuKxY+aSPWusg"
    "YvfxCDn2EFvosLrtQXA+R+lQE8Djm4dt7pzju0d9Dn2uuWjzrc/VHOaJXsBDzvL8rjliqkrp8ox67oxpRu3s0t4hMTzub8dIBs/6"
    "JPmRw6dm+xT3TJd3ntGmeCv2F+W9Tb6CnpAJ992Y5W/O8ydYT9vXinOBfv8bzorl+8TPgxuM075+P0/GxyCeVVzs8vaFCS9fhY/z"
    "rD5/Hs/7v1iqPBzynoyO64+NST8r3gOWHfI+YKR3z83DPnOhzxrRZz7NxRmt8v4pqvyHUrG6wq5yzE0yJ6Q/BCuKjJFbsZ2QVeBk"
    "G/fP6XZUBVI1aGjRGqlmCtFP8J0rwM/GVS5ktRO83eBGqvaqpuTo/CcAAAD//wMAUEsDBBQABgAIAAAAIQB+xIpNVQEAAI4CAAAR"
    "AAgBZG9jUHJvcHMvY29yZS54bWwgogQBKKAAAQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACMkl9PgzAUxd9N/A6k79AC"
    "28QGWHS6J5csOqPxrWnvNiIU0lbZvr0d/8Tpg4/tOffXc24azw9F7nyC0lkpE+R7BDkgeSkyuUvQ82bpRsjRhknB8lJCgo6g0Ty9"
    "vIh5RXmpYK3KCpTJQDuWJDXlVYL2xlQUY833UDDtWYe04rZUBTP2qHa4Yvyd7QAHhMxwAYYJZhg+Ad1qIKIOKfiArD5U3gAEx5BD"
    "AdJo7Hs+/vYaUIX+c6BRRs4iM8fKdurijtmCt+LgPuhsMNZ17dVhE8Pm9/Hr6uGpqepm8rQrDiiNBadcATOlSm8W948xHl2clpcz"
    "bVZ2z9sMxO2x8/y+761rlUkDIg1IMHNJ5JJw41/TaUSnV28x7uZ6k3286domAOHY9LTt2isv4eJus0RnvElEQ2J5Z/OnNi2w6BL/"
    "jxgQSkI6mY2IPSBtQv/8QekXAAAA//8DAFBLAwQUAAYACAAAACEAIOo6OaABAAA5AwAAEAAIAWRvY1Byb3BzL2FwcC54bWwgogQB"
    "KKAAAQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACck8Fu2zAMhu8D9g6G7oncdCiGQFYxpCty2LBgcXvYjZXpRJssCRJj"
    "JHubPctebLK9uM56GNAbyZ/+9YmUxe2xMVmLIWpnC3Y1z1mGVrlK213BHsr72XuWRQJbgXEWC3bCyG7l2zdiE5zHQBpjlixsLNie"
    "yC85j2qPDcR5km1SahcaoJSGHXd1rRXeOXVo0BJf5PkNxyOhrbCa+dGQDY7Lll5rWjnV8cXH8uQTsBQfvDdaAaVbys9aBRddTdnH"
    "o0Ij+FQUiW6L6hA0nWQu+DQVWwUGV8lY1mAiCv5cEGuEbmgb0CFK0dKyRUUuZFH/TGNbsOwJInY4BWshaLCUsLq2Ielj4yMFuXbf"
    "IWYVZur3L6MOxgme+gatD6efTGP9Ti76hhRcNnYGA08SLklLTQbjl3oDgf4H3jMM2APO/az8+m2W58OxfxFH2LN6/eIC/WgSyj+H"
    "r1zjwZ6SMEaftP0RH3zp7oDwPPbLotjuIWCVNjWuZSyIdZp4MJ3Jag92h9W556XQPZLH4U+QVzfz/DpP+5/UBH9+8/IPAAAA//8D"
    "AFBLAQItABQABgAIAAAAIQBrK/rSlgEAAK8GAAATAAAAAAAAAAAAAAAAAAAAAABbQ29udGVudF9UeXBlc10ueG1sUEsBAi0AFAAG"
    "AAgAAAAhALVVMCP0AAAATAIAAAsAAAAAAAAAAAAAAAAAzwMAAF9yZWxzLy5yZWxzUEsBAi0AFAAGAAgAAAAhAMOzx5coAwAALwcA"
    "AA8AAAAAAAAAAAAAAAAA9AYAAHhsL3dvcmtib29rLnhtbFBLAQItABQABgAIAAAAIQBKqaZh+gAAAEcDAAAaAAAAAAAAAAAAAAAA"
    "AEkKAAB4bC9fcmVscy93b3JrYm9vay54bWwucmVsc1BLAQItABQABgAIAAAAIQD/BbKFeQoAANc2AAAYAAAAAAAAAAAAAAAAAIMM"
    "AAB4bC93b3Jrc2hlZXRzL3NoZWV0MS54bWxQSwECLQAUAAYACAAAACEAhHUxNRoJAACJKAAAGAAAAAAAAAAAAAAAAAAyFwAAeGwv"
    "d29ya3NoZWV0cy9zaGVldDIueG1sUEsBAi0AFAAGAAgAAAAhAINNbMhWBwAAyCAAABMAAAAAAAAAAAAAAAAAgiAAAHhsL3RoZW1l"
    "L3RoZW1lMS54bWxQSwECLQAUAAYACAAAACEAlwwfs04FAACxKgAADQAAAAAAAAAAAAAAAAAJKAAAeGwvc3R5bGVzLnhtbFBLAQIt"
    "ABQABgAIAAAAIQABtcQrCwIAAM0FAAAUAAAAAAAAAAAAAAAAAIItAAB4bC9zaGFyZWRTdHJpbmdzLnhtbFBLAQItABQABgAIAAAA"
    "IQC1fjtOWgIAAG0EAAAYAAAAAAAAAAAAAAAAAL8vAAB4bC9kcmF3aW5ncy9kcmF3aW5nMS54bWxQSwECLQAKAAAAAAAAACEAzKVD"
    "4ywfAAAsHwAAEwAAAAAAAAAAAAAAAABPMgAAeGwvbWVkaWEvaW1hZ2UxLmpwZ1BLAQItABQABgAIAAAAIQA/NMrwYAIAAHAEAAAY"
    "AAAAAAAAAAAAAAAAAKxRAAB4bC9kcmF3aW5ncy9kcmF3aW5nMi54bWxQSwECLQAUAAYACAAAACEAOTG1kdsAAADQAQAAIwAAAAAA"
    "AAAAAAAAAABCVAAAeGwvd29ya3NoZWV0cy9fcmVscy9zaGVldDEueG1sLnJlbHNQSwECLQAUAAYACAAAACEAPnRQ49sAAADQAQAA"
    "IwAAAAAAAAAAAAAAAABeVQAAeGwvd29ya3NoZWV0cy9fcmVscy9zaGVldDIueG1sLnJlbHNQSwECLQAUAAYACAAAACEAspc8br4A"
    "AAAkAQAAIwAAAAAAAAAAAAAAAAB6VgAAeGwvZHJhd2luZ3MvX3JlbHMvZHJhd2luZzEueG1sLnJlbHNQSwECLQAUAAYACAAAACEA"
    "spc8br4AAAAkAQAAIwAAAAAAAAAAAAAAAAB5VwAAeGwvZHJhd2luZ3MvX3JlbHMvZHJhd2luZzIueG1sLnJlbHNQSwECLQAUAAYA"
    "CAAAACEAg6cIbcICAABcCgAAJwAAAAAAAAAAAAAAAAB4WAAAeGwvcHJpbnRlclNldHRpbmdzL3ByaW50ZXJTZXR0aW5nczEuYmlu"
    "UEsBAi0AFAAGAAgAAAAhAPPu5+vCAgAAXAoAACcAAAAAAAAAAAAAAAAAf1sAAHhsL3ByaW50ZXJTZXR0aW5ncy9wcmludGVyU2V0"
    "dGluZ3MyLmJpblBLAQItABQABgAIAAAAIQB+xIpNVQEAAI4CAAARAAAAAAAAAAAAAAAAAIZeAABkb2NQcm9wcy9jb3JlLnhtbFBL"
    "AQItABQABgAIAAAAIQAg6jo5oAEAADkDAAAQAAAAAAAAAAAAAAAAABJhAABkb2NQcm9wcy9hcHAueG1sUEsFBgAAAAAUABQAgQUA"
    "AOhjAAAAAA=="
)


def abrir_plantilla_despacho():
    """Abre la plantilla oficial incorporada en el código, sin archivos externos."""
    try:
        contenido = base64.b64decode(PLANTILLA_DESPACHO_XLSX_B64)
        return load_workbook(io.BytesIO(contenido))
    except Exception as exc:
        raise RuntimeError(f"No fue posible abrir la plantilla interna de despacho: {exc}") from exc


def formatear_numero_litros(valor):
    if valor in (None, ""):
        return ""
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return str(valor)
    if numero.is_integer():
        return str(int(numero))
    return f"{numero:.1f}".rstrip("0").rstrip(".")


def capacidad_barril_por_codigo(codigo):
    codigo_limpio = normalizar_codigo_barril(codigo)
    if codigo_limpio.startswith("20"):
        return 20
    if codigo_limpio.startswith("30"):
        return 30
    if codigo_limpio.startswith("58"):
        return 58
    return ""


def extraer_litros_desde_observaciones(texto):
    """Detecta observaciones como 'Barril con 14 lt' o '28,4 litros'."""
    if not texto:
        return None
    patron = re.compile(r"(\d+(?:[,.]\d+)?)\s*(?:l|lt|lts|litro|litros)\b", re.IGNORECASE)
    coincidencia = patron.search(str(texto))
    if not coincidencia:
        return None
    try:
        return float(coincidencia.group(1).replace(",", "."))
    except ValueError:
        return None


def nombre_archivo_seguro(texto):
    limpio = unicodedata.normalize("NFKD", str(texto or ""))
    limpio = "".join(c for c in limpio if not unicodedata.combining(c))
    limpio = re.sub(r"[^A-Za-z0-9_-]+", "_", limpio).strip("_")
    return limpio or "cliente"


def construir_items_orden_despacho(
    codigo_barril,
    estilo_barril,
    lote_barril,
    latas_solicitadas,
    observaciones,
):
    """Construye exactamente las líneas confirmadas del despacho."""
    items = []

    codigo_limpio = normalizar_codigo_barril(codigo_barril)
    if codigo_limpio:
        litros_observados = extraer_litros_desde_observaciones(observaciones)
        capacidad = litros_observados if litros_observados else capacidad_barril_por_codigo(codigo_limpio)
        capacidad_txt = formatear_numero_litros(capacidad)
        producto = "Barril"
        if capacidad_txt:
            producto = f"Barril de {capacidad_txt}L"
        if str(estilo_barril).strip():
            producto = f"{producto} - {str(estilo_barril).strip()}"

        items.append(
            {
                "Tipo": "Barril",
                "Producto": producto,
                "Cantidad": 1,
                "Lote": str(lote_barril or "").strip(),
                "Código del barril": codigo_limpio,
            }
        )

    for item in latas_solicitadas or []:
        estilo = str(item.get("estilo", "")).strip()
        lote = str(item.get("lote", "")).strip()
        cantidad = int(item.get("cantidad", 0) or 0)
        if cantidad <= 0 or not estilo or not lote:
            continue
        items.append(
            {
                "Tipo": "Latas",
                "Producto": f"Lata 330mL - {estilo}",
                "Cantidad": cantidad,
                "Lote": lote,
                "Código del barril": "",
            }
        )

    return items


def escribir_valor_formato(ws, celda, valor):
    """Escribe un dato y conserva el estilo oficial del formato."""
    ws[celda].value = valor
    alineacion = copy(ws[celda].alignment)
    alineacion.wrap_text = True
    alineacion.vertical = "center"
    ws[celda].alignment = alineacion


def limpiar_area_formatos(ws, tipo):
    """Limpia los campos variables sin tocar encabezados, logotipo ni firmas."""
    if tipo == "F-TRZ-002":
        for fila in range(7, 34):
            for columna in ["C", "D", "E", "F"]:
                ws[f"{columna}{fila}"].value = None
        for fila_grupo in range(7, 34, 3):
            for celda in [
                f"A{fila_grupo}", f"B{fila_grupo}", f"G{fila_grupo}",
                f"H{fila_grupo}", f"I{fila_grupo}", f"J{fila_grupo}",
                f"K{fila_grupo}",
            ]:
                ws[celda].value = None
        for celda in ["B35", "B36", "C34", "C35", "C36"]:
            ws[celda].value = None
    elif tipo == "F-TRZ-003":
        for fila in range(7, 34):
            for columna in ["C", "D"]:
                ws[f"{columna}{fila}"].value = None
        for fila_grupo in range(7, 34, 3):
            for celda in [
                f"A{fila_grupo}", f"B{fila_grupo}", f"E{fila_grupo}",
                f"F{fila_grupo}", f"G{fila_grupo}", f"H{fila_grupo}",
            ]:
                ws[celda].value = None
        for celda in ["B34", "B35"]:
            ws[celda].value = None


def llenar_hoja_pedido_distribucion(
    ws,
    items,
    fecha,
    cliente,
    responsable,
    observaciones,
):
    """Diligencia F-TRZ-002 con todos los productos del despacho."""
    limpiar_area_formatos(ws, "F-TRZ-002")
    fecha_txt = fecha.strftime("%d/%m/%Y")

    for indice, item in enumerate(items[:MAX_LINEAS_FORMATO_DESPACHO]):
        fila = 7 + indice
        fila_grupo = 7 + (indice // 3) * 3
        if indice % 3 == 0:
            escribir_valor_formato(ws, f"A{fila_grupo}", fecha_txt)
            escribir_valor_formato(ws, f"B{fila_grupo}", cliente)
            escribir_valor_formato(ws, f"G{fila_grupo}", "X")  # Calidad: cumple
            escribir_valor_formato(ws, f"I{fila_grupo}", "X")  # Limpieza: cumple
            escribir_valor_formato(ws, f"K{fila_grupo}", observaciones)

        escribir_valor_formato(ws, f"C{fila}", item["Producto"])
        escribir_valor_formato(ws, f"D{fila}", item["Cantidad"])
        escribir_valor_formato(ws, f"E{fila}", item["Lote"])
        escribir_valor_formato(ws, f"F{fila}", item["Código del barril"])

    # Queda listo para la firma de quien realiza y de quien supervisa.
    escribir_valor_formato(ws, "B35", responsable)
    escribir_valor_formato(ws, "B36", "")


def llenar_hoja_orden_entrega(
    ws,
    items,
    fecha,
    cliente_y_direccion,
    responsable,
    observaciones,
):
    """Diligencia F-TRZ-003 y deja libre la firma de recibido del cliente."""
    limpiar_area_formatos(ws, "F-TRZ-003")
    fecha_txt = fecha.strftime("%d/%m/%Y")

    for indice, item in enumerate(items[:MAX_LINEAS_FORMATO_DESPACHO]):
        fila = 7 + indice
        fila_grupo = 7 + (indice // 3) * 3
        if indice % 3 == 0:
            escribir_valor_formato(ws, f"A{fila_grupo}", fecha_txt)
            escribir_valor_formato(ws, f"B{fila_grupo}", cliente_y_direccion)
            escribir_valor_formato(ws, f"E{fila_grupo}", "X")  # Pedido correcto: sí
            escribir_valor_formato(ws, f"G{fila_grupo}", observaciones)
            escribir_valor_formato(ws, f"H{fila_grupo}", "")  # Firma de recibido

        escribir_valor_formato(ws, f"C{fila}", item["Producto"])
        escribir_valor_formato(ws, f"D{fila}", item["Cantidad"])

    escribir_valor_formato(ws, "B34", responsable)
    escribir_valor_formato(ws, "B35", "")


def generar_formatos_despacho_excel(
    items,
    cliente,
    direccion,
    responsable,
    observaciones,
    fecha=None,
    operacion_id="",
):
    """Genera los dos formatos oficiales completamente diligenciados."""
    if not items:
        raise ValueError("No hay productos confirmados para generar la orden.")
    if len(items) > MAX_LINEAS_FORMATO_DESPACHO:
        raise ValueError(
            f"El formato permite máximo {MAX_LINEAS_FORMATO_DESPACHO} líneas de producto. "
            f"Actualmente hay {len(items)} líneas."
        )

    wb = abrir_plantilla_despacho()
    fecha = fecha or datetime.now()
    cliente_limpio = str(cliente or "").strip()
    direccion_limpia = str(direccion or "").strip()
    responsable_limpio = str(responsable or "").strip()
    observaciones_limpias = str(observaciones or "").strip()
    cliente_y_direccion = cliente_limpio
    if direccion_limpia:
        cliente_y_direccion = f"{cliente_limpio} - {direccion_limpia}"

    hojas_requeridas = {"F-TRZ-002", "F-TRZ-003"}
    faltantes = hojas_requeridas.difference(wb.sheetnames)
    if faltantes:
        raise ValueError(f"La plantilla interna no contiene: {', '.join(sorted(faltantes))}")

    llenar_hoja_pedido_distribucion(
        wb["F-TRZ-002"],
        items,
        fecha,
        cliente_limpio,
        responsable_limpio,
        observaciones_limpias,
    )
    llenar_hoja_orden_entrega(
        wb["F-TRZ-003"],
        items,
        fecha,
        cliente_y_direccion,
        responsable_limpio,
        observaciones_limpias,
    )

    # Configuración de impresión para que cada formato salga en una sola página.
    for ws in (wb["F-TRZ-002"], wb["F-TRZ-003"]):
        ws.sheet_view.showGridLines = False
        ws.page_setup.orientation = "landscape"
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 1
        ws.sheet_properties.pageSetUpPr.fitToPage = True
        ws.print_options.horizontalCentered = True

    wb.properties.title = f"Orden de despacho - {cliente_limpio}"
    wb.properties.subject = "Formatos F-TRZ-002 y F-TRZ-003 listos para firma"
    wb.properties.creator = "Sistema de Trazabilidad Castiza"
    if operacion_id:
        wb.properties.identifier = str(operacion_id)

    salida = io.BytesIO()
    wb.save(salida)
    return salida.getvalue()


def generar_html_impresion_orden(
    items,
    cliente,
    direccion,
    responsable,
    observaciones,
    fecha=None,
):
    """Crea una vista rápida para imprimir y firmar desde el navegador."""
    fecha_txt = (fecha or datetime.now()).strftime("%d/%m/%Y")
    direccion_limpia = str(direccion or "").strip()
    filas = ""
    for item in items:
        filas += f"""
        <tr>
            <td>{html_lib.escape(str(item['Producto']))}</td>
            <td>{html_lib.escape(str(item['Cantidad']))}</td>
            <td>{html_lib.escape(str(item['Lote']))}</td>
            <td>{html_lib.escape(str(item['Código del barril']))}</td>
        </tr>
        """

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: Arial, sans-serif; color: #1f2933; margin: 24px; }}
            .toolbar {{ margin-bottom: 16px; }}
            button {{ background: #20cb80; color: white; border: 0; border-radius: 8px; padding: 10px 16px; font-weight: 700; cursor: pointer; }}
            h1 {{ color: #1a5d3b; margin-bottom: 4px; }}
            .meta {{ margin: 2px 0; font-size: 13px; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 18px; }}
            th {{ background: #1a5d3b; color: white; text-align: left; }}
            th, td {{ border: 1px solid #b6c2b9; padding: 8px; font-size: 12px; }}
            .firmas {{ display: grid; grid-template-columns: 1fr 1fr; gap: 40px; margin-top: 56px; }}
            .firma {{ border-top: 1px solid #333; padding-top: 8px; font-size: 12px; }}
            @media print {{
                .toolbar {{ display: none; }}
                body {{ margin: 8mm; }}
            }}
        </style>
    </head>
    <body>
        <div class="toolbar">
            <button onclick="window.print()">🖨️ Imprimir orden</button>
        </div>
        <h1>Orden de pedido y despacho Castiza</h1>
        <p class="meta"><strong>Fecha:</strong> {html_lib.escape(fecha_txt)}</p>
        <p class="meta"><strong>Cliente:</strong> {html_lib.escape(str(cliente or ''))}</p>
        <p class="meta"><strong>Dirección:</strong> {html_lib.escape(direccion_limpia)}</p>
        <p class="meta"><strong>Responsable:</strong> {html_lib.escape(str(responsable or ''))}</p>
        <table>
            <thead>
                <tr>
                    <th>Producto</th>
                    <th>Cantidad</th>
                    <th>Lote</th>
                    <th>Código del barril</th>
                </tr>
            </thead>
            <tbody>{filas}</tbody>
        </table>
        <p class="meta"><strong>Observaciones:</strong> {html_lib.escape(str(observaciones or ''))}</p>
        <div class="firmas">
            <div class="firma">Entrega / Responsable del transporte</div>
            <div class="firma">Recibe / Cliente</div>
        </div>
    </body>
    </html>
    """


def preparar_orden_despacho_para_descarga(
    items,
    cliente,
    direccion,
    responsable,
    observaciones,
    operacion_id,
    fecha=None,
):
    """Empaqueta el Excel oficial y la vista de impresión tras un despacho exitoso."""
    fecha = fecha or datetime.now()
    archivo_excel = generar_formatos_despacho_excel(
        items,
        cliente,
        direccion,
        responsable,
        observaciones,
        fecha=fecha,
        operacion_id=operacion_id,
    )
    nombre_archivo = (
        f"orden_despacho_{nombre_archivo_seguro(cliente)}_"
        f"{fecha.strftime('%Y%m%d_%H%M%S')}.xlsx"
    )
    return {
        "archivo": archivo_excel,
        "nombre": nombre_archivo,
        "html": generar_html_impresion_orden(
            items,
            cliente,
            direccion,
            responsable,
            observaciones,
            fecha=fecha,
        ),
        "operacion_id": str(operacion_id or ""),
    }


def mostrar_orden_despacho_generada(orden, descarga_automatica=False):
    """Muestra la orden confirmada e intenta descargarla una sola vez automáticamente."""
    if not orden:
        return

    st.markdown("---")
    st.success("📄 Orden oficial diligenciada y lista para imprimir y firmar.")
    st.download_button(
        "⬇️ Descargar nuevamente los formatos F-TRZ-002 y F-TRZ-003",
        data=orden["archivo"],
        file_name=orden["nombre"],
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
        key=f"descargar_orden_{orden.get('operacion_id', '')}",
    )

    import streamlit.components.v1 as components

    if descarga_automatica:
        contenido_b64 = base64.b64encode(orden["archivo"]).decode("ascii")
        nombre_js = json.dumps(orden["nombre"])
        components.html(
            f"""
            <div style="font-family:Arial,sans-serif;font-size:13px;color:#243b2f;">
                Iniciando descarga automática de la orden…
            </div>
            <script>
            (() => {{
                try {{
                    const binario = atob("{contenido_b64}");
                    const bytes = new Uint8Array(binario.length);
                    for (let i = 0; i < binario.length; i++) bytes[i] = binario.charCodeAt(i);
                    const blob = new Blob([bytes], {{
                        type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    }});
                    const url = URL.createObjectURL(blob);
                    const enlace = document.createElement("a");
                    enlace.href = url;
                    enlace.download = {nombre_js};
                    enlace.style.display = "none";
                    document.body.appendChild(enlace);
                    enlace.click();
                    setTimeout(() => {{
                        URL.revokeObjectURL(url);
                        enlace.remove();
                    }}, 1500);
                }} catch (error) {{
                    console.error("No se pudo iniciar la descarga automática", error);
                }}
            }})();
            </script>
            """,
            height=38,
        )

    st.caption(
        "El Excel contiene los formatos oficiales completos. Las casillas de firma quedan en blanco "
        "para que firmen el responsable, el supervisor y el cliente al recibir."
    )
    with st.expander("🖨️ Vista rápida e impresión desde el navegador", expanded=False):
        components.html(orden["html"], height=560, scrolling=True)


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

# ---------- RESULTADO DEL ÚLTIMO INTENTO ----------
resultado_anterior = st.session_state.pop("resultado_movimiento", None)
if resultado_anterior:
    tipo = resultado_anterior.get("tipo", "info")
    mensaje = resultado_anterior.get("mensaje", "")
    if tipo == "success":
        st.success(f"✅ {mensaje}")
    elif tipo == "warning":
        st.warning(f"⚠️ {mensaje}")
    else:
        st.error(f"❌ {mensaje}")
    for detalle in resultado_anterior.get("detalles", []):
        st.write(f"• {detalle}")

# La orden se muestra después del resultado para que corresponda únicamente a un despacho confirmado.
orden_confirmada = st.session_state.get("orden_despacho_generada")
if orden_confirmada:
    descarga_automatica = bool(
        st.session_state.pop("descargar_orden_automaticamente", False)
    )
    mostrar_orden_despacho_generada(
        orden_confirmada,
        descarga_automatica=descarga_automatica,
    )
    if st.button(
        "Cerrar orden generada",
        key="cerrar_orden_generada",
        use_container_width=True,
    ):
        st.session_state.pop("orden_despacho_generada", None)
        st.rerun()

if BACKEND_SEGURO_ACTIVO:
    st.success("🔒 Protección transaccional activa: bloqueo simultáneo e idempotencia habilitados.")
else:
    st.warning(
        "🟡 Protección local activa. Para impedir también choques entre usuarios o pestañas distintas, "
        "configura el Apps Script incluido con esta versión."
    )

# ---------- ESTADO Y DATOS ACTUALES DE BARRILES ----------
if "movimiento_guardando" not in st.session_state:
    st.session_state.movimiento_guardando = False
if "movimiento_solicitado" not in st.session_state:
    st.session_state.movimiento_solicitado = False

estado_barril = st.selectbox(
    "Estado del barril",
    ["Despacho", "Lavado en bodega", "Sucio", "En cuarto frío"],
    key="mov_estado",
    disabled=st.session_state.movimiento_guardando,
)

try:
    datos_barriles_ui = cargar_datos_barriles_ui()
    ultimos_barriles_ui = obtener_ultimos_movimientos(datos_barriles_ui)
except Exception as exc:
    datos_barriles_ui = pd.DataFrame()
    ultimos_barriles_ui = pd.DataFrame()
    st.error(f"No fue posible consultar el estado actual de los barriles: {exc}")

codigo_barril = ""
lote_producto = ""
estilo_cerveza = ""
ultimo_ui = None

if estado_barril == "Despacho":
    cuarto_frio_ui = barriles_actualmente_en_cuarto_frio(datos_barriles_ui)
    cuarto_frio_ui.sort_values(["Estilo", "Código"], inplace=True, ignore_index=True)
    mapa_barriles = {
        fila["Código"]: {
            "estilo": fila["Estilo"],
            "lote": fila["Lote"],
        }
        for _, fila in cuarto_frio_ui.iterrows()
    }
    opciones = [""] + list(mapa_barriles.keys())
    if st.session_state.get("mov_codigo_despacho", "") not in opciones:
        st.session_state.mov_codigo_despacho = ""

    codigo_barril = st.selectbox(
        "Barril a despachar",
        opciones,
        key="mov_codigo_despacho",
        format_func=lambda codigo: (
            "— Sin barril: despacho exclusivo de latas —"
            if codigo == ""
            else (
                f"{codigo} — {mapa_barriles[codigo]['estilo'] or 'Sin estilo'}"
                f" — lote {mapa_barriles[codigo]['lote'] or 'sin lote'}"
            )
        ),
        disabled=st.session_state.movimiento_guardando,
        help="La lista contiene únicamente barriles cuyo último estado es En cuarto frío.",
    )

    if codigo_barril:
        datos_seleccionados = mapa_barriles[codigo_barril]
        estilo_cerveza = datos_seleccionados["estilo"]
        lote_producto = datos_seleccionados["lote"]
        ultimo_ui = obtener_ultimo_movimiento(datos_barriles_ui, codigo_barril)
        st.success(
            f"✅ Disponible para despacho: {codigo_barril} · "
            f"{estilo_cerveza or 'Sin estilo'} · lote {lote_producto or 'sin lote'}"
        )
    elif cuarto_frio_ui.empty:
        st.info("No hay barriles actualmente disponibles en cuarto frío. Aún puedes despachar solo latas.")
else:
    codigo_barril = st.text_input(
        "Código del barril (5 dígitos; inicia por 20, 30 o 58)",
        key="mov_codigo_manual",
        disabled=st.session_state.movimiento_guardando,
    ).strip()
    if codigo_barril:
        ultimo_ui = obtener_ultimo_movimiento(datos_barriles_ui, codigo_barril)
        if ultimo_ui is not None:
            st.caption(
                f"Último estado registrado: {ultimo_ui['Estado'] or 'Sin estado'}"
                + (f" · cliente: {ultimo_ui['Cliente']}" if ultimo_ui["Cliente"] else "")
            )
            if normalizar_clave(ultimo_ui["Estado"]) == normalizar_clave(estado_barril):
                st.error(f"🚫 Este barril ya tiene como último estado '{estado_barril}'.")
        else:
            st.caption("El código no tiene movimientos anteriores registrados.")

if estado_barril == "En cuarto frío":
    lote_producto = st.text_input(
        "Lote del producto",
        key="mov_lote",
        disabled=st.session_state.movimiento_guardando,
    ).strip()
    estilo_cerveza = st.selectbox(
        "Estilo",
        estilos,
        key="mov_estilo",
        disabled=st.session_state.movimiento_guardando,
    )

# ---------- CLIENTES ----------
try:
    df_clientes = cargar_hoja_csv(HOJA_CLIENTES).copy()
    df_clientes.columns = df_clientes.columns.astype(str).str.strip()
    if "Nombre" not in df_clientes.columns:
        raise ValueError("La hoja RClientes no contiene la columna Nombre.")
    df_clientes["Nombre"] = df_clientes["Nombre"].fillna("").astype(str).str.strip()
    df_clientes = df_clientes[df_clientes["Nombre"].ne("")]
    lista_clientes = df_clientes["Nombre"].drop_duplicates().tolist()
    if "Dirección" in df_clientes.columns:
        dict_direcciones = df_clientes.drop_duplicates("Nombre").set_index("Nombre")["Dirección"].to_dict()
    else:
        dict_direcciones = {}
except Exception as exc:
    lista_clientes = []
    dict_direcciones = {}
    if estado_barril == "Despacho":
        st.warning(f"No se pudieron cargar los clientes: {exc}")

cliente = "Planta Castiza"
direccion_cliente = ""
if estado_barril == "Despacho":
    if lista_clientes:
        cliente = st.selectbox(
            "Cliente",
            lista_clientes,
            key="mov_cliente",
            disabled=st.session_state.movimiento_guardando,
        )
        direccion_cliente = dict_direcciones.get(cliente, "")
        if direccion_cliente:
            st.text_input(
                "Dirección del cliente",
                value=str(direccion_cliente),
                disabled=True,
                key="mov_direccion_cliente",
            )
    else:
        cliente = st.text_input(
            "Cliente",
            key="mov_cliente_manual",
            disabled=st.session_state.movimiento_guardando,
        ).strip()

# ---------- DESPACHO DE LATAS ----------
latas = []
errores_configuracion_latas = []
inventario_latas = pd.DataFrame()
incluye_latas = "No"

if estado_barril == "Despacho":
    incluye_latas = st.selectbox(
        "¿🚚 Incluye despacho de latas?",
        ["No", "Sí"],
        key="incluye_latas_despacho",
        disabled=st.session_state.movimiento_guardando,
    )

    if incluye_latas == "Sí":
        st.markdown(
            "<h4 style='color:#fff3aa;'>🚚 Detalles de despacho de latas</h4>",
            unsafe_allow_html=True,
        )

        if st.button(
            "🔄 Actualizar inventario de latas",
            key="actualizar_inventario_latas",
            disabled=st.session_state.movimiento_guardando,
        ):
            cargar_hoja_csv.clear()
            st.rerun()

        try:
            inventario_latas = calcular_inventario_latas()
        except Exception as exc:
            st.error(f"❌ No se pudo calcular el inventario de latas: {exc}")
            errores_configuracion_latas.append("No fue posible consultar el inventario de latas.")

        if inventario_latas.empty:
            st.warning("⚠️ No hay lotes de latas con existencias disponibles.")
            errores_configuracion_latas.append("No hay inventario de latas disponible para despachar.")
        else:
            resumen_estilos = (
                inventario_latas.groupby("Estilo", as_index=False)["Disponible"]
                .sum()
                .sort_values("Estilo", key=lambda serie: serie.astype(str).str.casefold())
            )
            st.caption("Existencias actuales por estilo")
            st.dataframe(resumen_estilos, hide_index=True, use_container_width=True)

            if "num_latas" not in st.session_state:
                st.session_state.num_latas = 1

            estilos_disponibles = inventario_latas["Estilo"].drop_duplicates().tolist()
            opcion_vacia_estilo = "— Selecciona un estilo —"
            opcion_vacia_lote = "— Selecciona un lote —"

            for indice in range(st.session_state.num_latas):
                st.markdown(f"### Orden {indice + 1}")
                estilo_lata = st.selectbox(
                    f"Estilo de cerveza (Orden {indice + 1})",
                    [opcion_vacia_estilo] + estilos_disponibles,
                    key=f"estilo_lata_{indice}",
                    disabled=st.session_state.movimiento_guardando,
                )

                if estilo_lata == opcion_vacia_estilo:
                    errores_configuracion_latas.append(
                        f"Selecciona el estilo de la orden {indice + 1}."
                    )
                    st.selectbox(
                        f"Lote disponible (Orden {indice + 1})",
                        [opcion_vacia_lote],
                        key=f"lote_lata_{indice}",
                        disabled=True,
                    )
                    continue

                inventario_estilo = inventario_latas[
                    inventario_latas["Estilo"] == estilo_lata
                ].copy()
                disponibilidad_por_lote = {
                    fila.Lote: int(fila.Disponible)
                    for fila in inventario_estilo.itertuples(index=False)
                }
                lotes_disponibles = list(disponibilidad_por_lote.keys())
                lote_lata = st.selectbox(
                    f"Lote disponible (Orden {indice + 1})",
                    [opcion_vacia_lote] + lotes_disponibles,
                    format_func=lambda lote, mapa=disponibilidad_por_lote: (
                        lote if lote == opcion_vacia_lote
                        else f"{lote} — {mapa[lote]} latas disponibles"
                    ),
                    key=f"lote_lata_{indice}",
                    disabled=st.session_state.movimiento_guardando,
                )

                if lote_lata == opcion_vacia_lote:
                    errores_configuracion_latas.append(
                        f"Selecciona el lote de la orden {indice + 1}."
                    )
                    continue

                disponible_lote = disponibilidad_por_lote[lote_lata]
                cantidad_key = f"cantidad_lata_{indice}"
                if cantidad_key in st.session_state:
                    cantidad_actual = int(st.session_state[cantidad_key])
                    st.session_state[cantidad_key] = min(max(cantidad_actual, 1), disponible_lote)

                cantidad = st.number_input(
                    f"Cantidad (Orden {indice + 1})",
                    min_value=1,
                    max_value=disponible_lote,
                    step=1,
                    key=cantidad_key,
                    disabled=st.session_state.movimiento_guardando,
                    help=f"Máximo disponible para este lote: {disponible_lote}",
                )
                latas.append(
                    {"cantidad": int(cantidad), "estilo": estilo_lata, "lote": lote_lata}
                )

            columnas_orden = st.columns(2)
            if columnas_orden[0].button(
                "➕ Agregar otro lote",
                key="agregar_orden_latas",
                disabled=st.session_state.movimiento_guardando,
            ):
                st.session_state.num_latas += 1
                st.rerun()

            if columnas_orden[1].button(
                "➖ Quitar última orden",
                key="quitar_orden_latas",
                disabled=(
                    st.session_state.movimiento_guardando
                    or st.session_state.num_latas <= 1
                ),
            ):
                indice = st.session_state.num_latas - 1
                for prefijo in ("estilo_lata_", "lote_lata_", "cantidad_lata_"):
                    st.session_state.pop(f"{prefijo}{indice}", None)
                st.session_state.num_latas -= 1
                st.rerun()

# ---------- RESPONSABLE Y OBSERVACIONES ----------
responsables = [
    "Pepe Vallejo", "Ligia Cajigas", "Erika Martinez", "Marcelo Martinez",
    "Yimer Luna", "Operario 2"
]
responsable = st.selectbox(
    "Responsable",
    responsables,
    key="mov_responsable",
    disabled=st.session_state.movimiento_guardando,
)
observaciones = st.text_area(
    "Observaciones",
    key="mov_observaciones",
    disabled=st.session_state.movimiento_guardando,
)

# ---------- VISTA PREVIA DE LA ORDEN QUE SE GENERARÁ AL CONFIRMAR ----------
if estado_barril == "Despacho":
    st.markdown("---")
    st.markdown(
        "<h3 style='color:#fff3aa;'>📄 Orden de pedido automática</h3>",
        unsafe_allow_html=True,
    )

    items_orden = construir_items_orden_despacho(
        codigo_barril,
        estilo_cerveza,
        lote_producto,
        latas,
        observaciones,
    )

    if items_orden:
        st.caption("Productos que se incluirán en los formatos cuando el despacho sea confirmado")
        st.dataframe(pd.DataFrame(items_orden), hide_index=True, use_container_width=True)
        st.info(
            "Al finalizar correctamente el registro se generarán automáticamente F-TRZ-002 y "
            "F-TRZ-003, completos y listos para imprimir y firmar."
        )
    else:
        st.info("Selecciona un barril y/o completa las latas del despacho.")

st.caption(
    "Al presionar Guardar, el botón se bloquea hasta terminar. No es necesario volver a hacer clic aunque la conexión esté lenta."
)
st.button(
    "🔒 Guardar Registro",
    key="guardar_movimiento_principal",
    type="primary",
    use_container_width=True,
    disabled=st.session_state.movimiento_guardando,
    on_click=solicitar_guardado_movimiento,
)

# ---------- PROCESAR EXACTAMENTE UNA VEZ POR CLIC ----------
if st.session_state.get("movimiento_solicitado", False):
    errores_guardado = []
    registrar_barril = bool(codigo_barril.strip())
    despacho_solo_latas = (
        estado_barril == "Despacho"
        and incluye_latas == "Sí"
        and not registrar_barril
    )

    if not registrar_barril and not despacho_solo_latas:
        errores_guardado.append(
            "Debes seleccionar o ingresar un barril. Solo puede quedar vacío en un despacho exclusivo de latas."
        )

    if estado_barril == "Despacho" and not str(cliente).strip():
        errores_guardado.append("Debes seleccionar o ingresar el cliente del despacho.")

    if estado_barril == "Despacho":
        items_para_formato = construir_items_orden_despacho(
            codigo_barril,
            estilo_cerveza,
            lote_producto,
            latas,
            observaciones,
        )
        if not items_para_formato:
            errores_guardado.append(
                "El despacho no contiene productos para diligenciar la orden."
            )
        elif len(items_para_formato) > MAX_LINEAS_FORMATO_DESPACHO:
            errores_guardado.append(
                f"El formato admite máximo {MAX_LINEAS_FORMATO_DESPACHO} líneas de producto; "
                f"este despacho tiene {len(items_para_formato)}."
            )

    datos_barriles_frescos = pd.DataFrame()
    ultimo_fresco = None
    if registrar_barril:
        try:
            cargar_datos_barriles_ui.clear()
            datos_barriles_frescos = cargar_datos_barriles_frescos()
        except Exception as exc:
            errores_guardado.append(
                f"No se pudo verificar el estado actual del barril. No se registró nada: {exc}"
            )
        else:
            valido, mensaje, ultimo_fresco = validar_movimiento_barril_local(
                datos_barriles_frescos,
                codigo_barril,
                estado_barril,
                estilo=estilo_cerveza,
                lote=lote_producto,
            )
            if not valido:
                errores_guardado.append(mensaje)

            if movimiento_local_reciente(codigo_barril, estado_barril):
                errores_guardado.append(
                    "Este mismo movimiento fue confirmado recientemente en esta sesión. "
                    "Se bloqueó para evitar un duplicado mientras Google actualiza la hoja."
                )

            if estado_barril == "Despacho" and ultimo_fresco is not None:
                estilo_cerveza = str(ultimo_fresco.get("Estilo", "")).strip()
                lote_producto = str(ultimo_fresco.get("Lote", "")).strip()

    inventario_actual = inventario_latas
    if incluye_latas == "Sí":
        errores_guardado.extend(errores_configuracion_latas)
        if not errores_configuracion_latas:
            try:
                cargar_hoja_csv.clear()
                inventario_actual = calcular_inventario_latas()
                errores_guardado.extend(validar_existencias_latas(latas, inventario_actual))
            except Exception as exc:
                errores_guardado.append(
                    f"No fue posible validar el inventario actualizado de latas: {exc}"
                )

    if errores_guardado:
        guardar_resultado_y_reiniciar(
            "error",
            "La operación fue bloqueada y no se registró ningún movimiento.",
            list(dict.fromkeys(errores_guardado)),
            conservar_operacion=False,
        )

    datos_huella = {
        "codigo": codigo_barril,
        "estado": estado_barril,
        "cliente": cliente,
        "responsable": responsable,
        "observaciones": observaciones,
        "lote": lote_producto,
        "estilo": estilo_cerveza,
        "incluye_latas": incluye_latas,
        "latas": latas,
    }
    huella = construir_huella_operacion(datos_huella)
    operacion_id = obtener_operacion_id_para_huella(huella)
    payload_seguro = dict(datos_huella)
    payload_seguro["operacion_id"] = operacion_id

    with st.spinner("Validando y registrando. No cierres la página ni vuelvas a presionar el botón..."):
        if BACKEND_SEGURO_ACTIVO:
            exito, mensaje, reintentable, respuesta_extra = enviar_backend_apps_script(payload_seguro)
        else:
            exito, mensaje, reintentable, respuesta_extra = enviar_por_formularios_compatibilidad(payload_seguro)

    if exito:
        marcar_movimiento_local_confirmado(codigo_barril, estado_barril, operacion_id)
        cargar_hoja_csv.clear()
        cargar_datos_barriles_ui.clear()
        detalle = []

        if respuesta_extra.get("duplicate"):
            detalle.append("El servidor reconoció el identificador de operación y evitó reenviarla.")
        elif registrar_barril and estado_barril == "Despacho":
            detalle.append(
                f"Barril {codigo_barril} despachado a {cliente}. Ya no aparecerá entre los barriles de cuarto frío."
            )

        # La orden se crea solo después de que el despacho completo fue confirmado.
        if estado_barril == "Despacho":
            try:
                items_confirmados = construir_items_orden_despacho(
                    codigo_barril,
                    estilo_cerveza,
                    lote_producto,
                    latas,
                    observaciones,
                )
                orden_confirmada = preparar_orden_despacho_para_descarga(
                    items_confirmados,
                    cliente,
                    direccion_cliente,
                    responsable,
                    observaciones,
                    operacion_id,
                    fecha=datetime.now(),
                )
                st.session_state.orden_despacho_generada = orden_confirmada
                st.session_state.descargar_orden_automaticamente = True
                detalle.append(
                    "Se diligenciaron automáticamente F-TRZ-002 y F-TRZ-003 con todos los productos registrados."
                )
            except Exception as exc:
                detalle.append(
                    "El despacho quedó registrado, pero no fue posible construir la orden para firma: "
                    f"{exc}"
                )

        limpiar_widgets_movimiento()
        guardar_resultado_y_reiniciar(
            "success",
            mensaje,
            detalle,
            conservar_operacion=False,
        )
    else:
        tipo_resultado = "warning" if reintentable else "error"
        detalles = []
        if reintentable:
            detalles.append(
                f"Identificador conservado: {operacion_id}. Al reintentar, el servidor no duplicará una operación que ya haya recibido."
            )
        guardar_resultado_y_reiniciar(
            tipo_resultado,
            mensaje,
            detalles,
            conservar_operacion=reintentable,
        )

# Mantener la variable utilizada por las secciones inferiores de búsqueda y últimos movimientos.
url_datos = URL_DATOS_BARRILES_PUBLICA

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
        st.dataframe(df_filtrado[["Marca temporal","Código", "Estilo", "Estado", "Cliente", "Responsable", "Observaciones"]])
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
