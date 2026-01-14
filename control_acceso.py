import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import pytz
import time

# ================= CONFIGURACIÓN =================
st.set_page_config(page_title="SICA CONALEP CUAUTLA", layout="wide")
zona = pytz.timezone("America/Mexico_City")

# ESTILOS FORMALES
st.markdown("""
    <style>
    .card-acceso {
        background-color: white; padding: 40px; border-radius: 20px;
        border-left: 15px solid #1E8449; box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    .acceso-permitido { color: #1E8449; font-size: 65px !important; font-weight: 900; }
    .nombre-alumno { color: #1B4F72; font-size: 80px !important; font-weight: bold; text-transform: uppercase; }
    .datos-escolares { color: #566573; font-size: 35px !important; }
    </style>
    """, unsafe_allow_html=True)

SHEET_ID = "11RZyoBo_MyQkGWfc21WCY_xPFZdKkwTG12YagiZf3yM"
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbwEzRUIDz4YtnT40VIbAwUs7WOgba0DWjSTYt2d7-QdZKFo3BCetNrB0kSy4Y4w4fTncg/exec"

GID_ALUMNOS = 1882885827
GID_USUARIOS = 921806663
GID_ENTRADAS = 25814912
GID_INCIDENCIAS = 2080119575
GID_ACADEMICO = 1794524153

# ================= CARGA DE DATOS =================
@st.cache_data(ttl=2)
def cargar(gid):
    try:
        url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={gid}"
        df = pd.read_csv(url)
        df.columns = [str(c).strip().upper().replace("Á","A").replace("É","E").replace("Í","I").replace("Ó","O").replace("Ú","U") for c in df.columns]
        return df
    except: return pd.DataFrame()

df_alumnos = cargar(GID_ALUMNOS)
df_usuarios = cargar(GID_USUARIOS)
df_entradas = cargar(GID_ENTRADAS)

# ================= LOGIN =================
if "user" not in st.session_state: st.session_state.user = None

if not st.session_state.user:
    st.title("🔐 SICA - CONALEP CUAUTLA")
    u = st.text_input("Usuario")
    p = st.text_input("PIN", type="password")
    if st.button("Ingresar"):
        if not df_usuarios.empty:
            m = df_usuarios[(df_usuarios["USUARIO"].astype(str).str.lower() == u.lower()) & (df_usuarios["PIN"].astype(str) == p)]
            if not m.empty:
                st.session_state.user = m.iloc[0].to_dict()
                st.rerun()
            else: st.error("Credenciales incorrectas")
    st.stop()

user = st.session_state.user

# ================= MENÚ LATERAL =================
opciones = ["Puerta de Entrada", "Historial Alumnos"]
rol = str(user.get("ROL", "")).upper()
if rol == "ADMIN": opciones += ["Incidencias", "Academico"]

menu = st.sidebar.radio("SISTEMA", opciones)
st.sidebar.button("Cerrar sesión", on_click=lambda: st.session_state.update(user=None))

# ================= MODULOS =================

if menu == "Puerta de Entrada":
    st.markdown("<h4 style='text-align: center;'>CONTROL DE ACCESO</h4>", unsafe_allow_html=True)
    
    # Lógica de auto-limpieza usando session_state
    if "last_mat" not in st.session_state: st.session_state.last_mat = ""

    def registrar_y_limpiar():
        st.session_state.last_mat = st.session_state.widget_scanner
        st.session_state.widget_scanner = ""

    mat_input = st.text_input("ESCANEE CREDENCIAL", key="widget_scanner", on_change=registrar_y_limpiar).strip()
    mat = st.session_state.last_mat.replace("'", "-")

    if mat:
        a = df_alumnos[df_alumnos["MATRICULA"].astype(str) == mat]
        if a.empty:
            st.error(f"❌ MATRÍCULA {mat} NO REGISTRADA")
        else:
            al = a.iloc[0]
            nombre = f"{al['NOMBRE']} {al['PRIMER APELLIDO']} {al.get('SEGUNDO APELLIDO', '')}"
            st.divider()
            c1, c2 = st.columns([1, 2.5])
            with c1: st.image(al.get('FOTO', "https://cdn-icons-png.flaticon.com/512/3135/3135715.png"), use_container_width=True)
            with c2:
                st.markdown(f"<div class='card-acceso'><div class='acceso-permitido'>ACCESO PERMITIDO</div><div class='nombre-alumno'>{nombre}</div><div class='datos-escolares'><b>GRUPO:</b> {al['GRUPO']}<br><b>HORA:</b> {datetime.now(zona).strftime('%H:%M:%S')}</div></div>", unsafe_allow_html=True)
            
            requests.post(APPS_SCRIPT_URL, json={
                "TIPO_REGISTRO": "ENTRADA", "FECHA": datetime.now(zona).strftime("%Y-%m-%d"),
                "HORA": datetime.now(zona).strftime("%H:%M:%S"), "MATRICULA": mat,
                "NOMBRE": nombre, "GRUPO": al["GRUPO"], "REGISTRO_POR": user["NOMBRE"]
            }, timeout=3)

elif menu == "Incidencias":
    st.title("🚨 Incidencias")
    mat_i = st.text_input("Matrícula")
    if mat_i:
        al_i = df_alumnos[df_alumnos["MATRICULA"].astype(str) == mat_i]
        if not al_i.empty:
            al_i = al_i.iloc[0]
            st.info(f"Alumno: {al_i['NOMBRE']}")
            tipo = st.selectbox("Tipo", ["Retardo", "Falta", "Disciplina"])
            desc = st.text_area("Descripción")
            if st.button("Guardar"):
                requests.post(APPS_SCRIPT_URL, json={"TIPO_REGISTRO": "INCIDENCIA", "FECHA": datetime.now(zona).strftime("%Y-%m-%d"), "HORA": datetime.now(zona).strftime("%H:%M:%S"), "MATRICULA": mat_i, "NOMBRE": al_i["NOMBRE"], "GRUPO": al_i["GRUPO"], "TIPO": tipo, "DESCRIPCION": desc, "REGISTRO_POR": user["NOMBRE"]})
                st.success("Guardado")

elif menu == "Academico":
    st.title("📚 Académico")
    mat_a = st.text_input("Matrícula")
    materia = st.text_input("Materia")
    cal = st.number_input("Calificación", 0, 100)
    if st.button("Registrar"):
        requests.post(APPS_SCRIPT_URL, json={"TIPO_REGISTRO": "ACADEMICO", "MATRICULA": mat_a, "MATERIA": materia, "CALIFICACION": cal, "REGISTRO_POR": user["NOMBRE"]})
        st.success("Calificación guardada")

elif menu == "Historial Alumnos":
    st.title("📊 Historial")
    busqueda = st.text_input("Matrícula")
    if busqueda:
        st.dataframe(df_entradas[df_entradas["MATRICULA"].astype(str) == busqueda], use_container_width=True)






