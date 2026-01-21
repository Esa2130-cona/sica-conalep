import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime
import pytz
import time
import plotly.express as px
from fpdf import FPDF

# ================= ESTILOS DE FLASH =================
st.markdown("""
<style>
.flash-overlay {
    position: fixed;
    top: 0;
    left: 0;
    width: 100vw;
    height: 100vh;
    z-index: 9999;
    pointer-events: none;
}

@keyframes flashGreen {
    0% { background-color: rgba(0, 230, 118, 0.0); }
    40% { background-color: rgba(0, 230, 118, 0.35); }
    100% { background-color: rgba(0, 230, 118, 0.0); }
}

@keyframes flashAmber {
    0% { background-color: rgba(255, 152, 0, 0.0); }
    40% { background-color: rgba(255, 152, 0, 0.35); }
    100% { background-color: rgba(255, 152, 0, 0.0); }
}

@keyframes flashRed {
    0% { background-color: rgba(255, 23, 68, 0.0); }
    40% { background-color: rgba(255, 23, 68, 0.35); }
    100% { background-color: rgba(255, 23, 68, 0.0); }
}

.flash-ok {
    animation: flashGreen 0.6s ease-in-out;
}

.flash-warn {
    animation: flashAmber 0.6s ease-in-out;
}

.flash-error {
    animation: flashRed 0.6s ease-in-out;
}
</style>
""", unsafe_allow_html=True)


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

