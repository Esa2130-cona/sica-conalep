import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import os
import pytz

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="SICA Conalep Cuautla", layout="wide", page_icon="🛡️")

# Zona horaria de México
zona_horaria = pytz.timezone('America/Mexico_City')

# --- ESTILOS ---
st.markdown("""
    <style>
    .stApp { background-color: #F8F9FA; color: #212529; }
    h1, h2, h3 { color: #006437 !important; }
    .big-font { font-size:38px !important; font-weight: bold; color: #006437; }
    .status-box { 
        padding: 25px; border-radius: 20px; text-align: center; 
        background-color: #FFFFFF; border: 3px solid #006437; color: #006437;
        box-shadow: 0px 4px 15px rgba(0,0,0,0.1);
    }
    .aviso-box { 
        padding: 15px; background-color: #FFF3CD; color: #856404; 
        border-radius: 12px; border-left: 8px solid #FFC107; font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

# --- CONEXIÓN A GOOGLE SHEETS (REEMPLAZA LOS GIDs) ---
SHEET_ID = "11RZyoBo_MyQkGWfc21WCY_xPFZdKkwTG12YagiZf3yM"

# URLs con GIDs (Asegúrate de que correspondan a tus pestañas)
URL_ALUMNOS = f"https://docs.google.com/spreadsheets/d/11RZyoBo_MyQkGWfc21WCY_xPFZdKkwTG12YagiZf3yM/edit?gid=1882885827#gid=1882885827{SHEET_ID}/export?format=csv&gid=0"
URL_ACADEMICO = f"https://docs.google.com/spreadsheets/d/11RZyoBo_MyQkGWfc21WCY_xPFZdKkwTG12YagiZf3yM/edit?gid=1794524153#gid=1794524153{SHEET_ID}/export?format=csv&gid=1114227031"
URL_INCIDENCIAS = f"https://docs.google.com/spreadsheets/d/11RZyoBo_MyQkGWfc21WCY_xPFZdKkwTG12YagiZf3yM/edit?gid=2080119575#gid=2080119575{SHEET_ID}/export?format=csv&gid=569107936"
URL_USUARIOS = f"https://docs.google.com/spreadsheets/d/11RZyoBo_MyQkGWfc21WCY_xPFZdKkwTG12YagiZf3yM/edit?gid=921806663#gid=921806663{SHEET_ID}/export?format=csv&gid=1418859187"

@st.cache_data(ttl=10)
def cargar_datos(url):
    try:
        df = pd.read_csv(url)
        # Limpiar la columna MATRICULA de cualquier pestaña que la tenga
        if 'MATRICULA' in df.columns:
            df['MATRICULA'] = df['MATRICULA'].astype(str).str.strip()
        return df
    except:
        return pd.DataFrame()

# Cargar bases de datos
df_alumnos = cargar_datos(URL_ALUMNOS).set_index('MATRICULA')
df_academico = cargar_datos(URL_ACADEMICO).set_index('MATRICULA')
df_incidencias = cargar_datos(URL_INCIDENCIAS)
df_usuarios = cargar_datos(URL_USUARIOS)

# --- SISTEMA DE LOGIN ---
if 'user_data' not in st.session_state:
    st.session_state.user_data = None

if st.session_state.user_data is None:
    st.title("🛡️ SICA - Inicio de Sesión")
    u_input = st.text_input("Usuario")
    p_input = st.text_input("PIN", type="password")
    if st.button("INGRESAR"):
        # Validar contra la pestaña 'Usuarios' de tu Excel
        user_match = df_usuarios[(df_usuarios['USUARIO'] == u_input) & (df_usuarios['PIN'].astype(str) == p_input)]
        if not user_match.empty:
            st.session_state.user_data = user_match.iloc[0].to_dict()
            st.rerun()
        else:
            st.error("Usuario o PIN incorrectos")
    st.stop()

# --- INTERFAZ PRINCIPAL ---
user = st.session_state.user_data
st.sidebar.title(f"👤 {user['NOMBRE']}")
st.sidebar.write(f"Rol: {user['ROL']}")
if st.sidebar.button("Cerrar Sesión"):
    st.session_state.user_data = None
    st.rerun()

menu = st.sidebar.radio("Menú", ["Puerta de Entrada", "Historial Alumnos", "Gestión Administrativa"])

# --- MÓDULO 1: PUERTA DE ENTRADA ---
if menu == "Puerta de Entrada":
    st.title("🚀 Control de Acceso")
    
    if 'scanned_id' not in st.session_state: st.session_state.scanned_id = ""

    def procesar_escaneo():
        # Limpiar comilla y guardar
        raw = st.session_state.lector_input
        st.session_state.scanned_id = raw.replace("'", "-").strip()
        st.session_state.lector_input = ""

    st.text_input("👇 ESCANEE AQUÍ", key="lector_input", on_change=procesar_escaneo)
    
    mat = st.session_state.scanned_id
    
    if mat:
        if mat in df_alumnos.index:
            al = df_alumnos.loc[mat]
            c1, c2 = st.columns([1, 2])
            with c1:
                # Mostrar foto
                foto = f"Fotos-Alumnos/{mat}.jpg"
                if os.path.exists(foto): st.image(foto, width=300)
                else: st.info("📷 Foto pendiente")
            
            with c2:
                st.markdown(f"<p class='big-font'>{al['NOMBRE']} {al['PRIMER APELLIDO']}</p>", unsafe_allow_html=True)
                st.write(f"### Grupo: {al['GRUPO']}")
                
                # Aviso de entrada
                aviso = al.get('AVISO_ENTRADA', "")
                if pd.notna(aviso) and aviso != "":
                    st.markdown(f"<div class='aviso-box'>📢 AVISO: {aviso}</div>", unsafe_allow_html=True)
                
                # Estado del acceso
                hora_actual = datetime.now(zona_horaria).strftime('%H:%M:%S')
                st.markdown(f"<div class='status-box'>✅ ACCESO REGISTRADO<br>{hora_actual}</div>", unsafe_allow_html=True)
                
                # Botones de reporte rápido
                st.write("---")
                col_btn1, col_btn2 = st.columns(2)
                if col_btn1.button("⏰ RETARDO"):
                    st.toast("Retardo registrado") # Aquí iría la llamada al Webhook
                if col_btn2.button("🚫 REPORTE"):
                    st.toast("Reporte generado")
        else:
            st.error(f"Matrícula {mat} no encontrada.")

# --- MÓDULO 2: HISTORIAL (CONSULTA 360) ---
elif menu == "Historial Alumnos":
    st.title("🔍 Buscador de Expedientes")
    buscar_mat = st.text_input("Ingresar Matrícula").replace("'", "-").strip()
    
    if buscar_mat in df_alumnos.index:
        alumno = df_alumnos.loc[buscar_mat]
        st.header(f"Alumno: {alumno['NOMBRE']} {alumno['PRIMER APELLIDO']}")
        
        tab_acad, tab_incid = st.tabs(["📊 Datos Académicos", "📜 Historial de Conducta"])
        
        with tab_acad:
            if buscar_mat in df_academico.index:
                ac = df_academico.loc[buscar_mat]
                c1, c2, c3 = st.columns(3)
                c1.metric("Promedio", ac.get('PROMEDIO_GENERAL', 'N/A'))
                c2.metric("Adeudos", ac.get('MATERIAS_ADEUDADAS', '0'))
                c3.write(f"**Estado:** {ac.get('ESTADO_ACADEMICO', 'Regular')}")
            else:
                st.warning("No hay datos académicos vinculados.")
        
        with tab_incid:
            mis_incidencias = df_incidencias[df_incidencias['MATRICULA'] == buscar_mat]
            if not mis_incidencias.empty:
                st.table(mis_incidencias)
            else:
                st.success("Sin incidencias registradas.")

# --- MÓDULO 3: GESTIÓN (SERVICIOS ESCOLARES) ---
elif menu == "Gestión Administrativa":
    st.title("⚙️ Panel de Administración")
    st.write("Desde aquí puedes ir directamente a la base de datos para modificar avisos o usuarios.")
    st.link_button("Abrir Google Sheets Principal", f"https://docs.google.com/spreadsheets/d/{SHEET_ID}")

