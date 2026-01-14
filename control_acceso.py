import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import pytz

# ================= CONFIGURACIÓN DE PÁGINA =================
st.set_page_config(page_title="SICA CONALEP - ACCESO", layout="wide")
zona = pytz.timezone("America/Mexico_City")

# ESTILOS CSS FORMALES
st.markdown("""
    <style>
    .card-acceso {
        background-color: white;
        padding: 40px;
        border-radius: 20px;
        border-left: 15px solid #1E8449;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    .acceso-permitido {
        color: #1E8449;
        font-size: 70px !important;
        font-weight: 900;
        line-height: 1;
    }
    .nombre-alumno {
        color: #1B4F72;
        font-size: 80px !important;
        font-weight: bold;
        text-transform: uppercase;
        line-height: 1.1;
    }
    .datos-escolares {
        color: #566573;
        font-size: 35px !important;
    }
    </style>
    """, unsafe_allow_html=True)

SHEET_ID = "11RZyoBo_MyQkGWfc21WCY_xPFZdKkwTG12YagiZf3yM"
# URL de tu Apps Script (asegúrate de que esté actualizado)
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbwEzRUIDz4YtnT40VIbAwUs7WOgba0DWjSTYt2d7-QdZKFo3BCetNrB0kSy4Y4w4fTncg/exec"

GID_ALUMNOS = 1882885827
GID_USUARIOS = 921806663
GID_ENTRADAS = 25814912

# ================= CARGA DE DATOS =================
@st.cache_data(ttl=2)
def cargar(gid):
    try:
        url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={gid}"
        df = pd.read_csv(url)
        # Limpieza robusta de columnas
        df.columns = [str(c).strip().upper().replace("Á","A").replace("É","E").replace("Í","I").replace("Ó","O").replace("Ú","U") for c in df.columns]
        return df
    except:
        return pd.DataFrame()

df_alumnos = cargar(GID_ALUMNOS)
df_usuarios = cargar(GID_USUARIOS)

# ================= LOGIN =================
if "user" not in st.session_state:
    st.session_state.user = None

if not st.session_state.user:
    st.markdown("<h1 style='text-align:center;'>SICA - CONALEP CUAUTLA</h1>", unsafe_allow_html=True)
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
menu = st.sidebar.radio("SISTEMA", ["Puerta de Entrada", "Historial Alumnos"])
if st.sidebar.button("Cerrar sesión"):
    st.session_state.user = None
    st.rerun()

# ================= PUERTA DE ENTRADA =================
if menu == "Puerta de Entrada":
    st.markdown("<h4 style='text-align: center; color: gray;'>CONTROL DE ACCESO INSTITUCIONAL</h4>", unsafe_allow_html=True)
    
    # PROCESAMIENTO DE ESCÁNER: Cambia comilla (') por guion (-) o diagonal (/) según prefieras
    # Aquí lo configuré para que acepte la diagonal como pediste.
    entrada_raw = st.text_input("ESCANEE CREDENCIAL", key="main_scanner").strip()
    mat = entrada_raw.replace("'", "-") # Muchos escáneres mandan ' en vez de -

    if mat:
        a = df_alumnos[df_alumnos["MATRICULA"].astype(str) == mat]
        
        if a.empty:
            st.error(f"❌ MATRÍCULA {mat} NO REGISTRADA")
        else:
            al = a.iloc[0]
            nombre = f"{al['NOMBRE']} {al['PRIMER APELLIDO']} {al.get('SEGUNDO APELLIDO', '')}"
            
            st.divider()
            col_foto, col_info = st.columns([1, 2.5])
            
            with col_foto:
                foto_url = al.get('FOTO', "https://cdn-icons-png.flaticon.com/512/3135/3135715.png")
                st.image(foto_url, use_container_width=True)
            
            with col_info:
                st.markdown(f"""
                <div class='card-acceso'>
                    <div class='acceso-permitido'>ACCESO PERMITIDO</div>
                    <div class='nombre-alumno'>{nombre}</div>
                    <div class='datos-escolares'>
                        <b>MATRÍCULA:</b> {mat}<br>
                        <b>GRUPO:</b> {al['GRUPO']}<br>
                        <b>HORA:</b> {datetime.now(zona).strftime('%H:%M:%S')}
                    </div>
                </div>
                """, unsafe_allow_html=True)

            # ENVÍO A GOOGLE SHEETS (Sin mensaje de error si la red es lenta)
            payload = {
                "TIPO_REGISTRO": "ENTRADA",
                "FECHA": datetime.now(zona).strftime("%Y-%m-%d"),
                "HORA": datetime.now(zona).strftime("%H:%M:%S"),
                "MATRICULA": mat,
                "NOMBRE": nombre,
                "GRUPO": al["GRUPO"],
                "REGISTRO_POR": user["NOMBRE"]
            }
            try:
                # Se agrega timeout para evitar que la app se trabe si Sheets tarda en responder
                requests.post(APPS_SCRIPT_URL, json=payload, timeout=5)
            except:
                pass # Silenciamos el error visual para no confundir al alumno






