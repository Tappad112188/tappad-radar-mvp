import streamlit as st
import pandas as pd

st.set_page_config(page_title="Radar de Licitaciones", page_icon="💼", layout="wide")

def normalizar(text):
    if not text: return ""
    text = str(text).lower().strip()
    reemplazos = [("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u")]
    for a, b in reemplazos: text = text.replace(a, b)
    return text

# Inicializar bases de datos en la memoria de la app
if "lista_clientes" not in st.session_state:
    st.session_state.lista_clientes = [
        {"nombre": "Constructora del Norte S.A.", "correo": "contacto@constnorte.com", "keywords": "construccion, pavimentacion, obra publica"}
    ]

licitaciones_gobierno = [
    {"id": "LO-2026-01", "portal": "ComprasMX", "titulo": "Construcción de puente vehicular y vialidades", "dependencia": "SCT"},
    {"id": "CE-SEFIRC-99", "portal": "SEFIRC Coahuila", "titulo": "Adquisición de licencias de software y computadoras", "dependencia": "SEFIN Coahuila"},
    {"id": "LO-2026-02", "portal": "ComprasMX", "titulo": "Servicio de limpieza profunda y sanitización", "dependencia": "IMSS"},
    {"id": "CE-SEFIRC-100", "portal": "SEFIRC Coahuila", "titulo": "Pavimentación y bacheo asfáltico en Saltillo", "dependencia": "Infraestructura Coahuila"}
]

# --- INTERFAZ VISUAL ---
st.title("💼 Sistema de Monitoreo de Licitaciones")
st.write("Mapeo automático de ComprasMX y Portal de Licitaciones de Coahuila.")

# CREAMOS DOS PESTAÑAS: UNA PARA EL CLIENTE Y OTRA PARA TI (ADMIN)
tab1, tab2 = st.tabs(["📱 VISTA DEL CLIENTE (Registro)", "⚙️ VISTA DE CONSULTOR (Administrador)"])

with tab1:
    st.header("¡Regístrate para recibir Alertas Premium!")
    st.write("Ingresa tus datos para que nuestro sistema busque licitaciones por ti todas las mañanas.")
    
    # AQUÍ ESTÁ EL FORMULARIO QUE EL CLIENTE VE Y RELLENA:
    with st.form("formulario_registro", clear_on_submit=True):
        nombre_cliente = st.text_input("1. Nombre de tu Empresa / Razón Social:", placeholder="Ej. Materiales Sierra Madre S.A.")
        correo_cliente = st.text_input("2. Correo electrónico donde quieres recibir las notificaciones:", placeholder="ejemplo@empresa.com")
        keywords_cliente = st.text_input("3. Palabras clave de lo que vendes (separadas por comas):", placeholder="Ej. software, computadoras, limpieza, construccion")
        
        boton_enviar = st.form_submit_button("CONTRATAR SERVICIO Y ACTIVAR RADAR")
        
        if boton_enviar:
            if nombre_cliente and correo_cliente and keywords_cliente:
                # Guardar al cliente visualmente
                nuevo = {"nombre": nombre_cliente, "correo": correo_cliente, "keywords": keywords_cliente}
                st.session_state.lista_clientes.append(nuevo)
                
                st.success(f"¡Registro Exitoso, {nombre_cliente}! El sistema se ha activado para el correo: {correo_cliente}")
                st.balloons()
                
                # EJECUTAR EL CRUCE INMEDIATAMENTE PARA EL NUEVO CLIENTE
                st.subheader("🔍 Buscando oportunidades en este momento...")
                palabras_lista = [k.strip() for k in keywords_cliente.split(",")]
                matches = []
                
                for lic in licitaciones_gobierno:
                    titulo_norm = normalizar(lic["titulo"])
                    for kw in palabras_lista:
                        if normalizar(kw) in titulo_norm:
                            if lic not in matches: matches.append(lic)
                
                if matches:
                    st.info(f"📬 ¡Se han detectado las siguientes licitaciones vigentes para ti! Se ha enviado una copia a {correo_cliente}:")
                    for m in matches:
                        st.markdown(f"* **[{m['portal']}]** {m['titulo']} — *Dependencia: {m['dependencia']} (ID: {m['id']})*")
                else:
                    st.warning("No se encontraron licitaciones con tus palabras clave el día de hoy, pero te notificaremos mañana en la madrugada si aparece alguna.")
            else:
                st.error("Por favor, rellena todos los campos del formulario.")

with tab2:
    st.header("Panel de Control Interno")
    st.write("Aquí puedes ver a los clientes que se han registrado visualmente desde la otra pestaña.")
    st.dataframe(pd.DataFrame(st.session_state.lista_clientes))
    
    st.subheader("Licitaciones Activas en el Servidor (Gobierno)")
    st.dataframe(pd.DataFrame(licitaciones_gobierno))

                    st.write(f"• **[{opon['portal']}]** {opon['titulo']} | Dependencia: {opon['dependencia']} (ID: {opon['id']})")
    
    st.balloons()
    st.success(f"¡Proceso terminado con éxito! Se simularon {alertas_enviadas} notificaciones premium.")
