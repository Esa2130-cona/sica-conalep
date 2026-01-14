import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import pytz

# ================= CONFIG =================
st.set_page_config(page_title="SICA CONALEP", layout="wide")
zona = pytz.timezone("America/Mexico_City")

SHEET_ID = "11RZyoBo_MyQkGWfc21WCY_xPFZdKkwTG12YagiZf3yM"
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbwwTQehk_CODj_-8ZNeZRu2hYudq66I2FpJR8rqrZ9_6HeFy3I_zPgKIGMGvShua_71GQ/exec"

GID_ALUMNOS = 0
GID_USUARIOS = 111
GID_ENTRADAS = 222
GID_INCIDENCIAS = 333
GID_ACADEMICO = 444

# ================= UTIL =================
@st.cache_data(ttl=10)
def cargar(gid):
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={gid}"
    df = pd.read_csv(url)
    df.columns = [c.strip().upper() for c in df.columns]
    return df

df_alumnos = cargar(GID_ALUMNOS)
df_usuarios = cargar(GID_USUARIOS)
df_entradas = cargar(GID_ENTRADAS)
df_incidencias = cargar(GID_INCIDENCIAS)
df_academico = cargar(GID_ACADEMICO)

# ================= LOGIN =================
if "user" not in st.session_state:
    st.session_state.user = None

if not st.session_state.user:
    st.title("🔐 SICA - CONALEP CUAUTLA")
    u = st.text_input("Usuario")
    p = st.text_input("PIN", type="password")
    if st.button("Ingresar"):
        m = df_usuarios[
            (df_usuarios["USUARIO"].str.lower() == u.lower()) &
            (df_usuarios["PIN"].astype(str) == p)
        ]
        if not m.empty:
            st.session_state.user = m.iloc[0].to_dict()
            st.rerun()
        else:
            st.error("Credenciales incorrectas")
    st.stop()

user = st.session_state.user

# ================= MENU =================
opciones = set(["Puerta de Entrada", "Historial Alumnos"])
rol = user["ROL"].upper()

if rol == "ADMIN":
    opciones |= {"Incidencias", "Academico", "Reportes"}

elif rol == "PREFECTO":
    opciones |= {"Incidencias", "Reportes"}

elif rol == "SERVICIOS_ESCOLARES":
    opciones.add("Incidencias")

elif rol == "FORMACION":
    opciones.add("Academico")

menu = st.sidebar.radio("MENÚ", sorted(opciones))
st.sidebar.button("Cerrar sesión", on_click=lambda: st.session_state.update(user=None))

# ================= PUERTA =================
if menu == "Puerta de Entrada":
    st.title("🚪 Registro de Entrada")
    mat = st.text_input("Escanee matrícula").replace("'", "-").strip()

    if mat:
        a = df_alumnos[df_alumnos["MATRICULA"] == mat]
        if a.empty:
            st.error("Alumno no encontrado")
        else:
            al = a.iloc[0]
            payload = {
                "TIPO_REGISTRO": "ENTRADA",
                "FECHA": datetime.now(zona).strftime("%Y-%m-%d"),
                "HORA": datetime.now(zona).strftime("%H:%M:%S"),
                "MATRICULA": mat,
                "NOMBRE": f"{al['NOMBRE']} {al['PRIMER APELLIDO']}",
                "GRUPO": al["GRUPO"],
                "REGISTRO_POR": user["NOMBRE"]
            }
            requests.post(APPS_SCRIPT_URL, json=payload)
            st.success("Acceso registrado")

# ================= INCIDENCIAS =================
elif menu == "Incidencias":
    st.title("🚨 Incidencias")
    mat = st.text_input("Matrícula").replace("'", "-").strip()
    if mat:
        al = df_alumnos[df_alumnos["MATRICULA"] == mat]
        if not al.empty:
            al = al.iloc[0]
            tipo = st.selectbox("Tipo", ["Retardo", "Falta", "Disciplina"])
            desc = st.text_area("Descripción")
            if st.button("Registrar incidencia"):
                requests.post(APPS_SCRIPT_URL, json={
                    "TIPO_REGISTRO": "INCIDENCIA",
                    "FECHA": datetime.now(zona).strftime("%Y-%m-%d"),
                    "HORA": datetime.now(zona).strftime("%H:%M:%S"),
                    "MATRICULA": mat,
                    "NOMBRE": al["NOMBRE"],
                    "GRUPO": al["GRUPO"],
                    "TIPO": tipo,
                    "DESCRIPCION": desc,
                    "REGISTRO_POR": user["NOMBRE"]
                })
                st.success("Incidencia registrada")

# ================= ACADEMICO =================
elif menu == "Academico":
    st.title("📚 Registro Académico")
    mat = st.text_input("Matrícula")
    materia = st.text_input("Materia")
    periodo = st.text_input("Periodo")
    cal = st.number_input("Calificación", 0, 100)
    if st.button("Guardar"):
        requests.post(APPS_SCRIPT_URL, json={
            "TIPO_REGISTRO": "ACADEMICO",
            "MATRICULA": mat,
            "MATERIA": materia,
            "PERIODO": periodo,
            "CALIFICACION": cal,
            "REGISTRO_POR": user["NOMBRE"]
        })
        st.success("Registro académico guardado")

# ================= HISTORIAL =================
elif menu == "Historial Alumnos":
    st.title("📊 Historial")
    tab1, tab2 = st.tabs(["Por alumno", "Por día"])

    with tab1:
        mat = st.text_input("Matrícula alumno")
        if mat:
            st.dataframe(df_entradas[df_entradas["MATRICULA"] == mat])

    with tab2:
        f = st.date_input("Fecha")
        st.dataframe(df_entradas[df_entradas["FECHA"] == str(f)])

# ================= REPORTES =================
elif menu == "Reportes":
    st.title("📈 Reporte mensual")
    df_entradas["FECHA"] = pd.to_datetime(df_entradas["FECHA"])
    mensual = df_entradas.groupby(df_entradas["FECHA"].dt.to_period("M")).size()
    st.bar_chart(mensual)