# ================= ESTILOS CSS (FONDO OSCURO / TEXTO NEGRO EN INPUTS) =================
st.markdown("""
<style>
    .stApp { background-color: #050a10; color: #f0f6fc; }
    div[data-baseweb="input"], div[data-baseweb="textarea"] {
        background-color: #e0e6ed !important;
        border-radius: 8px !important;
    }
    input, textarea { color: #000000 !important; font-weight: 500 !important; }
    .stWidgetLabel p { color: #ffffff !important; font-weight: 600 !important; font-size: 16px !important; }
    .stButton>button { background-color: #1e8449 !important; color: white !important; font-weight: 700 !important; }
    
    .scan-card {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 25px;
        padding: 50px;
        text-align: center;
        border: 2px solid rgba(30, 132, 73, 0.3);
        border-top: 10px solid #1e8449;
        box-shadow: 0 10px 30px rgba(0,0,0,0.5);
    }
    .scan-title {
        font-size: 55px !important;
        font-weight: 900 !important;
        color: #ffffff !important;
        text-shadow: 0 0 20px rgba(30, 132, 73, 0.6);
        line-height: 1.1;
    }
    .scan-subtitle {
        font-size: 24px !important;
        color: #1e8449 !important;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 2px;
    }
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

# ================= 2. CONFIGURACIÓN DE USUARIO LOGUEADO =================
user = st.session_state.user
rol = str(user.get("rol", user.get("ROL", ""))).upper().strip()
nombre_usuario = user.get("usuario", "Usuario")

# Sidebar con Bienvenida
st.sidebar.markdown(f"""
<div style='background-color: #161b22; padding: 15px; border-radius: 10px; border: 1px solid #30363d; margin-bottom: 20px;'>
    <p style='margin: 0; color: #8b949e; font-size: 11px;'>BIENVENIDO(A)</p>
    <h3 style='margin: 0; color: #ffffff; font-size: 18px;'>{nombre_usuario}</h3>
    <span style='background-color: #1e8449; color: white; padding: 2px 8px; border-radius: 5px; font-size: 10px; font-weight: bold;'>ROL: {rol}</span>
</div>
""", unsafe_allow_html=True)

# Lógica de Menú por Roles
if rol == "KIOSKO": opciones = ["Puerta de Entrada"]
elif rol == "DIRECTOR": opciones = ["Dashboard", "Expediente Digital"]
elif rol == "PREFECTO": opciones = ["Reportes", "Historial", "Avisos", "Expediente Digital"]
elif rol == "GENERAL": opciones = ["Reportes", "Avisos", "Servicios y Técnica", "Expediente Digital"]
elif rol == "ADMIN": opciones = ["Puerta de Entrada", "Reportes", "Historial", "Avisos", "Dashboard", "Servicios y Técnica", "Expediente Digital"]
else: opciones = ["Puerta de Entrada"]

menu = st.sidebar.radio("📋 MENÚ PRINCIPAL", opciones)
if st.sidebar.button("Cerrar Sesión"):
    st.session_state.user = None
    st.rerun()

# ================= MÓDULO: PUERTA DE ENTRADA =================
elif menu == "Puerta de Entrada":

    st.markdown("""
        <div class='scan-card'>
            <div class='scan-subtitle'>SICA</div>
            <div class='scan-title'>SISTEMA DE ACCESO<br>CONALEP CUAUTLA</div>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    if "resultado" not in st.session_state:
        st.session_state.resultado = None

    if "procesando" not in st.session_state:
        st.session_state.procesando = False

    def ejecutar_procesamiento(mat_raw):
        if not mat_raw or st.session_state.procesando:
            return

        st.session_state.procesando = True
        mat = normalizar_matricula(mat_raw)

        try:
            al_query = supabase.table("alumnos") \
                .select("*, estatus") \
                .filter("matricula", "eq", mat) \
                .execute()

            av_query = supabase.table("avisos") \
                .select("mensaje, prioridad") \
                .filter("matricula", "eq", mat) \
                .filter("activo", "eq", True) \
                .execute()

            if not al_query.data:
                st.session_state.resultado = {
                    "tipo": "error",
                    "mensaje": "MATRÍCULA NO REGISTRADA"
                }

            else:
                al = al_query.data[0]

                if al.get("estatus") is False:
                    st.session_state.resultado = {
                        "tipo": "bloqueado",
                        "nombre": al.get("nombre"),
                        "mensaje": "ACCESO DENEGADO / BLOQUEADO"
                    }

                else:
                    enviar("entradas", {
                        "fecha": datetime.now(zona).strftime("%Y-%m-%d"),
                        "hora": datetime.now(zona).strftime("%H:%M:%S"),
                        "matricula": mat,
                        "nombre": al.get("nombre", "N/A"),
                        "grupo": al.get("grupo", "N/A"),
                        "registro_por": user.get("usuario", "Sistema")
                    })

                    st.session_state.resultado = {
                        "tipo": "ok",
                        "nombre": al.get("nombre"),
                        "grupo": al.get("grupo"),
                        "aviso": av_query.data[0] if av_query.data else None
                    }

        except Exception as e:
            st.error(f"Error: {e}")

        finally:
            st.session_state.scan_input = ""
            st.session_state.procesando = False

    # --- INTERFAZ DE ESCANEO (LECTOR FÍSICO) ---
    _, col_input, _ = st.columns([1, 2, 1])
    with col_input:
        st.text_input(
            "ESCANEE SU CREDENCIAL AQUÍ (LECTOR LÁSER)",
            key="scan_input",
            placeholder="Esperando lectura...",
            on_change=lambda: ejecutar_procesamiento(
                st.session_state.scan_input
            )
        )

    # --- RESULTADOS VISUALES (DISEÑO ORIGINAL) ---
    if st.session_state.resultado:
        res = st.session_state.resultado

        if res["tipo"] == "ok":
            st.markdown("<div class='flash-overlay flash-ok'></div>", unsafe_allow_html=True)
            st.markdown(f"""
                <div style='text-align:center;
                            background:rgba(30, 132, 73, 0.2);
                            padding:40px;
                            border-radius:20px;
                            border:2px solid #00e676;'>
                    <div style='font-size:30px;
                                color:#00e676;
                                font-weight:bold;'>
                        ✅ ACCESO PERMITIDO
                    </div>
                    <div style='font-size:60px;
                                font-weight:900;
                                color:white;'>
                        {res['nombre']}
                    </div>
                    <div style='font-size:35px;
                                color:#f0f6fc;'>
                        GRUPO: {res['grupo']}
                    </div>
                </div>
            """, unsafe_allow_html=True)

            # --- AVISOS ---
            if res.get("aviso"):
                av = res["aviso"]
                color_aviso = "#ff1744" if av["prioridad"] == "ALTA" else "#ffeb3b"

                st.markdown(f"""
                    <div style='margin-top:20px;
                                padding:20px;
                                background:rgba(255,255,255,0.1);
                                border-left:10px solid {color_aviso};
                                border-radius:10px;'>
                        <h3 style='color:{color_aviso};
                                   margin:0;'>
                            ⚠️ AVISO PRIORIDAD {av["prioridad"]}
                        </h3>
                        <p style='font-size:24px;
                                  color:white;
                                  margin:10px 0;'>
                            {av["mensaje"]}
                        </p>
                    </div>
                """, unsafe_allow_html=True)

        elif res["tipo"] == "bloqueado":
            st.markdown("<div class='flash-overlay flash-warn'></div>", unsafe_allow_html=True)
            st.markdown(f"""
                <div style='text-align:center;
                            background:rgba(255, 152, 0, 0.2);
                            padding:40px;
                            border-radius:20px;
                            border:2px solid #ff9800;'>
                    <div style='font-size:40px;
                                color:#ff9800;
                                font-weight:bold;'>
                        ⚠️ {res['mensaje']}
                    </div>
                    <div style='font-size:50px;
                                font-weight:900;
                                color:white;'>
                        {res['nombre']}
                    </div>
                    <div style='font-size:25px;
                                color:#f0f6fc;
                                margin-top:10px;'>
                        FAVOR DE PASAR A LA OFICINA
                    </div>
                </div>
            """, unsafe_allow_html=True)

        else:  # ERROR
            st.markdown("<div class='flash-overlay flash-error'></div>", unsafe_allow_html=True)
            st.markdown(f"""
                <div style='text-align:center;
                            background:rgba(231, 76, 60, 0.2);
                            padding:40px;
                            border-radius:20px;
                            border:2px solid #ff1744;'>
                    <div style='font-size:50px;
                                color:#ff1744;
                                font-weight:bold;'>
                        ❌ {res['mensaje']}
                    </div>
                </div>
            """, unsafe_allow_html=True)

        time.sleep(3.5)
        st.session_state.resultado = None
        st.rerun()
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
                
                tab1, tab2 = st.tabs(["🕒 Registro de Entradas", "🚨 Reportes"])
                
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
# ================= AVISOS=================

elif menu == "Avisos":
    st.title("📢 Gestión de Avisos Escolares")
    st.markdown("Use este módulo para mostrar mensajes importantes al alumno al momento de escanear su credencial.")

    # Usamos la misma lógica de reset para limpiar el formulario al terminar
    if "aviso_reset_count" not in st.session_state:
        st.session_state.aviso_reset_count = 0
    
    def reset_avisos():
        st.session_state.aviso_reset_count += 1
        st.rerun()

    suffix_av = f"_av{st.session_state.aviso_reset_count}"

    # 1. Búsqueda del Alumno
    mat_av = st.text_input("Ingrese Matrícula del Alumno", key=f"mat_av{suffix_av}").strip().upper()

    if mat_av:
        try:
            # Validar existencia del alumno
            al_res = supabase.table("alumnos").select("nombre, grupo").eq("matricula", mat_av).execute()
            
            if al_res.data:
                al = al_res.data[0]
                st.success(f"Alumno: {al['nombre']} | Grupo: {al['grupo']}")

                # 2. Formulario de Aviso
                with st.form("form_nuevo_aviso"):
                    st.markdown("### Configuración del Mensaje")
                    
                    mensaje = st.text_area("Mensaje para el alumno", 
                                         placeholder="Ej: Pasar a prefectura inmediatamente",
                                         help="Este mensaje aparecerá en la pantalla de acceso.")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        prioridad = st.selectbox("Prioridad", ["BAJA", "MEDIA", "ALTA"])
                    with col2:
                        st.info("El aviso estará activo automáticamente al guardar.")

                    submit = st.form_submit_button("🔔 Publicar Aviso en Puerta")

                    if submit:
                        if mensaje.strip() == "":
                            st.error("El mensaje no puede estar vacío.")
                        else:
                            # 3. Guardar en la tabla 'avisos'
                            try:
                                # Primero desactivamos avisos anteriores del mismo alumno (opcional, para que solo tenga uno)
                                supabase.table("avisos").update({"activo": False}).eq("matricula", mat_av).execute()
                                
                                # Insertar nuevo aviso
                                datos_aviso = {
                                    "matricula": mat_av,
                                    "mensaje": mensaje,
                                    "prioridad": prioridad,
                                    "activo": True
                                }
                                
                                # Usamos tu función enviar o insert directo
                                supabase.table("avisos").insert(datos_aviso).execute()
                                
                                st.balloons()
                                st.success(f"✅ Aviso publicado para {al['nombre']}.")
                                time.sleep(2)
                                reset_avisos()
                            except Exception as e:
                                st.error(f"Error al guardar: {e}")
                
                # 4. Mostrar Avisos Actuales del Alumno (Para poder borrarlos)
                st.markdown("---")
                st.subheader("Aviso actual")
                hist_av = supabase.table("avisos").select("*").eq("matricula", mat_av).eq("activo", True).execute()
                
                if hist_av.data:
                    for av in hist_av.data:
                        c1, c2 = st.columns([4, 1])
                        c1.warning(f"**{av['prioridad']}**: {av['mensaje']}")
                        if c2.button("Eliminar", key=f"del_{av['id']}"):
                            supabase.table("avisos").update({"activo": False}).eq("id", av['id']).execute()
                            st.rerun()
                else:
                    st.write("No hay avisos activos para este alumno.")

            else:
                st.error("Matrícula no encontrada.")
        except Exception as e:
            st.error(f"Error: {e}")
# =================DASHBOARD DIRECTOR=================
elif menu == "Dashboard":
    st.title("🏛️ Panel de Control Directivo - CONALEP")
    st.markdown("---")

    try:
        # 1. CARGA DE DATOS
        res_rep = supabase.table("reportes").select("*").execute()
        res_ent = supabase.table("entradas").select("*").execute()
        res_al = supabase.table("alumnos").select("matricula, grupo").execute()

        if res_rep.data and res_ent.data and res_al.data:
            df_rep = pd.DataFrame(res_rep.data)
            df_ent = pd.DataFrame(res_ent.data)
            df_al = pd.DataFrame(res_al.data)

            # 2. NORMALIZACIÓN DE COLUMNAS (Forzar minúsculas y quitar espacios)
            df_rep.columns = [c.lower().strip() for c in df_rep.columns]
            df_al.columns = [c.lower().strip() for c in df_al.columns]
            df_ent.columns = [c.lower().strip() for c in df_ent.columns]

            # 3. UNIÓN Y CREACIÓN FORZOSA DE LA COLUMNA GRUPO
            # Si 'grupo' ya existe en reportes, la quitamos para traer la oficial de alumnos
            if 'grupo' in df_rep.columns:
                df_rep = df_rep.drop(columns=['grupo'])
            
            # Realizamos el cruce de tablas
            df_rep = df_rep.merge(df_al[['matricula', 'grupo']], on="matricula", how="left")
            
            # REGLA DE ORO: Si después del merge no hay grupo, lo creamos como "SIN GRUPO"
            if 'grupo' not in df_rep.columns:
                df_rep['grupo'] = "SIN GRUPO"
            else:
                df_rep['grupo'] = df_rep['grupo'].fillna("SIN GRUPO")

            # --- SECCIÓN DE MÉTRICAS ---
            c1, c2, c3, c4 = st.columns(4)
            total_ent = len(df_ent)
            total_inc = len(df_rep)
            # Buscamos 'nivel' de forma segura
            col_niv = 'nivel' if 'nivel' in df_rep.columns else None
            graves = len(df_rep[df_rep[col_niv].astype(str).str.upper() == 'REPORTE']) if col_niv else 0
            motivo = df_rep['tipo'].mode()[0] if not df_rep.empty and 'tipo' in df_rep.columns else "N/A"

            c1.metric("Asistencias", total_ent)
            c2.metric("Incidencias", total_inc, delta="Alerta", delta_color="inverse")
            c3.metric("Casos Graves", graves)
            c4.metric("Motivo Común", motivo)

            # --- GRÁFICAS ---
            st.markdown("### 📈 Análisis Visual")
            col_a, col_b = st.columns(2)

            with col_a:
                st.subheader("Reportes por Grupo")
                # Preparamos los datos para la gráfica asegurando que existan
                df_graf_grupos = df_rep['grupo'].value_counts().reset_index()
                df_graf_grupos.columns = ['grupo', 'conteo']
                
                fig_grupos = px.bar(df_graf_grupos, 
                                   x='conteo', y='grupo', orientation='h',
                                   color='conteo', color_continuous_scale='Reds')
                fig_grupos.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white")
                st.plotly_chart(fig_grupos, use_container_width=True)

            with col_b:
                st.subheader("Tendencia de Asistencia")
                if 'fecha' in df_ent.columns:
                    df_ent['fecha'] = pd.to_datetime(df_ent['fecha'])
                    asistencia_diaria = df_ent.groupby('fecha').size().reset_index(name='asistencias')
                    fig_asistencia = px.line(asistencia_diaria, x='fecha', y='asistencias', markers=True)
                    fig_asistencia.update_traces(line_color='#1e8449')
                    fig_asistencia.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white")
                    st.plotly_chart(fig_asistencia, use_container_width=True)

            # --- EXPORTACIÓN Y WHATSAPP ---
            st.markdown("---")
            fecha_hoy = datetime.now(zona).strftime('%d/%m/%Y')
            texto_reporte = f"*RESUMEN DIRECTIVO SICA - {fecha_hoy}*\nTotal Asistencias: {total_ent}\nTotal Reportes: {total_inc}\nCasos Graves: {graves}"
            
            col_w1, col_w2 = st.columns(2)
            with col_w1:
                # Botón de WhatsApp (Ajusta el número)
                numero = "527351234567"
                url_wa = f"https://wa.me/{numero}?text={texto_reporte.replace(' ', '%20')}"
                st.markdown(f'<a href="{url_wa}" target="_blank" style="text-decoration:none;"><div style="background-color:#25d366;color:white;padding:10px;border-radius:10px;text-align:center;font-weight:bold;">📲 Enviar a WhatsApp</div></a>', unsafe_allow_html=True)
            with col_w2:
                st.text_area("Reporte para copiar:", value=texto_reporte, height=100)

        else:
            st.info("No hay suficientes datos registrados para generar el Dashboard.")

    except Exception as e:
        st.error(f"Error al generar Dashboard: {e}")
# ================= CONFIGURACIÓN INICIAL =================
elif menu == "Servicios y Técnica":
    st.title("⚙️ Panel de Servicios Escolares y Formación Técnica")
    st.markdown("---")

    try:
        # 1. CARGA DE DATOS
        res_rep = supabase.table("reportes").select("*").execute()
        res_al = supabase.table("alumnos").select("*").execute()
        
        if res_rep.data and res_al.data:
            df_rep = pd.DataFrame(res_rep.data)
            df_al = pd.DataFrame(res_al.data)

            # Normalización
            df_rep.columns = [c.lower().strip() for c in df_rep.columns]
            df_al.columns = [c.lower().strip() for c in df_al.columns]

            # --- SECCIÓN: PRODUCTIVIDAD DE PREFECTURA Y PERSONAL ---
            st.subheader("👮 Control de Desempeño Operativo")
            st.info("Métricas de reportes generados por cada miembro del personal.")

            if 'registrado_por' in df_rep.columns:
                # Calculamos el conteo por persona
                prod_personal = df_rep['registrado_por'].value_counts().reset_index()
                prod_personal.columns = ['Personal / Prefecto', 'Total Reportes']
                
                col_m1, col_m2 = st.columns([2, 1])
                
                with col_m1:
                    # Gráfica de barras de productividad
                    fig_prod = px.bar(prod_personal, 
                                     x='Total Reportes', y='Personal / Prefecto', 
                                     orientation='h',
                                     color='Total Reportes',
                                     color_continuous_scale='Greens',
                                     text_auto=True)
                    fig_prod.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white")
                    st.plotly_chart(fig_prod, use_container_width=True)
                
                with col_m2:
                    st.markdown("**Top 5 Mayor Actividad**")
                    st.table(prod_personal.head(5))

                # --- FILTRO POR PREFECTO ---
                st.markdown("---")
                st.subheader("🔍 Consultar Trabajo por Persona")
                lista_personal = df_rep['registrado_por'].unique()
                prefecto_sel = st.selectbox("Seleccione al Prefecto/Personal para ver su detalle:", lista_personal)
                
                if prefecto_sel:
                    detalle_pref = df_rep[df_rep['registrado_por'] == prefecto_sel]
                    st.write(f"Mostrando los últimos {len(detalle_pref)} reportes levantados por **{prefecto_sel}**:")
                    # Mostramos columnas clave para Servicios Escolares
                    columnas_ver = [c for c in ['fecha', 'matricula', 'nombre', 'tipo', 'nivel'] if c in detalle_pref.columns]
                    st.dataframe(detalle_pref[columnas_ver], use_container_width=True, hide_index=True)

            else:
                st.warning("No se ha detectado la columna 'registrado_por' en la base de datos de reportes.")

            # --- SECCIÓN: ALUMNOS EN SEGUIMIENTO ---
            st.markdown("---")
            st.subheader("📋 Lista de Alumnos en Riesgo")
            conteo_al = df_rep['matricula'].value_counts().reset_index()
            conteo_al.columns = ['matricula', 'Total']
            alumnos_riesgo = conteo_al[conteo_al['Total'] >= 2]
            st.table(alumnos_riesgo.head(10))

        else:
            st.info("No hay datos suficientes para mostrar métricas operativas.")

    except Exception as e:
        st.error(f"Error en Panel de Servicios: {e}")
# ================= EXPEDIENTE DIGITAL (CON BOTÓN DE BLOQUEO) =================
# ================= EXPEDIENTE DIGITAL ACTUALIZADO =================
# ================= EXPEDIENTE DIGITAL FINAL Y CORREGIDO =================
# ================= EXPEDIENTE DIGITAL FINAL (CORRECCIÓN DE ERRORES) =================
elif menu == "Expediente Digital":
    st.title("🗂️ Expediente Digital Integral")
    
    mat_exp = st.text_input("Ingrese Matrícula").strip().upper()

    if mat_exp:
        try:
            # 1. CARGA DE DATOS (Primero traemos todo de la base de datos)
            al_res = supabase.table("alumnos").select("*").eq("matricula", mat_exp).execute()
            
            if al_res.data:
                al = al_res.data[0]
                estatus_actual = al.get("estatus", True)
                
                # Consultas a tablas relacionadas
                res_rep = supabase.table("reportes").select("*").eq("matricula", mat_exp).execute()
                res_ent = supabase.table("entradas").select("*").eq("matricula", mat_exp).execute()
                res_av = supabase.table("avisos").select("*").eq("matricula", mat_exp).eq("activo", True).execute()
                
                # DEFINICIÓN DE VARIABLES (Aseguramos que existan antes de que el PDF las pida)
                df_rep = pd.DataFrame(res_rep.data) if res_rep.data else pd.DataFrame()
                df_ent = pd.DataFrame(res_ent.data) if res_ent.data else pd.DataFrame()
                list_av = res_av.data if res_av.data else [] 
                
                # Lógica de Riesgo
                puntos = len(df_rep)
                if puntos == 0: color_r, txt_r = "#00e676", "BAJO"
                elif puntos <= 2: color_r, txt_r = "#ffeb3b", "MEDIO"
                else: color_r, txt_r = "#ff5252", "ALTO"

                # --- 2. FUNCIÓN PDF CON SOPORTE PARA ACENTOS Y EMOJIS ---
                def generar_pdf_seguro(datos_al, reporte_df, avisos, riesgo_txt):
                    pdf = FPDF()
                    pdf.add_page()
                    # Usamos 'Helvetica' o 'Arial' y reemplazamos caracteres problemáticos
                    pdf.set_font("Arial", 'B', 16)
                    pdf.cell(200, 10, "CONALEP CUAUTLA - EXPEDIENTE DIGITAL", ln=True, align='C')
                    
                    pdf.ln(5)
                    pdf.set_font("Arial", 'B', 12)
                    pdf.cell(0, 10, f"RIESGO: {riesgo_txt}", ln=True, align='R')
                    
                    pdf.set_fill_color(240, 240, 240)
                    pdf.cell(0, 10, "DATOS DEL ALUMNO", ln=True, fill=True)
                    pdf.set_font("Arial", '', 11)
                    # El .encode('latin-1', 'replace').decode('latin-1') evita el error de la imagen 3
                    nombre_limpio = datos_al.get('nombre', '').encode('latin-1', 'replace').decode('latin-1')
                    pdf.cell(0, 8, f"Nombre: {nombre_limpio}", ln=True)
                    pdf.cell(0, 8, f"Matricula: {datos_al.get('matricula')}", ln=True)
                    
                    if avisos:
                        pdf.ln(5)
                        pdf.cell(0, 10, "AVISOS VIGENTES", ln=True, fill=True)
                        for av in avisos:
                            msg = av['mensaje'].encode('latin-1', 'replace').decode('latin-1')
                            pdf.cell(0, 8, f"- {msg}", ln=True)

                    pdf.ln(5)
                    pdf.cell(0, 10, "HISTORIAL", ln=True, fill=True)
                    if not reporte_df.empty:
                        for _, row in reporte_df.iterrows():
                            tipo = str(row.get('tipo', '')).encode('latin-1', 'replace').decode('latin-1')
                            desc = str(row.get('descripcion', '')).encode('latin-1', 'replace').decode('latin-1')
                            pdf.multi_cell(0, 8, f"[{row['fecha']}] {tipo}: {desc}", border=1)
                    
                    return pdf.output(dest='S').encode('latin-1', 'ignore')

                # --- 3. FUNCIÓN DE BLOQUEO ---
                def gestionar_acceso(bloquear=True):
                    nuevo_estatus = not bloquear
                    supabase.table("alumnos").update({"estatus": nuevo_estatus}).eq("matricula", mat_exp).execute()
                    if bloquear:
                        # Quitamos el emoji del mensaje para evitar errores de PDF
                        supabase.table("avisos").insert({
                            "matricula": mat_exp, 
                            "mensaje": "ACCESO RESTRINGIDO: PASAR A DIRECCION", 
                            "prioridad": "ALTA", "activo": True
                        }).execute()
                    else:
                        supabase.table("avisos").update({"activo": False}).eq("matricula", mat_exp).execute()
                    time.sleep(1)
                    st.rerun()

                # --- 4. INTERFAZ ---
                col_perfil, col_riesgo, col_accion = st.columns([2, 1, 1])
                with col_perfil:
                    st.markdown(f"<div style='background:#161b22; padding:20px; border-radius:15px; border-left:8px solid #1e8449;'><h2 style='margin:0; color:white;'>{al.get('nombre')}</h2><p style='margin:0; color:#8b949e;'>Grupo: {al.get('grupo')} | Matrícula: {mat_exp}</p></div>", unsafe_allow_html=True)
                
                with col_riesgo:
                    st.markdown(f"<div style='background:#161b22; padding:20px; border-radius:15px; text-align:center; border: 2px solid {color_r};'><p style='margin:0; color:#8b949e; font-size:12px;'>RIESGO</p><h2 style='margin:0; color:{color_r};'>{txt_r}</h2></div>", unsafe_allow_html=True)

                with col_accion:
                    if estatus_actual:
                        if st.button("🚫 BLOQUEAR", use_container_width=True): gestionar_acceso(True)
                    else:
                        if st.button("✅ ACTIVAR", use_container_width=True, type="primary"): gestionar_acceso(False)

                # --- 5. BOTÓN PDF Y TABS ---
                pdf_data = generar_pdf_seguro(al, df_rep, list_av, txt_r)
                st.download_button(
                    label="📥 Descargar Expediente (PDF)",
                    data=pdf_data,
                    file_name=f"Expediente_{mat_exp}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )

                t1, t2 = st.tabs(["🕒 Asistencias", "🚨 Reportes"])
                with t1: st.dataframe(df_ent, use_container_width=True)
                with t2: st.dataframe(df_rep, use_container_width=True)

            else:
                st.error("Matrícula no encontrada.")
        except Exception as e:
            st.error(f"Error en el sistema: {e}")



















































































































