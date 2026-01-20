import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime
import pytz
import time
import plotly.express as px
import plotly.graph_objects as go

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
# 1. Agregamos "Avisos" a la lista base
opciones = ["Puerta de Entrada", "Reportes", "Historial", "Avisos", "Bitácora Maestros","Dashboard","Servicios y Técnica"]

# 2. Filtramos según el rol
if rol == "KIOSKO": 
    opciones = ["Puerta de Entrada"]
else:
    # Si no es kiosko, puede ver todo, incluyendo la gestión de avisos
    pass

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
            # 1. Buscamos al alumno
            al_query = supabase.table("alumnos").select("*").filter("matricula", "eq", mat).execute()
            
            # 2. Buscamos avisos incluyendo la PRIORIDAD
            av_query = supabase.table("avisos").select("mensaje, prioridad").filter("matricula", "eq", mat).filter("activo", "eq", True).execute()

            if not al_query.data:
                st.session_state.resultado = {"tipo": "error", "mensaje": "NO REGISTRADO"}
            else:
                al = al_query.data[0]
                nombre = al.get("nombre", al.get("NOMBRE", "Estudiante"))
                grupo = al.get("grupo", al.get("GRUPO", "N/A"))
                
                # Extraemos mensaje y prioridad si existen
                aviso_data = av_query.data[0] if av_query.data else None
                
                enviar("entradas", {
                    "fecha": datetime.now(zona).strftime("%Y-%m-%d"),
                    "hora": datetime.now(zona).strftime("%H:%M:%S"),
                    "matricula": mat,
                    "nombre": nombre,
                    "grupo": grupo,
                    "registro_por": user.get("usuario", "Sistema")
                })
                
                st.session_state.resultado = {
                    "tipo": "ok", 
                    "nombre": nombre, 
                    "grupo": grupo, 
                    "aviso": aviso_data  # Guardamos el objeto completo del aviso
                }
        except Exception as e:
            st.session_state.resultado = {"tipo": "error", "mensaje": f"Error DB: {str(e)[:40]}"}

    st.text_input("", key="scan_input", on_change=procesar_scan, placeholder="ESCANEE AQUÍ", autocomplete="off")

    if st.session_state.resultado:
        res = st.session_state.resultado
        if res["tipo"] == "ok":
            # Card principal de acceso
            st.markdown(f"""
                <div class='res-card res-ok'>
                    <div style='font-size:30px; color:#00e676;'>✅ ACCESO PERMITIDO</div>
                    <div class='student-name'>{res['nombre']}</div>
                    <div style='font-size:25px; color:white;'>GRUPO: {res['grupo']}</div>
                </div>
            """, unsafe_allow_html=True)
            
            # Lógica de Avisos por Prioridad
            if res["aviso"]:
                msg = res["aviso"]["mensaje"]
                prio = str(res["aviso"].get("prioridad", "BAJA")).upper()
                
                # Definimos color según prioridad para que sea visualmente moderno
                # Rojo para ALTA, Naranja para MEDIA, Azul para BAJA
                colores = {"ALTA": "#e74c3c", "MEDIA": "#f39c12", "BAJA": "#3498db"}
                color_fondo = colores.get(prio, "#3498db")

                st.markdown(f"""
                    <div style='background-color: {color_fondo}; padding: 20px; border-radius: 15px; 
                                color: white; text-align: center; margin-top: 15px; border: 2px solid white;'>
                        <div style='font-size: 18px; font-weight: bold; opacity: 0.9;'>⚠️ AVISO PRIORIDAD {prio}</div>
                        <div style='font-size: 24px; font-weight: bold;'>{msg}</div>
                    </div>
                """, unsafe_allow_html=True)
                
        else:
            st.markdown(f"<div class='res-card res-error'><h1>❌ {res['mensaje']}</h1></div>", unsafe_allow_html=True)
        
        # Aumentamos un poco el tiempo si hay aviso para que alcancen a leer
        tiempo = 4.0 if res.get("aviso") else 2.0
        time.sleep(tiempo)
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
        # 1. CARGA DE DATOS SEGURA
        res_rep = supabase.table("reportes").select("*").execute()
        res_al = supabase.table("alumnos").select("*").execute()
        res_av = supabase.table("avisos").select("*").eq("activo", True).execute()

        if res_rep.data and res_al.data:
            df_rep = pd.DataFrame(res_rep.data)
            df_al = pd.DataFrame(res_al.data)
            df_av = pd.DataFrame(res_av.data) if res_av.data else pd.DataFrame()

            # Normalización a minúsculas para evitar errores de escritura (GRUPO vs grupo)
            df_rep.columns = [c.lower().strip() for c in df_rep.columns]
            df_al.columns = [c.lower().strip() for c in df_al.columns]

            # 2. IDENTIFICAR COLUMNAS DISPONIBLES
            # Verificamos si existen las columnas críticas para no tronar
            cols_al = df_al.columns.tolist()
            
            # Definimos qué columnas de alumnos queremos traer al reporte
            columnas_interes = ['matricula']
            if 'nombre' in cols_al: columnas_interes.append('nombre')
            if 'grupo' in cols_al: columnas_interes.append('grupo')
            if 'turno' in cols_al: columnas_interes.append('turno')

            # 3. UNIÓN DE TABLAS (Merge)
            df_master = df_rep.merge(df_al[columnas_interes], on="matricula", how="left")
            
            # Si 'grupo' existe, llenamos los vacíos para que no falle la visualización
            if 'grupo' in df_master.columns:
                df_master['grupo'] = df_master['grupo'].fillna("N/A")

            # --- MÉTRICAS OPERATIVAS ---
            m1, m2, m3 = st.columns(3)
            with m1:
                # Alumnos con 2 o más reportes (Seguimiento preventivo)
                conteo = df_master['matricula'].value_counts()
                riesgo = len(conteo[conteo >= 2])
                st.metric("Alumnos en Seguimiento", riesgo)
            with m2:
                st.metric("Avisos Activos", len(df_av))
            with m3:
                st.metric("Total de Incidencias", len(df_master))

            # --- DETECCIÓN DE INCIDENCIAS TÉCNICAS ---
            st.subheader("🛠️ Alertas en Talleres y Laboratorios")
            palabras_clave = ['taller', 'laboratorio', 'maquina', 'herramienta', 'practica', 'seguridad']
            
            # Buscamos en la descripción (si existe la columna)
            if 'descripcion' in df_master.columns:
                df_tec = df_master[df_master['descripcion'].str.contains('|'.join(palabras_clave), case=False, na=False)]
                
                if not df_tec.empty:
                    st.warning(f"Se detectaron {len(df_tec)} incidencias técnicas.")
                    # Mostramos solo las columnas que sabemos que existen
                    columnas_ver = [c for c in ['fecha', 'nombre', 'grupo', 'descripcion'] if c in df_tec.columns]
                    st.dataframe(df_tec[columnas_ver], use_container_width=True)
                else:
                    st.success("No hay reportes técnicos pendientes.")
            
            # --- LISTA DE SEGUIMIENTO ---
            st.subheader("📋 Estudiantes con Reportes Recurrentes")
            if 'nombre' in df_master.columns:
                # Agrupamos por los datos disponibles
                cols_agrupar = [c for c in ['matricula', 'nombre', 'grupo'] if c in df_master.columns]
                seguimiento = df_master.groupby(cols_agrupar).size().reset_index(name='Total')
                seguimiento = seguimiento[seguimiento['Total'] >= 2].sort_values(by='Total', ascending=False)
                st.table(seguimiento.head(10))

        else:
            st.info("Aún no hay datos suficientes en las tablas de alumnos o reportes.")

    except Exception as e:
        st.error(f"Error en Dashboard Operativo: {e}")

















































































































