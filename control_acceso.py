import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import pytz
import threading
import base64

# ================= CONFIGURACIÓN =================
st.set_page_config(page_title="SICA CONALEP CUAUTLA", layout="wide")
zona = pytz.timezone("America/Mexico_City")

# ESTILOS FORMALES E INSTITUCIONALES (Incluye Alerta Roja)
st.markdown("""
    <style>
    .card-acceso {
        background-color: white; padding: 40px; border-radius: 20px;
        border-left: 15px solid #1E8449; box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    .card-error {
        background-color: #FDEDEC; padding: 40px; border-radius: 20px;
        border: 5px solid #CB4335; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.2);
    }
    .acceso-permitido { color: #1E8449; font-size: 65px !important; font-weight: 900; line-height: 1; }
    .acceso-denegado { color: #CB4335; font-size: 75px !important; font-weight: 900; }
    .nombre-alumno { color: #1B4F72; font-size: 75px !important; font-weight: bold; text-transform: uppercase; line-height: 1.1; }
    .msg-error { color: #943126; font-size: 50px !important; font-weight: bold; }
    .datos-escolares { color: #566573; font-size: 35px !important; margin-top: 10px; }
    </style>
    """, unsafe_allow_html=True)

# Función para reproducir sonido de alerta
def play_audio(file_url):
    audio_html = f"""
        <audio autoplay>
            <source src="{file_url}" type="audio/mp3">
        </audio>
    """
    st.components.v1.html(audio_html, height=0)

SHEET_ID = "11RZyoBo_MyQkGWfc21WCY_xPFZdKkwTG12YagiZf3yM"
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbwEzRUIDz4YtnT40VIbAwUs7WOgba0DWjSTYt2d7-QdZKFo3BCetNrB0kSy4Y4w4fTncg/exec"

GIDS = {
    "ALUMNOS": 1882885827,
    "USUARIOS": 921806663,
    "ENTRADAS": 25814912,
    "INCIDENCIAS": 2080119575,
    "ACADEMICO": 1794524153
}

# ================= FUNCIONES =================
@st.cache_data(ttl=5)
def cargar(gid):
    try:
        url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={gid}"
        df = pd.read_csv(url)
        df.columns = [str(c).strip().upper().replace("Á","A").replace("É","E").replace("Í","I").replace("Ó","O").replace("Ú","U") for c in df.columns]
        return df
    except: return pd.DataFrame()

def enviar_registro_background(payload):
    try: requests.post(APPS_SCRIPT_URL, json=payload, timeout=10)
    except: pass

# ================= LOGIN =================
if "user" not in st.session_state: st.session_state.user = None
df_usuarios = cargar(GIDS["USUARIOS"])

if not st.session_state.user:
    st.title("🔐 SICA - CONALEP CUAUTLA")
    u = st.text_input("Usuario")
    p = st.text_input("PIN", type="password")
    if st.button("Ingresar"):
        if not df_usuarios.empty and "USUARIO" in df_usuarios.columns:
            m = df_usuarios[(df_usuarios["USUARIO"].astype(str).str.lower() == u.lower()) & (df_usuarios["PIN"].astype(str) == p)]
            if not m.empty:
                st.session_state.user = m.iloc[0].to_dict()
                st.rerun()
            else: st.error("Credenciales incorrectas")
    st.stop()

user = st.session_state.user

# ================= MENÚ =================
opciones = ["Puerta de Entrada", "Historial Alumnos"]
rol = str(user.get("ROL", "")).upper()
if rol == "ADMIN": opciones += ["Incidencias", "Academico"]
elif rol == "PREFECTO": opciones += ["Incidencias"]

menu = st.sidebar.radio("MENÚ PRINCIPAL", opciones)
st.sidebar.button("Cerrar sesión", on_click=lambda: st.session_state.update(user=None))

# ================= MÓDULOS =================

