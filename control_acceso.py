import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime
import pytz
import time
import plotly.express as px
from fpdf import FPDF

# ================= CONFIGURACIÓN INICIAL =================
st.set_page_config(page_title="SICA CONALEP CUAUTLA", layout="wide")
zona = pytz.timezone("America/Mexico_City")

@st.cache_resource
def init_connection():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception as e:
        st.error("Error en Secrets: Verifica URL y KEY")
        st.stop()

supabase = init_connection()

def normalizar_matricula(mat):
    if not mat: return ""
    return mat.strip().upper().replace('"', '-').replace("'", '-')

def enviar(tabla, datos):
    datos_db = {k.lower(): v for k, v in datos.items()}
    return supabase.table(tabla).insert(datos_db).execute()

# ================= ESTILOS CSS =================
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
    .scan-card { background: rgba(255, 255, 255, 0.03); border-radius: 20px; padding: 30px; text-align: center; border-top: 6px solid #1e8449; }
    .student-name { font-size: 42px !important; font-weight: 900 !important; color: white !important; }
</style>
""", unsafe_allow_html=True)

# ================= 1. SISTEMA DE LOGIN =================
if "user" not in st.session_state:
    st.session_state.user = None

if not st.session_state.user:
    st.markdown("<h1 style='color:white; text-align:center;'>🔐 SICA CONALEP CUAUTLA</h1>", unsafe_allow_html=True)
    with st.container():
        u = st.text_input("Usuario").strip()
        p = st.text_input("PIN", type="password").strip()
        if st.button("Ingresar"):
            try:
                query = supabase.table("usuarios").select("*").filter("usuario", "eq", u).filter("pin", "eq", p).execute()
                if query.data:
                    st.session_state.user = query.data[0]
                    st.rerun()
                else: st.error("Credenciales incorrectas")
            except Exception as e: st.error(f"Error de base de datos: {e}")
    st.stop()

# ================= 2. CONFIGURACIÓN DE USUARIO =================
user = st.session_state.user
rol = str(user.get("rol", user.get("ROL", ""))).upper().strip()
nombre_usuario = user.get("usuario", "Usuario")

st.sidebar.markdown(f"""
<div style='background-color: #161b22; padding: 15px; border-radius: 10px; border: 1px solid #30363d; margin-bottom: 20px;'>
    <p style='margin: 0; color: #8b949e; font-size: 11px;'>BIENVENIDO(A)</p>
    <h3 style='margin: 0; color: #ffffff; font-size: 18px;'>{nombre_usuario}</h3>
    <span style='background-color: #1e8449; color: white; padding: 2px 8px; border-radius: 5px; font-size: 10px; font-weight: bold;'>ROL: {rol}</span>
</div>
""", unsafe_allow_html=True)

# Lógica de Menú
if rol == "KIOSKO": opciones = ["Puerta de Entrada"]
elif rol == "DIRECTOR": opciones = ["Dashboard", "Expediente Digital"]
elif rol == "PREFECTO": opciones = ["Reportes", "Historial", "Avisos", "Expediente Digital"]
elif rol == "GENERAL": opciones = ["Reportes", "Avisos", "Servicios y Técnica", "Expediente Digital"]
elif rol == "ADMIN": opciones = ["Puerta de Entrada", "Reportes", "Historial", "Avisos", "Bitácora Maestros", "Dashboard", "Servicios y Técnica", "Expediente Digital"]
else: opciones = ["Puerta de Entrada"]

menu = st.sidebar.radio("📋 MENÚ PRINCIPAL", opciones)
if st.sidebar.button("Cerrar Sesión"):
    st.session_state.user = None
    st.rerun()

# ================= 3. NAVEGACIÓN DE MÓDULOS (UNIFICADA) =================

if menu == "Dashboard":
    st.title("🏛️ Panel de Control Directivo")
    try:
        res_rep = supabase.table("reportes").select("*").execute()
        res_ent = supabase.table("entradas").select("*").execute()
        res_al = supabase.table("alumnos").select("matricula, grupo").execute()

        if res_rep.data and res_ent.data:
            df_rep, df_ent, df_al = pd.DataFrame(res_rep.data), pd.DataFrame(res_ent.data), pd.DataFrame(res_al.data)
            df_rep.columns = [c.lower().strip() for c in df_rep.columns]
            df_al.columns = [c.lower().strip() for c in df_al.columns]
            df_final = df_rep.merge(df_al[['matricula', 'grupo']], on="matricula", how="left")
            df_final['grupo'] = df_final['grupo'].fillna("SIN GRUPO")

            c1, c2, c3 = st.columns(3)
            c1.metric("Asistencias", len(df_ent))
            c2.metric("Incidencias", len(df_rep))
            c3.metric("Casos Graves", len(df_final[df_final['nivel'].astype(str).str.upper() == 'REPORTE']) if 'nivel' in df_final.columns else 0)

            st.markdown("### 📊 Análisis Visual")
            col_a, col_b = st.columns(2)
            with col_a:
                fig_grupos = px.bar(df_final['grupo'].value_counts().reset_index(), x='count', y='grupo', orientation='h', title="Reportes por Grupo", color_discrete_sequence=['#ff4b4b'])
                st.plotly_chart(fig_grupos, use_container_width=True)
            with col_b:
                df_ent['fecha'] = pd.to_datetime(df_ent['fecha'])
                asist_diaria = df_ent.groupby('fecha').size().reset_index(name='total')
                fig_asist = px.line(asist_diaria, x='fecha', y='total', title="Tendencia de Asistencia", markers=True)
                st.plotly_chart(fig_asist, use_container_width=True)
    except Exception as e: st.error(f"Error en Dashboard: {e}")

elif menu == "Puerta de Entrada":
    st.markdown("<div class='scan-card'><div class='scan-text'>📡 SISTEMA DE ACCESO CONALEP CUAUTLA</div></div>", unsafe_allow_html=True)
    if "resultado" not in st.session_state: st.session_state.resultado = None

    def procesar_scan():
        mat = normalizar_matricula(st.session_state.scan_input)
        st.session_state.scan_input = ""
        if not mat: return
        try:
            al_query = supabase.table("alumnos").select("*").filter("matricula", "eq", mat).execute()
            av_query = supabase.table("avisos").select("mensaje, prioridad").filter("matricula", "eq", mat).filter("activo", "eq", True).execute()
            if not al_query.data:
                st.session_state.resultado = {"tipo": "error", "mensaje": "NO REGISTRADO"}
            else:
                al = al_query.data[0]
                aviso_data = av_query.data[0] if av_query.data else None
                enviar("entradas", {
                    "fecha": datetime.now(zona).strftime("%Y-%m-%d"), "hora": datetime.now(zona).strftime("%H:%M:%S"),
                    "matricula": mat, "nombre": al.get("nombre"), "grupo": al.get("grupo"),
                    "registro_por": user.get("usuario", "Sistema")
                })
                st.session_state.resultado = {"tipo": "ok", "nombre": al.get("nombre"), "grupo": al.get("grupo"), "aviso": aviso_data}
        except Exception as e: st.session_state.resultado = {"tipo": "error", "mensaje": str(e)}

    st.text_input("", key="scan_input", on_change=procesar_scan, placeholder="ESCANEE AQUÍ", autocomplete="off")

    if st.session_state.resultado:
        res = st.session_state.resultado
        if res["tipo"] == "ok":
            st.markdown(f"<div class='res-card res-ok'><div style='font-size:30px; color:#00e676;'>✅ ACCESO PERMITIDO</div><div class='student-name'>{res['nombre']}</div><div style='font-size:25px; color:white;'>GRUPO: {res['grupo']}</div></div>", unsafe_allow_html=True)
            if res["aviso"]:
                prio = str(res["aviso"].get("prioridad", "BAJA")).upper()
                colores = {"ALTA": "#e74c3c", "MEDIA": "#f39c12", "BAJA": "#3498db"}
                st.markdown(f"<div style='background-color: {colores.get(prio)}; padding: 20px; border-radius: 15px; color: white; text-align: center; margin-top: 15px;'>⚠️ AVISO {prio}: {res['aviso']['mensaje']}</div>", unsafe_allow_html=True)
        else: st.error(res["mensaje"])
        time.sleep(3.0); st.session_state.resultado = None; st.rerun()

elif menu == "Reportes":
    st.title("🚨 Gestión de Reportes")
    if "form_reset_count" not in st.session_state: st.session_state.form_reset_count = 0
    suffix = f"_{st.session_state.form_reset_count}"
    
    mat_rep = st.text_input("Matrícula del Alumno", key=f"mat{suffix}").strip().upper()
    if mat_rep:
        al_res = supabase.table("alumnos").select("*").eq("matricula", mat_rep).execute()
        if al_res.data:
            al = al_res.data[0]
            st.info(f"Alumno: {al.get('nombre')}")
            tipo = st.selectbox("Falta", ["Uniforme", "Conducta", "Retardo", "Celular", "Otro"], key=f"tipo{suffix}")
            desc = st.text_area("Descripción", key=f"desc{suffix}")
            if st.button("💾 Guardar Registro"):
                enviar("reportes", {
                    "fecha": datetime.now(zona).strftime("%Y-%m-%d"), "matricula": mat_rep,
                    "nombre": al.get("nombre"), "tipo": tipo, "descripcion": desc,
                    "registrado_por": user.get("usuario")
                })
                st.success("✅ Guardado"); time.sleep(1); st.session_state.form_reset_count += 1; st.rerun()
        else: st.error("No encontrado")

elif menu == "Historial":
    st.title("📊 Historial de Alumno")
    mat_h = st.text_input("Matrícula a consultar").strip().upper()
    if mat_h:
        res_ent = supabase.table("entradas").select("*").eq("matricula", mat_h).order("fecha", desc=True).execute()
        st.subheader("Entradas")
        st.dataframe(pd.DataFrame(res_ent.data), use_container_width=True)

elif menu == "Avisos":
    st.title("📢 Gestión de Avisos")
    mat_av = st.text_input("Matrícula").strip().upper()
    if mat_av:
        msg = st.text_area("Mensaje")
        prio = st.selectbox("Prioridad", ["BAJA", "MEDIA", "ALTA"])
        if st.button("Publicar"):
            supabase.table("avisos").insert({"matricula": mat_av, "mensaje": msg, "prioridad": prio, "activo": True}).execute()
            st.success("Aviso Publicado")

elif menu == "Servicios y Técnica":
    st.title("⚙️ Servicios y Técnica")
    res_al = supabase.table("alumnos").select("*").execute()
    st.dataframe(pd.DataFrame(res_al.data), use_container_width=True)

elif menu == "Expediente Digital":
    st.title("🗂️ Expediente Digital")
    mat_exp = st.text_input("Ingrese Matrícula").strip().upper()
    if mat_exp:
        al_res = supabase.table("alumnos").select("*").eq("matricula", mat_exp).execute()
        if al_res.data:
            al = al_res.data[0]
            st.subheader(f"Expediente de {al.get('nombre')}")
            # Aquí puedes agregar el resto de la lógica del expediente y el PDF

elif menu == "Bitácora Maestros":
    st.title("📖 Bitácora de Maestros")
    st.info("Módulo en desarrollo...")






















































































































