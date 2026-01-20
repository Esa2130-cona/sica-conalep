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
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception as e:
        st.error("Error en Secrets: Verifica SUPABASE_URL y SUPABASE_KEY")
        st.stop()

supabase = init_connection()

# --- FUNCIONES GLOBALES ---
def normalizar_matricula(mat):
    if not mat: return ""
    return mat.strip().upper().replace('"', '-').replace("'", '-')

def enviar(tabla, datos):
    # Forzamos nombres de columnas en minúsculas para coincidir con Supabase
    datos_db = {k.lower(): v for k, v in datos.items()}
    return supabase.table(tabla).insert(datos_db).execute()
# ================= ESTILOS CSS REFINADOS (TEXTO NEGRO) =================
st.markdown("""
<style>
    /* 1. Fondo general de la App */
    .stApp { 
        background-color: #050a10; 
        color: #f0f6fc;
    }

    /* 2. CAJAS DE TEXTO CON FONDO CLARO Y TEXTO NEGRO */
    div[data-baseweb="input"], div[data-baseweb="textarea"], div[data-baseweb="select"] {
        background-color: #e0e6ed !important; /* Fondo gris claro/blanco */
        border: 2px solid #30363d !important;
        border-radius: 8px !important;
    }
    
    div[data-baseweb="input"]:focus-within {
        border-color: #1e8449 !important; /* Verde Conalep al seleccionar */
        background-color: #ffffff !important; /* Se vuelve blanco puro al escribir */
    }

    /* 3. COLOR DEL TEXTO EN NEGRO (Lo que tú pediste) */
    input, textarea {
        color: #000000 !important; /* Negro puro */
        -webkit-text-fill-color: #000000 !important; /* Forzar en móviles */
        font-weight: 500 !important;
    }

    /* 4. ETIQUETAS (Labels) - Se mantienen blancas para el fondo oscuro de la app */
    .stWidgetLabel p {
        color: #ffffff !important;
        font-weight: 600 !important;
        font-size: 16px !important;
    }

    /* 5. BOTONES INSTITUCIONALES */
    .stButton>button {
        background-color: #1e8449 !important;
        color: white !important;
        border-radius: 8px !important;
        font-weight: 700 !important;
        width: 100% !important;
        border: none !important;
    }
    
    .stButton>button:hover {
        background-color: #145a32 !important;
        box-shadow: 0 4px 12px rgba(30, 132, 73, 0.4) !important;
    }

    /* 6. DISEÑO DEL KIOSKO (SCANNER) */
    .scan-card {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 20px;
        padding: 30px;
        text-align: center;
        border-top: 6px solid #1e8449;
    }
    
    .student-name {
        font-size: 42px !important;
        font-weight: 900 !important;
        color: white !important;
    }
</style>
""", unsafe_allow_html=True)

# ================= SISTEMA DE LOGIN =================
if "user" not in st.session_state:
    st.session_state.user = None

if not st.session_state.user:
    st.markdown("<h1 style='color:white; text-align:center;'>🔐 SICA CONALEP CUAUTLA</h1>", unsafe_allow_html=True)
    with st.container():
        u = st.text_input("Usuario").strip()
        p = st.text_input("PIN", type="password").strip()
        if st.button("Ingresar"):
            try:
                # Usamos filtros explícitos para evitar conflictos de nombres
                query = supabase.table("usuarios").select("*").filter("usuario", "eq", u).filter("pin", "eq", p).execute()
                if query.data:
                    st.session_state.user = query.data[0]
                    st.rerun()
                else:
                    st.error("Credenciales incorrectas")
            except Exception as e:
                st.error(f"Error de base de datos: {e}")
                st.info("Verifica que las columnas se llamen 'usuario' y 'pin' en minúsculas y el RLS esté desactivado.")
    st.stop()

user = st.session_state.user
rol = str(user.get("rol", user.get("ROL", ""))).upper()

# ================= MENÚ PRINCIPAL =================
opciones = ["Puerta de Entrada", "Reportes", "Historial", "Bitácora Maestros"]
if rol == "KIOSKO": opciones = ["Puerta de Entrada"]
menu = st.sidebar.radio("📋 MENÚ", opciones)

if st.sidebar.button("Cerrar Sesión"):
    st.session_state.user = None
    st.rerun()