if menu == "Puerta de Entrada":
    df_alumnos = cargar(GIDS["ALUMNOS"])
    st.markdown("<h4 style='text-align: center; color: gray;'>ESCANEE CREDENCIAL</h4>", unsafe_allow_html=True)
    
    if "input_val" not in st.session_state: st.session_state.input_val = ""
    def procesar_escaneo():
        st.session_state.input_val = st.session_state.temp_input
        st.session_state.temp_input = ""

    st.text_input("Esperando lectura...", key="temp_input", on_change=procesar_escaneo)
    
    mat = st.session_state.input_val.replace("'", "-").strip()

    if mat:
        a = df_alumnos[df_alumnos["MATRICULA"].astype(str) == mat]
        
        if a.empty:
            # --- ALERTA VISUAL Y SONORA DE ERROR ---
            play_audio("https://www.soundjay.com/buttons/beep-04.mp3") # Sonido de alerta
            st.markdown(f"""
                <div class='card-error'>
                    <div class='acceso-denegado'>🚫 ACCESO NO PERMITIDO</div>
                    <div class='msg-error'>MATRÍCULA NO REGISTRADA O BAJA</div>
                    <p style='font-size:30px;'>La matrícula <b>{mat}</b> no existe en la base de datos.</p>
                </div>
            """, unsafe_allow_html=True)
        else:
            al = a.iloc[0]
            nombre = f"{al['NOMBRE']} {al['PRIMER APELLIDO']} {al.get('SEGUNDO APELLIDO', '')}"
            st.divider()
            c1, c2 = st.columns([1, 2.5])
            with c1: st.image(al.get('FOTO', "https://cdn-icons-png.flaticon.com/512/3135/3135715.png"), use_container_width=True)
            with c2:
                st.markdown(f"""
                <div class='card-acceso'>
                    <div class='acceso-permitido'>✅ ACCESO PERMITIDO</div>
                    <div class='nombre-alumno'>{nombre}</div>
                    <div class='datos-escolares'><b>GRUPO:</b> {al['GRUPO']}<br><b>HORA:</b> {datetime.now(zona).strftime('%H:%M:%S')}</div>
                </div>
                """, unsafe_allow_html=True)
            
            payload = {"TIPO_REGISTRO": "ENTRADA", "FECHA": datetime.now(zona).strftime("%Y-%m-%d"), "HORA": datetime.now(zona).strftime("%H:%M:%S"), "MATRICULA": mat, "NOMBRE": nombre, "GRUPO": al["GRUPO"], "REGISTRO_POR": user["NOMBRE"]}
            threading.Thread(target=enviar_registro_background, args=(payload,)).start()

elif menu == "Incidencias":
    st.title("🚨 Registro de Incidencias")
    df_alumnos = cargar(GIDS["ALUMNOS"])
    mat_i = st.text_input("Escanee o ingrese matrícula", key="inc_input").replace("'", "-").strip()
    if mat_i:
        res = df_alumnos[df_alumnos["MATRICULA"].astype(str) == mat_i]
        if not res.empty:
            al = res.iloc[0]
            st.success(f"Alumno: {al['NOMBRE']} {al['PRIMER APELLIDO']}")
            tipo = st.selectbox("Tipo de reporte", ["Retardo", "Falta", "Indisciplina", "Uniforme"])
            obs = st.text_area("Observaciones")
            if st.button("Guardar Incidencia"):
                threading.Thread(target=enviar_registro_background, args=({
                    "TIPO_REGISTRO": "INCIDENCIA", "FECHA": datetime.now(zona).strftime("%Y-%m-%d"),
                    "HORA": datetime.now(zona).strftime("%H:%M:%S"), "MATRICULA": mat_i,
                    "NOMBRE": al['NOMBRE'], "TIPO": tipo, "DESCRIPCION": obs, "REGISTRO_POR": user["NOMBRE"]
                },)).start()
                st.success("Incidencia enviada")
        else: st.warning("Matrícula no encontrada")

elif menu == "Academico":
    st.title("📚 Módulo Académico")
    mat_a = st.text_input("Escanee matrícula del alumno", key="acad_input").replace("'", "-").strip()
    materia = st.text_input("Materia")
    cal = st.number_input("Calificación", 0, 100)
    if st.button("Registrar Calificación"):
        payload = {"TIPO_REGISTRO": "ACADEMICO", "MATRICULA": mat_a, "MATERIA": materia, "CALIFICACION": cal, "REGISTRO_POR": user["NOMBRE"]}
        threading.Thread(target=enviar_registro_background, args=(payload,)).start()
        st.success("Registro académico enviado")

elif menu == "Historial Alumnos":
    st.title("📊 Consultas de Historial")
    df_entradas = cargar(GIDS["ENTRADAS"])
    m_busq = st.text_input("Escanee matrícula para buscar", key="hist_input").replace("'", "-").strip()
    if m_busq:
        st.dataframe(df_entradas[df_entradas["MATRICULA"].astype(str) == m_busq], use_container_width=True)
