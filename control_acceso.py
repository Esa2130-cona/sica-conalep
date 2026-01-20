import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime
import pytz
import time

# ================= CONFIGURACIÓN INICIAL =================
st.set_page_config(page_title="SICA CONALEP CUAUTLA", layout="wide")
zona = pytz.timezone("America/Mexico_City")

# --- CONEXIÓN A SUPABASE ---
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

# --- FUNCIONES GLOBALES ---
def normalizar_matricula(mat):
    if not mat: return ""
    return mat.strip().upper().replace('"', '-').replace("'", '-')

def enviar(tabla, datos):
    datos_db = {k.lower(): v for k, v in datos.items()}
    return supabase.table(tabla).insert(datos_db).execute()

# ================= ESTILOS CSS =================
st.markdown("""
<style>
    .stApp { background: #0d1117; }
    .kiosko-wrapper { display: flex; flex-direction: column; align-items: center; justify-content: center; margin-top: -20px; }
    .scan-card { background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.1); backdrop-filter: blur(10px); padding: 30px; border-radius: 24px; text-align: center; width: 100%; max-width: 500px; margin-bottom: 20px; }
    .scan-text { color: #00e676; font-size: 24px; font-weight: 800; text-transform: uppercase; }
    .res-card { width: 100%; max-width: 600px; border-radius: 30px; padding: 40px; text-align: center; animation: slideUp 0.4s ease-out; }
    .res-ok { background: linear-gradient(145deg, #1b5e20, #2e7d32); border: 2px solid #00e676; }
    .res-error { background: linear-gradient(145deg, #b71c1c, #d32f2f); border: 2px solid #ff5252; }
    .student-name { font-size: 50px; font-weight: 900; color: white; margin: 15px 0; text-transform: uppercase; }
    div[data-baseweb="input"] { background: transparent !important; border: none !important; }
    input { text-align: center !important; font-size: 24px !important; color: white !important; border-bottom: 2px solid #00e676 !important; }
    @keyframes slideUp { from { transform: translateY(30px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
</style>
""", unsafe_allow_html=True)

# ================= SISTEMA DE LOGIN =================
if "user" not in st.session_state:
    st.session_state.user = None

if not st.session_state.user:
    st.markdown("<h1 style='color:white; text-align:center;'>🔐 SICA CONALEP CUAUTLA</h1>", unsafe_allow_html=True)
    with st.container():
        u = st.text_input("Usuario")
        p = st.text_input("PIN", type="password")
        if st.button("Ingresar"):
            query = supabase.table("usuarios").select("*").eq("usuario", u).eq("pin", p).execute()
            if query.data:
                st.session_state.user = query.data[0]
                st.rerun()
            else:
                st.error("Credenciales incorrectas")
    st.stop()

user = st.session_state.user
rol = user.get("rol", "").upper()

# ================= MENÚ PRINCIPAL =================
opciones = ["Puerta de Entrada", "Reportes", "Historial", "Bitácora Maestros"]
if rol == "KIOSKO": opciones = ["Puerta de Entrada"]
menu = st.sidebar.radio("📋 MENÚ", opciones)

