import json
from oauth2client.service_account import ServiceAccountCredentials

SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
import os

# Asegúrate de que st.secrets["gcp_service_account"] (o tu variable de entorno) esté configurada correctamente.
# Si estás usando st.secrets, asegúrate de haber configurado el archivo .streamlit/secrets.toml o la sección de Secrets en Streamlit Cloud.

with open("credentials.json", "r") as f:
    cred_dict = json.load(f)

credentials = ServiceAccountCredentials.from_json_keyfile_dict(cred_dict, SCOPE)
print("Credenciales cargadas correctamente")


