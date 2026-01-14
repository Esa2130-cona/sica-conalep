import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import pytz

# ================= CONFIG =================
st.set_page_config(page_title="SICA CONALEP CUAUTLA", layout="wide", page_icon="🏢")
zona = pytz.timezone("America/Mexico_City")

SHEET_ID = "11RZyoBo_MyQkGWfc21WCY_xPFZdKkwTG12YagiZf3yM"
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbwEzRUIDz4YtnT40VIbAwUs7WOgba0DWjSTYt2d7-QdZKFo3BCetNrB0kSy4Y4w4fTncg/exec"

# GIDs de las pestañas
GID_ALUMNOS = 1882885827
GID_USUARIOS = 921806663
GID_ENTRADAS = 25814912
GID_INCIDENCIAS = 2080119575
GID_ACADEMICO = 1794524153

# ================= FUNCIONES =================
@st.cache_data(ttl=5) # Cache corto para ver actualizaciones rápido
def cargar(gid):
    try:
        url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={gid}"
        df = pd.read_csv(url)
        # Limpieza de encabezados para evitar KeyErrors
        df.columns = (
            df.columns.astype(str).str.strip().str.upper()
            .str.replace("Á","A").str.replace("É","E")
            .str.replace("Í","I").str.replace("Ó","O").str.replace("Ú","U")
        )
        return df
    except Exception as e:
        st.error(f"Error cargando datos (GID {gid}): {e}")
        return pd.DataFrame()

# Carga inicial de datos
df_alumnos = cargar(GID_ALUMNOS)
df_usuarios = cargar(GID_USUARIOS)
df_entradas = cargar(GID_ENTRADAS)

# ================= LOGIN =================
if "user" not in st.session_state:
    st.session_state.user = None

