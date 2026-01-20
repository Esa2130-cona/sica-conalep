# ================= IMPORTS =================
import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime
import pytz
import time
import plotly.express as px
from fpdf import FPDF

# ================= CONFIGURACIÓN =================
st.set_page_config(page_title="SICA CONALEP CUAUTLA", layout="wide")
zona = pytz.timezone("America/Mexico_City")

@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

# ================= FUNCIONES BASE =================
def normalizar_matricula(mat):
    if not mat:
        return ""
    return mat.strip().upper().replace('"', '-').replace("'", '-')

def enviar(tabla, datos):
    datos_db = {k.lower(): v for k, v in datos.items()}
    return supabase.table(tabla).insert(datos_db).execute()

# ================= ESTILOS =================
st.markdown("""
<style>
.stApp { background-color: #050a10; color: #f0f6fc; }
div[data-baseweb="input"], div[data-baseweb="textarea"] {
    background-color: #e0e6ed !important;
    border-radius: 8px !important;
}
input, textarea { color: #000000 !important; font-weight: 500 !important; }
.stWidgetLabel p { color: #ffffff !important; font-weight: 600 !important; }
.stButton>button { background-color: #1e8449 !important; color: white !important; font-weight: 700 !important; }
</style>
""", unsafe_allow_html=True)

# ================= LOGIN =================
if "user" not in st.session_state:
    st.session_state.user = None

if not st.session_state.user:
    st.markdown("<h1 style='text-align:center;'>🔐 SICA CONALEP CUAUTLA</h1>", unsafe_allow_html=True)
    u = st.text_input("Usuario").strip()
    p = st.text_input("PIN", type="password").strip()
    if st.button("Ingresar"):
        q = supabase.table("usuarios").select("*").eq("usuario", u).eq("pin", p).execute()
        if q.data:
            st.session_state.user = q.data[0]
            st.rerun()
        else:
            st.error("Credenciales incorrectas")
    st.stop()

user = st.session_state.user
rol = str(user.get("rol", "")).upper()
nombre_usuario = user.get("usuario", "Usuario")

# ================= SIDEBAR =================
st.sidebar.markdown(f"""
<div style='background:#161b22;padding:15px;border-radius:10px;margin-bottom:20px;'>
<p style='font-size:11px;'>BIENVENIDO(A)</p>
<h3>{nombre_usuario}</h3>
<span style='background:#1e8449;padding:4px;border-radius:5px;font-size:11px;'>ROL: {rol}</span>
</div>
""", unsafe_allow_html=True)

if rol == "KIOSKO":
    opciones = ["Puerta de Entrada"]
elif rol == "DIRECTOR":
    opciones = ["Dashboard", "Expediente Digital"]
elif rol == "PREFECTO":
    opciones = ["Reportes", "Historial", "Avisos", "Expediente Digital"]
elif rol == "GENERAL":
    opciones = ["Reportes", "Avisos", "Servicios y Técnica", "Expediente Digital"]
elif rol == "ADMIN":
    opciones = ["Puerta de Entrada", "Dashboard", "Reportes", "Historial", "Avisos", "Servicios y Técnica", "Expediente Digital"]
else:
    opciones = ["Puerta de Entrada"]

menu = st.sidebar.radio("📋 MENÚ PRINCIPAL", opciones)

if st.sidebar.button("Cerrar Sesión"):
    st.session_state.user = None
    st.rerun()

# ======================================================
# ===================== MÓDULOS ========================
# ======================================================

def puerta_entrada():
    st.markdown("<h2 style='text-align:center;'>📡 SISTEMA DE ACCESO CONALEP</h2>", unsafe_allow_html=True)

    if "resultado" not in st.session_state:
        st.session_state.resultado = None

    def procesar_scan():
        mat = normalizar_matricula(st.session_state.scan_input)
        st.session_state.scan_input = ""
        if not mat:
            return

        al = supabase.table("alumnos").select("*").eq("matricula", mat).execute()
        av = supabase.table("avisos").select("mensaje, prioridad").eq("matricula", mat).eq("activo", True).execute()

        if not al.data:
            st.session_state.resultado = {"tipo": "error", "mensaje": "NO REGISTRADO"}
            return

        alumno = al.data[0]
        aviso = av.data[0] if av.data else None

        enviar("entradas", {
            "fecha": datetime.now(zona).strftime("%Y-%m-%d"),
            "hora": datetime.now(zona).strftime("%H:%M:%S"),
            "matricula": mat,
            "nombre": alumno["nombre"],
            "grupo": alumno["grupo"],
            "registro_por": nombre_usuario
        })

        st.session_state.resultado = {
            "tipo": "ok",
            "nombre": alumno["nombre"],
            "grupo": alumno["grupo"],
            "aviso": aviso
        }

    st.text_input("ESCANEE AQUÍ", key="scan_input", on_change=procesar_scan)

    if st.session_state.resultado:
        r = st.session_state.resultado
        if r["tipo"] == "ok":
            st.success(f"✅ ACCESO PERMITIDO: {r['nombre']} ({r['grupo']})")
            if r["aviso"]:
                st.warning(f"⚠️ {r['aviso']['prioridad']}: {r['aviso']['mensaje']}")
        else:
            st.error(r["mensaje"])

        time.sleep(3)
        st.session_state.resultado = None
        st.rerun()

