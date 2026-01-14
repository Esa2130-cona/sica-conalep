import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import os
import pytz

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="SICA Conalep Cuautla", layout="wide")
zona_horaria = pytz.timezone('America/Mexico_City')

st.markdown("""
    <style>
    .stApp { background-color: #F8F9FA; color: #212529; }
    h1, h2, h3 { color: #006437 !important; }
    .big-font { font-size:35px !important; font-weight: bold; color: #006437; }
    .status-box { padding: 25px; border-radius: 20px; text-align: center; background-color: #FFFFFF; border: 3px solid #006437; color: #006437; box-shadow: 0px 4px 15px rgba(0,0,0,0.1); }
    .aviso-box { padding: 15px; background-color: #FFF3CD; color: #856404; border-radius: 12px; border-left: 8px solid #FFC107; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXIÓN Y LIMPIEZA DE DATOS ---
SHEET_ID = "11RZyoBo_MyQkGWfc21WCY_xPFZdKkwTG12YagiZf3yM"

@st.cache_data(ttl=5)
def cargar_limpio(gid):
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={gid}"
    try:
        # Leemos el archivo ignorando columnas vacías al inicio
        df = pd.read_csv(url)
        
        # ELIMINAR COLUMNAS VACÍAS (Unnamed)
        df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
        
        # LIMPIAR NOMBRES DE COLUMNAS
        df.columns = [str(c).strip().upper() for c in df.columns]
        
        # ASEGURAR QUE MATRICULA SEA TEXTO
        if 'MATRICULA' in df.columns:
            df['MATRICULA'] = df['MATRICULA'].astype(str).str.strip()
        
        return df
    except Exception as e:
        st.error(f"Error cargando pestaña {gid}: {e}")
        return pd.DataFrame()

# Carga de las 4 pestañas principales
df_alumnos = cargar_limpio(0)
df_academico = cargar_limpio(1114227031)
df_incidencias = cargar_limpio(569107936)
df_usuarios = cargar_limpio(1418859187)

# --- 3. LOGIN ---
if 'user_data' not in st.session_state:
    st.session_state.user_data = None

if st.session_state.user_data is None:
    st.title("🛡️ SICA - CONALEP CUAUTLA")
    u = st.text_input("Usuario")
    p = st.text_input("PIN", type="password")
    if st.button("INGRESAR"):
        if not df_usuarios.empty:
            # Buscamos usuario y pin
            match = df_usuarios[(df_usuarios['USUARIO'].astype(str).str.lower() == u.lower()) & 
                                (df_usuarios['PIN'].astype(str) == p)]
            if not match.empty:
                st.session_state.user_data = match.iloc[0].to_dict()
                st.rerun()
            else: st.error("Usuario o PIN incorrectos")
    st.stop()

# --- 4. INTERFAZ PRINCIPAL ---
user = st.session_state.user_data
st.sidebar.title(f"👤 {user.get('NOMBRE', 'Usuario')}")
if st.sidebar.button("Cerrar Sesión"):
    st.session_state.user_data = None
    st.rerun()

menu = st.sidebar.radio("MENÚ", ["Puerta de Entrada", "Historial Alumnos"])

# --- MODULO: PUERTA DE ENTRADA ---
if menu == "Puerta de Entrada":
    st.title("🚀 Registro de Acceso")
    
    if 'id_leido' not in st.session_state: st.session_state.id_leido = ""

    def al_escanear():
        raw = st.session_state.input_lector
        # CORREGIR COMILLA POR GUION
        st.session_state.id_leido = raw.replace("'", "-").strip()
        st.session_state.input_lector = ""

    st.text_input("👇 ESCANEE AQUÍ", key="input_lector", on_change=al_escanear)
    
    mat = st.session_state.id_leido
    
    if mat:
        # Buscamos al alumno en el DataFrame
        res = df_alumnos[df_alumnos['MATRICULA'] == mat]
        
        if not res.empty:
            al = res.iloc[0]
            c1, c2 = st.columns([1, 2])
            with c1:
                # Mostrar foto o imagen por defecto
                foto = f"Fotos-Alumnos/{mat}.jpg"
                if os.path.exists(foto): st.image(foto, width=300)
                else: st.info("📷 Sin foto")
            with c2:
                st.markdown(f"<p class='big-font'>{al.get('NOMBRE','')} {al.get('PRIMER APELLIDO','')}</p>", unsafe_allow_html=True)
                st.write(f"### Grupo: {al.get('GRUPO', 'S/G')}")
                
                aviso = al.get('AVISO_ENTRADA', "")
                if pd.notna(aviso) and str(aviso).strip() != "":
                    st.markdown(f"<div class='aviso-box'>📢 AVISO: {aviso}</div>", unsafe_allow_html=True)
                
                h = datetime.now(zona_horaria).strftime('%H:%M:%S')
                st.markdown(f"<div class='status-box'>✅ ACCESO REGISTRADO<br>{h}</div>", unsafe_allow_html=True)
        else:
            st.error(f"❌ Matrícula {mat} no encontrada. Revise la pestaña ALUMNOS.")

# --- MODULO: HISTORIAL ---
elif menu == "Historial Alumnos":
    st.title("🔍 Consulta de Expedientes")
    m_busc = st.text_input("Matrícula").replace("'", "-").strip()
    if m_busc:
        busc_res = df_alumnos[df_alumnos['MATRICULA'] == m_busc]
        if not busc_res.empty:
            al_h = busc_res.iloc[0]
            st.header(f"Alumno: {al_h.get('NOMBRE','')} {al_h.get('PRIMER APELLIDO','')}")
            
            t1, t2 = st.tabs(["📊 Académico", "📜 Incidencias"])
            with t1:
                ac_h = df_academico[df_academico['MATRICULA'] == m_busc]
                st.dataframe(ac_h, hide_index=True)
            with t2:
                in_h = df_incidencias[df_incidencias['MATRICULA'] == m_busc]
                st.table(in_h)
        else: st.error("Alumno no encontrado.")