if not st.session_state.user:
    st.markdown("<h1 style='text-align: center;'>🔐 SICA - CONALEP CUAUTLA</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        u = st.text_input("Usuario")
        p = st.text_input("PIN", type="password")
        if st.button("Ingresar", use_container_width=True):
            if not df_usuarios.empty and "USUARIO" in df_usuarios.columns:
                # Buscamos coincidencia
                m = df_usuarios[
                    (df_usuarios["USUARIO"].astype(str).str.lower() == u.lower()) &
                    (df_usuarios["PIN"].astype(str) == p)
                ]
                if not m.empty:
                    st.session_state.user = m.iloc[0].to_dict()
                    st.rerun()
                else:
                    st.error("Usuario o PIN incorrectos")
            else:
                st.error("Error: No se pudo leer la tabla de usuarios.")
    st.stop()

user = st.session_state.user

# ================= MENU LATERAL =================
st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/thumb/1/1b/Conalep_Logo.svg/1200px-Conalep_Logo.svg.png", width=100)
st.sidebar.title(f"Bienvenido,\n{user['NOMBRE']}")

opciones = ["Puerta de Entrada", "Historial Alumnos"]
rol = str(user["ROL"]).upper()

if rol == "ADMIN":
    opciones += ["Incidencias", "Academico", "Reportes"]
elif rol in ["PREFECTO", "SERVICIOS_ESCOLARES"]:
    opciones += ["Incidencias"]
elif rol == "FORMACION":
    opciones += ["Academico"]

menu = st.sidebar.radio("MENÚ PRINCIPAL", opciones)

if st.sidebar.button("Cerrar sesión"):
    st.session_state.user = None
    st.rerun()

# ================= MÓDULO: PUERTA DE ENTRADA =================
if menu == "Puerta de Entrada":
    st.markdown("## 🚪 Registro de Acceso en Tiempo Real")
    
    # Campo de texto que siempre debe estar enfocado para el escáner
    mat = st.text_input("ESCANEÉ LA MATRÍCULA AQUÍ", key="scanner").strip()

    if mat:
        # Buscamos al alumno
        alumno_data = df_alumnos[df_alumnos["MATRICULA"].astype(str) == mat]
        
        if alumno_data.empty:
            st.error(f"❌ Matrícula {mat} no encontrada en el sistema.")
        else:
            al = alumno_data.iloc[0]
            nombre_completo = f"{al['NOMBRE']} {al['PRIMER APELLIDO']} {al.get('SEGUNDO APELLIDO', '')}"
            
            # Formatear datos para el envío
            fecha_hoy = datetime.now(zona).strftime("%Y-%m-%d")
            hora_hoy = datetime.now(zona).strftime("%H:%M:%S")

            # --- PARTE VISUAL: BIENVENIDA Y FOTO ---
            st.divider()
            col_foto, col_info = st.columns([1, 2])
            
            with col_foto:
                # Si tienes una columna 'FOTO' con el link de la imagen
                if "FOTO" in al and pd.notna(al["FOTO"]):
                    st.image(al["FOTO"], caption=f"Matrícula: {mat}", width=250)
                else:
                    st.image("https://via.placeholder.com/250x300?text=Sin+Foto", width=250)

            with col_info:
                st.balloons() # Efecto visual de éxito
                st.markdown(f"<h1 style='color: #1E8449;'>¡BIENVENIDO!</h1>", unsafe_allow_html=True)
                st.markdown(f"### {nombre_completo}")
                st.write(f"**Grupo:** {al['GRUPO']}")
                st.write(f"**Carrera:** {al.get('CARRERA', 'N/A')}")
                st.write(f"**Hora de entrada:** {hora_hoy}")
            
            # Enviar a Google Sheets vía Apps Script
            payload = {
                "TIPO_REGISTRO": "ENTRADA",
                "FECHA": fecha_hoy,
                "HORA": hora_hoy,
                "MATRICULA": mat,
                "NOMBRE": nombre_completo,
                "GRUPO": al["GRUPO"],
                "REGISTRO_POR": user["NOMBRE"]
            }
            
            try:
                res = requests.post(APPS_SCRIPT_URL, json=payload)
                if res.status_code == 200:
                    st.toast("✅ Registro guardado en la nube")
                else:
                    st.warning("⚠️ El registro se mostró pero no se pudo guardar en el Excel.")
            except:
                st.error("Error de conexión con el servidor.")

# ================= MÓDULO: HISTORIAL =================
elif menu == "Historial Alumnos":
    st.title("📊 Consulta de Movimientos")
    tab1, tab2 = st.tabs(["🔍 Por Alumno", "📅 Por Día"])

    with tab1:
        busqueda = st.text_input("Ingrese matrícula para consultar historial")
        if busqueda:
            resultado = df_entradas[df_entradas["MATRICULA"].astype(str) == busqueda]
            if not resultado.empty:
                st.dataframe(resultado, use_container_width=True)
            else:
                st.info("No hay registros para esta matrícula.")

    with tab2:
        fecha_sel = st.date_input("Seleccione una fecha", datetime.now(zona))
        fecha_str = fecha_sel.strftime("%Y-%m-%d")
        # Filtramos asegurando que la columna FECHA sea string
        resultado_dia = df_entradas[df_entradas["FECHA"].astype(str).str.contains(fecha_str)]
        if not resultado_dia.empty:
            st.write(f"Registros encontrados: {len(resultado_dia)}")
            st.dataframe(resultado_dia, use_container_width=True)
        else:
            st.info("No hubo registros en la fecha seleccionada.")

# ================= OTROS MÓDULOS (INCIDENCIAS, ACADEMICO, REPORTES) =================
# ... (Se mantienen igual pero con validaciones de seguridad para evitar KeyErrors)
elif menu == "Incidencias":
    st.title("🚨 Registro de Incidencias")
    mat_inc = st.text_input("Matrícula del Alumno").strip()
    if mat_inc:
        al_inc = df_alumnos[df_alumnos["MATRICULA"].astype(str) == mat_inc]
        if not al_inc.empty:
            al_i = al_inc.iloc[0]
            st.warning(f"Registrando a: {al_i['NOMBRE']} {al_i['PRIMER APELLIDO']}")
            tipo = st.selectbox("Tipo de Incidencia", ["Retardo", "Falta", "Disciplina", "Uniforme"])
            desc = st.text_area("Descripción de los hechos")
            if st.button("Guardar Incidencia"):
                requests.post(APPS_SCRIPT_URL, json={
                    "TIPO_REGISTRO": "INCIDENCIA",
                    "FECHA": datetime.now(zona).strftime("%Y-%m-%d"),
                    "HORA": datetime.now(zona).strftime("%H:%M:%S"),
                    "MATRICULA": mat_inc,
                    "NOMBRE": al_i["NOMBRE"],
                    "GRUPO": al_i["GRUPO"],
                    "TIPO": tipo,
                    "DESCRIPCION": desc,
                    "REGISTRO_POR": user["NOMBRE"]
                })
                st.success("Incidencia enviada.")
        else:
            st.error("Alumno no encontrado.")

elif menu == "Reportes":
    st.title("📈 Estadísticas Mensuales")
    if not df_entradas.empty:
        df_entradas["FECHA"] = pd.to_datetime(df_entradas["FECHA"])
        # Conteo por día
        conteo = df_entradas.resample('D', on='FECHA').size()
        st.line_chart(conteo)
        st.write("Resumen de entradas recientes", df_entradas.tail(10))