def dashboard():
    st.title("🏛️ Panel de Control Directivo - CONALEP")

    rep = supabase.table("reportes").select("*").execute()
    ent = supabase.table("entradas").select("*").execute()
    al = supabase.table("alumnos").select("matricula,grupo").execute()

    if not rep.data:
        st.info("Sin datos suficientes")
        return

    df_rep = pd.DataFrame(rep.data)
    df_ent = pd.DataFrame(ent.data)
    df_al = pd.DataFrame(al.data)

    df_rep.columns = [c.lower() for c in df_rep.columns]
    df_al.columns = [c.lower() for c in df_al.columns]

    if "grupo" in df_rep.columns:
        df_rep.drop(columns=["grupo"], inplace=True)

    df_rep = df_rep.merge(df_al, on="matricula", how="left")
    df_rep["grupo"] = df_rep["grupo"].fillna("SIN GRUPO")

    c1, c2, c3 = st.columns(3)
    c1.metric("Asistencias", len(df_ent))
    c2.metric("Incidencias", len(df_rep))
    c3.metric("Casos Graves", len(df_rep[df_rep["nivel"].str.upper()=="REPORTE"]))

    col1, col2 = st.columns(2)
    with col1:
        grp = df_rep["grupo"].value_counts().reset_index()
        grp.columns = ["grupo","total"]
        st.plotly_chart(px.bar(grp, x="total", y="grupo", orientation="h"), use_container_width=True)

    with col2:
        df_ent["fecha"] = pd.to_datetime(df_ent["fecha"])
        dia = df_ent.groupby("fecha").size().reset_index(name="total")
        st.plotly_chart(px.line(dia, x="fecha", y="total", markers=True), use_container_width=True)

def reportes():
    st.title("🚨 Gestión de Reportes")
    mat = st.text_input("Matrícula").upper()
    if not mat:
        return

    al = supabase.table("alumnos").select("*").eq("matricula", mat).execute()
    if not al.data:
        st.error("Matrícula no encontrada")
        return

    alumno = al.data[0]
    st.info(alumno["nombre"])

    tipo = st.selectbox("Tipo", ["Uniforme","Conducta","Retardo","Celular","Otro"])
    desc = st.text_area("Descripción")

    if st.button("Guardar"):
        enviar("reportes", {
            "fecha": datetime.now(zona).strftime("%Y-%m-%d"),
            "matricula": mat,
            "nombre": alumno["nombre"],
            "nivel": "LLAMADA",
            "tipo": tipo,
            "descripcion": desc,
            "registrado_por": nombre_usuario
        })
        st.success("Reporte guardado")

def historial():
    st.title("📊 Historial")
    mat = st.text_input("Matrícula").upper()
    if not mat:
        return

    ent = supabase.table("entradas").select("*").eq("matricula", mat).execute()
    rep = supabase.table("reportes").select("*").eq("matricula", mat).execute()

    st.subheader("Entradas")
    st.dataframe(pd.DataFrame(ent.data))

    st.subheader("Reportes")
    st.dataframe(pd.DataFrame(rep.data))

def avisos():
    st.title("📢 Avisos")
    mat = st.text_input("Matrícula").upper()
    msg = st.text_area("Mensaje")
    pr = st.selectbox("Prioridad", ["BAJA","MEDIA","ALTA"])

    if st.button("Publicar"):
        supabase.table("avisos").insert({
            "matricula": mat,
            "mensaje": msg,
            "prioridad": pr,
            "activo": True
        }).execute()
        st.success("Aviso publicado")

def servicios():
    st.title("⚙️ Servicios y Técnica")
    rep = supabase.table("reportes").select("*").execute()
    st.dataframe(pd.DataFrame(rep.data))

def expediente():
    st.title("🗂️ Expediente Digital")
    mat = st.text_input("Matrícula").upper()
    if not mat:
        return

    rep = supabase.table("reportes").select("*").eq("matricula", mat).execute()
    st.dataframe(pd.DataFrame(rep.data))

# ================= NAVEGACIÓN ÚNICA =================
if menu == "Puerta de Entrada":
    puerta_entrada()
elif menu == "Dashboard":
    dashboard()
elif menu == "Reportes":
    reportes()
elif menu == "Historial":
    historial()
elif menu == "Avisos":
    avisos()
elif menu == "Servicios y Técnica":
    servicios()
elif menu == "Expediente Digital":
    expediente()













































































