# ================= MÓDULO: PUERTA DE ENTRADA =================
if menu == "Puerta de Entrada":
    st.markdown("<div class='kiosko-wrapper'>", unsafe_allow_html=True)
    st.markdown("<div class='scan-card'><div class='scan-text'>📡 SISTEMA DE ACCESO CONALEP PLANTEL CUAUTLA</div></div>", unsafe_allow_html=True)

    if "resultado" not in st.session_state: st.session_state.resultado = None

    def procesar_scan():
        mat = normalizar_matricula(st.session_state.scan_input)
        st.session_state.scan_input = ""
        if not mat: return
        
        try:
            # Busqueda flexible (soporta min/MAY en las columnas de la DB)
            al_query = supabase.table("alumnos").select("*").filter("matricula", "eq", mat).execute()
            av_query = supabase.table("avisos").select("mensaje").filter("matricula", "eq", mat).filter("activo", "eq", True).execute()

            if not al_query.data:
                st.session_state.resultado = {"tipo": "error", "mensaje": "NO REGISTRADO"}
            else:
                al = al_query.data[0]
                nombre = al.get("nombre", al.get("NOMBRE", "Estudiante"))
                grupo = al.get("grupo", al.get("GRUPO", "N/A"))
                
                aviso = av_query.data[0]["mensaje"] if av_query.data else None
                
                enviar("entradas", {
                    "fecha": datetime.now(zona).strftime("%Y-%m-%d"),
                    "hora": datetime.now(zona).strftime("%H:%M:%S"),
                    "matricula": mat,
                    "nombre": nombre,
                    "grupo": grupo,
                    "registro_por": user.get("usuario", "Sistema")
                })
                st.session_state.resultado = {"tipo": "ok", "nombre": nombre, "grupo": grupo, "aviso": aviso}
        except Exception as e:
            st.session_state.resultado = {"tipo": "error", "mensaje": f"Error DB: {str(e)[:40]}"}

    st.text_input("", key="scan_input", on_change=procesar_scan, placeholder="ESCANEE AQUÍ", autocomplete="off")

    if st.session_state.resultado:
        res = st.session_state.resultado
        if res["tipo"] == "ok":
            st.markdown(f"""
                <div class='res-card res-ok'>
                    <div style='font-size:30px; color:#00e676;'>✅ ACCESO PERMITIDO</div>
                    <div class='student-name'>{res['nombre']}</div>
                    <div style='font-size:25px; color:white;'>GRUPO: {res['grupo']}</div>
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
    
    # TRUCO PARA LIMPIAR TODO: Usamos un contador en el session_state
    if "form_reset_count" not in st.session_state:
        st.session_state.form_reset_count = 0
    
    # Función para reiniciar el formulario incrementando el contador
    def reiniciar_formulario():
        st.session_state.form_reset_count += 1
        st.rerun()

    # Cada widget tendrá una key única basada en el contador
    suffix = f"_{st.session_state.form_reset_count}"

    # 1. Entrada de Matrícula (con key dinámica)
    mat_rep = st.text_input("Ingrese Matrícula del Alumno", key=f"mat{suffix}").strip().upper()
    
    if mat_rep:
        try:
            al_res = supabase.table("alumnos").select("*").eq("matricula", mat_rep).execute()
            
            if al_res.data:
                al = al_res.data[0]
                nombre_alumno = al.get("nombre", al.get("NOMBRE", "Estudiante"))
                
                # Diseño Moderno: Tarjeta de Alumno
                st.markdown(f"""
                <div style='background:#161b22; padding:15px; border-radius:10px; border-left:5px solid #1e8449; margin-bottom:20px;'>
                    <h3 style='margin:0; color:white;'>Alumno: {nombre_alumno}</h3>
                </div>
                """, unsafe_allow_html=True)
                
                # Lógica 3+1
                historial_rep = supabase.table("reportes").select("id", count="exact").eq("matricula", mat_rep).execute()
                total_previo = historial_rep.count if historial_rep.count is not None else 0
                niveles = ["LLAMADA 1", "LLAMADA 2", "LLAMADA 3"]
                nivel_sugerido = niveles[total_previo] if total_previo < 3 else "REPORTE"

                st.info(f"Registro actual detectado: {nivel_sugerido}")

                # Widgets con key dinámica para evitar errores al limpiar
                tipo = st.selectbox("Tipo de falta", ["Uniforme", "Conducta", "Retardo", "Celular", "Otro"], key=f"tipo{suffix}")
                desc = st.text_area("Descripción de lo sucedido", key=f"desc{suffix}")
                foto = st.camera_input("📸 Tomar Evidencia (Opcional)", key=f"foto{suffix}")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button("💾 Guardar Registro", use_container_width=True):
                        url_foto = ""
                        
                        # Subida de foto
                        if foto is not None:
                            try:
                                nombre_archivo = f"evidencia_{mat_rep}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                                supabase.storage.from_("evidencias").upload(nombre_archivo, foto.getvalue())
                                url_foto = supabase.storage.from_("evidencias").get_public_url(nombre_archivo)
                            except Exception as e:
                                st.error(f"Error al subir foto: {e}")

                        # Envío a la base de datos
                        try:
                            # Reutilizamos tu función enviar (asegúrate que esté definida arriba)
                            enviar("reportes", {
                                "fecha": datetime.now(zona).strftime("%Y-%m-%d"),
                                "matricula": mat_rep,
                                "nombre": nombre_alumno,
                                "nivel": nivel_sugerido,
                                "tipo": tipo,
                                "descripcion": desc,
                                "foto_url": url_foto,
                                "registrado_por": user.get("usuario", "Prefecto")
                            })
                            
                            st.success("✅ Registro y evidencia guardados correctamente.")
                            time.sleep(1.2)
                            
                            # LA SOLUCIÓN DEFINITIVA:
                            reiniciar_formulario() # Esto limpia TODO sin errores
                            
                        except Exception as e:
                            st.error(f"Error al guardar: {e}")

                with col2:
                    if st.button("❌ Cancelar", use_container_width=True):
                        reiniciar_formulario()
            else:
                st.error("Matrícula no encontrada.")
        except Exception as e:
            st.error(f"Error en consulta: {e}")
# ================= MÓDULO: HISTORIAL (ENTRADAS Y REPORTES) =================
elif menu == "Historial":
    st.title("📊 Consulta Integral de Historial")
    
    mat_h = st.text_input("Ingrese Matrícula para consultar").strip().upper()
    
    if mat_h:
        try:
            al_res = supabase.table("alumnos").select("nombre, grupo").eq("matricula", mat_h).execute()
            
            if al_res.data:
                al = al_res.data[0]
                # Tarjeta de encabezado con estilo institucional
                st.markdown(f"""
                <div style='background:#161b22; padding:15px; border-radius:10px; border-left:5px solid #1e8449; margin-bottom:20px;'>
                    <h3 style='margin:0; color:white;'>Expediente: {al['nombre']}</h3>
                    <p style='margin:0; color:#8b949e;'>Grupo: {al['grupo']}</p>
                </div>
                """, unsafe_allow_html=True)
                
                tab1, tab2 = st.tabs(["🕒 Registro de Entradas", "🚨 Reportes e Incidencias"])
                
                with tab1:
                    res_ent = supabase.table("entradas").select("fecha, hora").eq("matricula", mat_h).order("fecha", desc=True).execute()
                    if res_ent.data:
                        df_ent = pd.DataFrame(res_ent.data)
                        df_ent.columns = ["FECHA", "HORA"]
                        st.dataframe(df_ent, use_container_width=True)
                    else:
                        st.info("Sin registros de asistencia.")

                with tab2:
                    res_rep = supabase.table("reportes").select("fecha, nivel, tipo, descripcion, registrado_por, foto_url").eq("matricula", mat_h).order("fecha", desc=True).execute()
                    
                    if res_rep.data:
                        for rep in res_rep.data:
                            with st.container():
                                # Ajustamos columnas para mejor visibilidad en móviles
                                col_texto, col_foto = st.columns([3, 1.2])
                                
                                with col_texto:
                                    st.markdown(f"**📅 {rep['fecha']} — {rep['nivel']}**")
                                    st.markdown(f"**Motivo:** {rep['tipo']}")
                                    st.write(f"{rep['descripcion']}")
                                    st.caption(f"Registrado por: {rep.get('registrado_por', 'Personal autorizado')}")
                                
                                with col_foto:
                                    url = rep.get("foto_url")
                                    if url and str(url).strip() != "":
                                        # Imagen interactiva con HTML
                                        st.markdown(f"""
                                            <a href="{url}" target="_blank">
                                                <img src="{url}" style="width:100%; border-radius:10px; border: 1px solid #30363d; margin-bottom: 5px;">
                                            </a>
                                        """, unsafe_allow_html=True)
                                        st.caption("🔍 Ampliar foto")
                                    else:
                                        st.info("Sin evidencia")
                                
                                st.divider()
                    else:
                        st.write("El alumno no cuenta con reportes registrados.")
            else:
                st.error("La matrícula no existe en la base de datos.")
                
        except Exception as e:
            st.error(f"Error de conexión: {e}")









































































































