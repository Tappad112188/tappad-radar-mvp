import streamlit as st
import pandas as pd

# Configuración de la página
st.set_page_config(page_title="Radar de Licitaciones", page_icon="💼", layout="wide")

# 1. Función para limpiar texto (corregida y funcionando)
def normalizar(text):
    if not text:
        return ""
    text = str(text).lower().strip()
    reemplazos = [("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u")]
    for a, b in reemplazos:
        text = text.replace(a, b)
    return text

# --- INTERFAZ VISUAL ---
st.title("💼 Radar de Licitaciones Premium")
st.subheader("Consultoría Estratégica - Monitoreo ComprasMX y SEFIRC Coahuila")
st.write("Bienvenido al simulador de coincidencias para clientes registrados.")

# 2. Base de datos simulada de Clientes Premium
clientes = [
    {"nombre": "Constructora del Norte S.A.", "correo": "contacto@constnorte.com", "keywords": ["construccion", "pavimentacion", "obra pública"]},
    {"nombre": "Tecnologías Globales MX", "correo": "ventas@tecglobal.mx", "keywords": ["software", "computadoras", "licencias", "sistemas"]},
    {"nombre": "Limpieza y Mantenimiento Laguna", "correo": "servicios@limpiezalaguna.com", "keywords": ["limpieza", "sanitizacion", "insumos"]}
]

# 3. Base de datos simulada de Licitaciones Recientes
licitaciones = [
    {"id": "LO-01-2026", "portal": "ComprasMX", "titulo": "Construcción de puente vehicular en Saltillo", "dependencia": "SCT", "fecha": "10-Oct-2026"},
    {"id": "CE-SEFIRC-02", "portal": "SEFIRC Coahuila", "titulo": "Adquisición de licencias de software y servidores", "dependencia": "SEFIN Coahuila", "fecha": "09-Oct-2026"},
    {"id": "LO-02-2026", "portal": "ComprasMX", "titulo": "Servicio de limpieza profunda para oficinas federales", "dependencia": "IMSS", "fecha": "08-Oct-2026"},
    {"id": "CE-SEFIRC-03", "portal": "SEFIRC Coahuila", "titulo": "Pavimentación y bacheo en vialidades de Torreón", "dependencia": "Infraestructura Coahuila", "fecha": "07-Oct-2026"}
]

# Mostrar los datos en la app para validar
col1, col2 = st.columns(2)

with col1:
    st.markdown("### 👥 Clientes Premium Monitoreados")
    st.dataframe(pd.DataFrame(clientes))

with col2:
    st.markdown("### 📄 Últimas Licitaciones Detectadas")
    st.dataframe(pd.DataFrame(licitaciones))

st.divider()

# 4. Botón de ejecución del cruce inteligente
st.markdown("### 🚀 Motor de Coincidencias e Alertas")
if st.button("Ejecutar Cruce y Simular Envío de Alertas", type="primary"):
    st.info("Procesando algoritmos de coincidencia...")
    
    alertas_enviadas = 0
    
    for c in clientes:
        licitaciones_vaildas = []
        for l in licitaciones:
            # Cruzar palabras clave normalizadas
            titulo_norm = normalizar(l["titulo"])
            for kw in c["keywords"]:
                if normalizar(kw) in titulo_norm:
                    if l not in licitaciones_vaildas:
                        licitaciones_vaildas.append(l)
        
        # Si el cliente tiene oportunidades, simular correo
        if licitaciones_vaildas:
            alertas_enviadas += 1
            with st.expander(f"✉️ Alerta generada para: {c['nombre']} ({c['correo']})", expanded=True):
                st.success(f"¡Coincidencia encontrada! Enviando resumen premium a {c['correo']}...")
                for opon in licitaciones_vaildas:
                    st.write(f"• **[{opon['portal']}]** {opon['titulo']} | Dependencia: {opon['dependencia']} (ID: {opon['id']})")
    
    st.balloons()
    st.success(f"¡Proceso terminado con éxito! Se simularon {alertas_enviadas} notificaciones premium.")
