import streamlit as st
import qrcode
from io import BytesIO
from supabase import create_client

# 1. Conexión (Usa los mismos secrets que tu SICA original)
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

# 2. Configuración de página
st.set_page_config(page_title="Credencial Digital - CONALEP", page_icon="📲")

# Estilos rápidos para que se vea bien en celular
st.markdown("""
    <style>
    .main { background-color: #050a10; }
    .stTextInput input { color: #000; background-color: #fff; }
    h1, h3 { color: white; text-align: center; }
    </style>
""", unsafe_allow_html=True)

st.title("🎫 Mi Credencial Digital")
st.markdown("### SICA - CONALEP Cuautla")

# 3. Interfaz de usuario
matricula = st.text_input("Ingresa tu Matrícula oficial:", placeholder="Ej: 22173XXXX-X").strip().upper()

if matricula:
    try:
        # Buscamos si existe y si NO está bloqueado
        res = supabase.table("alumnos").select("nombre, estatus").eq("matricula", matricula).execute()
        
        if res.data:
            alumno = res.data[0]
            
            if alumno.get("estatus") == False:
                st.error("⚠️ ACCESO RESTRINGIDO. Favor de acudir a Dirección.")
            else:
                st.success(f"¡Hola {alumno['nombre']}! Aquí está tu código de acceso:")
                
                # Generación del QR
                qr = qrcode.QRCode(version=1, box_size=10, border=4)
                qr.add_data(matricula)
                qr.make(fit=True)
                
                img = qr.make_image(fill_color="black", back_color="white")
                
                # Mostrar en Streamlit
                buf = BytesIO()
                img.save(buf, format="PNG")
                st.image(buf, use_container_width=True)
                
                st.info("💡 Toma una captura de pantalla. Podrás usar esta imagen para entrar al plantel.")
        else:
            st.error("Matrícula no encontrada. Verifica tus datos.")
            
    except Exception as e:
        st.error("Error de conexión. Intenta más tarde.")
