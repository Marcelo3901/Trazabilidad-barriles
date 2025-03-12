import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json

# Definir el alcance de acceso
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# Obtener las credenciales desde st.secrets
credentials_dict = st.secrets["gcp_service_account"]

# Convertir el diccionario a JSON string y luego cargarlo con gspread
credentials = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, SCOPE)

# Autenticar con gspread
gc = gspread.authorize(credentials)

