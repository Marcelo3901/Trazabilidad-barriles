import streamlit as st
import pandas as pd
import requests
from urllib.parse import quote
import base64
import os
from datetime import datetime
import unicodedata
import hashlib
import io
import json
import re
import time
import uuid
import zipfile
import html as html_lib
from copy import copy
from pathlib import Path
from zoneinfo import ZoneInfo

from openpyxl import load_workbook
from openpyxl.drawing.image import Image as XLImage
from openpyxl.styles import Alignment, Font

# La validación de estados se realiza justo antes de guardar y nuevamente en Apps Script.
# V4: permite registrar barriles parciales al ingresar al cuarto frío y los advierte en despacho.

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