# ================= MÓDULO: PUERTA DE ENTRADA =================
if menu == "Puerta de Entrada":
    st.markdown("<div class='kiosko-wrapper'>", unsafe_allow_html=True)
    st.markdown("<div class='scan-card'><div class='scan-text'>📡 SISTEMA DE ACCESO</div></div>", unsafe_allow_html=True)

    if "resultado" not in st.session_state: st.session_state.resultado = None

    def procesar_scan():
        mat = normalizar_matricula(st.session_state.scan_input)
        st.session_state.scan_input = ""
        if not mat: return
        
        # Buscar Alumno y Avisos al mismo tiempo
        al_query = supabase.table("alumnos").select("*").eq("MATRICULA", mat).execute()
        av_query = supabase.table("avisos").select("mensaje").eq("matricula", mat).eq("activo", True).execute()

        if not al_query.data:
            st.session_state.resultado = {"tipo": "error", "mensaje": "NO REGISTRADO"}
        else:
            al = al_query.data[0]
            aviso = av_query.data[0]["mensaje"] if av_query.data else None
            
            enviar("entradas", {
                "FECHA": datetime.now(zona).strftime("%Y-%m-%d"),
                "HORA": datetime.now(zona).strftime("%H:%M:%S"),
                "MATRICULA": al["MATRICULA"],
                "NOMBRE": al["NOMBRE"],
                "GRUPO": al.get("GRUPO", "N/A"),
                "REGISTRO_POR": user["usuario"]
            })
            st.session_state.resultado = {"tipo": "ok", "alumno": al, "aviso": aviso}

    st.text_input("", key="scan_input", on_change=procesar_scan, placeholder="ESCANEE AQUÍ")

    if st.session_state.resultado:
        res = st.session_state.resultado
        if res["tipo"] == "ok":
            st.markdown(f"""
                <div class='res-card res-ok'>
                    <div style='font-size:30px; color:#00e676;'>✅ ACCESO PERMITIDO</div>
                    <div class='student-name'>{res['alumno']['NOMBRE']}</div>
                    <div style='font-size:25px; color:white;'>GRUPO: {res['alumno'].get('GRUPO','N/A')}</div>
                </div>
            """, unsafe_allow_html=True)
            if res["aviso"]: st.warning(f"⚠️ AVISO: {res['aviso']}")
        else:
            st.markdown(f"<div class='res-card res-error'><h1>❌ {res['mensaje']}</h1></div>", unsafe_allow_html=True)
        
        time.sleep(2.0)
        st.session_state.resultado = None
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

# ================= MÓDULO: REPORTES =================
elif menu == "Reportes":
    st.title("🚨 Gestión de Reportes")
    mat = st.text_input("Ingrese Matrícula del Alumno").strip()
    
    if mat:
        al_query = supabase.table("alumnos").select("*").eq("MATRICULA", mat).execute()
        if al_query.data:
            al = al_query.data[0]
            st.write(f"**Alumno:** {al['NOMBRE']} | **Grupo:** {al.get('GRUPO','N/A')}")
            
            # Lógica de niveles automática
            rep_count = supabase.table("reportes").select("id", count="exact").eq("matricula", mat).execute()
            count = rep_count.count if rep_count.count else 0
            niveles = ["LLAMADA 1", "LLAMADA 2", "LLAMADA 3", "REPORTE"]
            nivel_actual = niveles[min(count, 3)]
            
            st.info(f"Nivel de incidencia sugerido: {nivel_actual}")
            
            tipo = st.selectbox("Tipo", ["Uniforme", "Conducta", "Retardo", "Falta"])
            desc = st.text_area("Descripción de la incidencia")
            foto = st.camera_input("Capturar Evidencia (Opcional)")
            
            if st.button("Guardar Reporte"):
                enviar("reportes", {
                    "FECHA": datetime.now(zona).strftime("%Y-%m-%d"),
                    "MATRICULA": mat,
                    "NOMBRE": al["NOMBRE"],
                    "GRUPO": al.get("GRUPO","N/A"),
                    "NIVEL": nivel_actual,
                    "TIPO": tipo,
                    "DESCRIPCION": desc,
                    "REGISTRADO_POR": user["usuario"]
                })
                st.success("Reporte guardado con éxito.")
                time.sleep(1)
                st.rerun()
        else:
            st.error("Alumno no encontrado.")

# ================= MÓDULO: BITÁCORA MAESTROS =================
elif menu == "Bitácora Maestros":
    st.title("📖 Bitácora de Laboratorios")
    with st.form("bitacora"):
        aula = st.selectbox("Aula", ["Info 1", "Info 2", "Redes"])
        tema = st.text_input("Tema de la Práctica")
        grupo_clase = st.text_input("Grupo")
        estado = st.radio("Estado de Equipos", ["Todo OK", "Fallas Reportadas"], horizontal=True)
        obs = st.text_area("Observaciones")
        if st.form_submit_button("Registrar Clase"):
            enviar("bitacora_maestros", {
                "FECHA": datetime.now(zona).strftime("%Y-%m-%d"),
                "MAESTRO": user["usuario"],
                "AULA": aula,
                "TEMA": tema,
                "GRUPO": grupo_clase,
                "ESTADO_EQUIPOS": estado,
                "INCIDENCIAS": obs
            })
            st.success("Registro completado.")
























































































