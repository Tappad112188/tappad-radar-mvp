import hmac

import pandas as pd
import streamlit as st
from supabase import create_client

st.set_page_config(page_title="TAPPAD Radar", page_icon="📡", layout="wide")


def conectar_supabase():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])


def conectar_supabase_admin():
    # Solo se llama después de comprobar la contraseña administrativa.
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_ADMIN_KEY"])


st.title("📡 TAPPAD Radar")
st.subheader("Sistema de monitoreo de oportunidades en licitaciones públicas")
st.info("Versión MVP. Se muestran expedientes reales almacenados en TAPPAD Radar; la actualización automática aún está en desarrollo.")
st.divider()

menu = st.sidebar.radio("Menú principal", ["Explorar licitaciones", "Registrar empresa", "Panel administrativo"])

if menu == "Explorar licitaciones":
    st.header("Oportunidades de contratación")
    st.caption("Fuente: registros guardados en Supabase. Algunos expedientes pueden estar concluidos.")
    busqueda = st.text_input("Buscar por palabra clave").strip()

    try:
        # Consulta exclusivamente del lado del servidor: la clave administrativa
        # permanece en Streamlit Secrets y nunca se envía al navegador.
        supabase_admin = conectar_supabase_admin()
        respuesta = (
            supabase_admin.table("licitaciones")
            .select("numero_procedimiento,nombre_procedimiento,descripcion,nombre_dependencia,"
                    "tipo_procedimiento,estatus,entidad_federativa,fecha_publicacion,"
                    "fecha_apertura,fecha_fallo,fuente,url_procedimiento")
            .order("fecha_publicacion", desc=True)
            .limit(1000)
            .execute()
        )
        licitaciones = respuesta.data or []
        df = pd.DataFrame(licitaciones)
        if df.empty:
            st.info("Aún no hay licitaciones almacenadas.")
        else:
            if busqueda:
                columnas_busqueda = [
                    "numero_procedimiento", "nombre_procedimiento", "descripcion",
                    "nombre_dependencia", "tipo_procedimiento", "entidad_federativa"
                ]
                filtro = pd.Series(False, index=df.index)
                for columna in columnas_busqueda:
                    filtro = filtro | df[columna].fillna("").astype(str).str.contains(
                        busqueda, case=False, na=False, regex=False
                    )
                df = df.loc[filtro]

            st.metric("Licitaciones encontradas", len(df))
            if df.empty:
                st.info("No se encontraron procedimientos con esa palabra clave.")
            else:
                columnas = {
                    "numero_procedimiento": "Procedimiento",
                    "nombre_procedimiento": "Nombre",
                    "descripcion": "Descripción",
                    "nombre_dependencia": "Dependencia",
                    "tipo_procedimiento": "Tipo",
                    "estatus": "Estado",
                    "entidad_federativa": "Entidad",
                    "fecha_publicacion": "Publicación",
                    "fecha_apertura": "Apertura",
                    "fecha_fallo": "Fallo programado",
                    "fuente": "Fuente",
                    "url_procedimiento": "Expediente",
                }
                st.dataframe(
                    df[list(columnas)].rename(columns=columnas),
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Expediente": st.column_config.LinkColumn(
                            "Expediente", display_text="Abrir en ComprasMX"
                        )
                    },
                )
            st.caption("Se consultan hasta 1,000 expedientes, ordenados por publicación. Las fechas provienen de ComprasMX.")
    except KeyError:
        st.error("Falta configurar SUPABASE_URL o SUPABASE_ADMIN_KEY en Streamlit Secrets.")
    except Exception as e:
    st.error("No fue posible consultar las licitaciones.")
    st.error(f"Tipo de error: {type(e).__name__}")

    st.caption("Próximamente: actualización automática de ComprasMX y SECOP Coahuila.")

elif menu == "Registrar empresa":
    st.header("Registro de empresas")
    st.write("Registra tu empresa para recibir información sobre oportunidades de contratación pública.")
    with st.form("formulario_registro"):
        nombre = st.text_input("Nombre de la empresa")
        correo = st.text_input("Correo electrónico")
        palabras = st.text_area("Productos o servicios de interés", placeholder="Ejemplo: limpieza, papelería, mantenimiento")
        enviar = st.form_submit_button("Registrar empresa")

    if enviar:
        if not nombre.strip():
            st.warning("Ingresa el nombre de la empresa.")
        elif not correo.strip():
            st.warning("Ingresa un correo electrónico.")
        elif not palabras.strip():
            st.warning("Ingresa los productos o servicios de interés.")
        else:
            try:
                supabase = conectar_supabase()
                supabase.table("clientes").insert(
                    {"empresa": nombre.strip(), "correo": correo.strip().lower(), "palabras_clave": palabras.strip()},
                    returning="minimal",
                ).execute()
                st.success("¡Registro guardado correctamente!")
                st.info("Tu empresa ha sido registrada en TAPPAD Radar.")
            except Exception:
                st.error("No fue posible guardar el registro. Inténtalo de nuevo o contacta a TAPPAD Consultoría.")

elif menu == "Panel administrativo":
    st.header("Panel administrativo")
    st.write("Acceso exclusivo para TAPPAD Consultoría.")

    if "admin_autorizado" not in st.session_state:
        st.session_state.admin_autorizado = False

    if not st.session_state.admin_autorizado:
        with st.form("acceso_admin"):
            clave = st.text_input("Contraseña de administrador", type="password")
            ingresar = st.form_submit_button("Ingresar")
        if ingresar:
            try:
                esperada = str(st.secrets["admin_password"])
                if clave and hmac.compare_digest(clave, esperada):
                    st.session_state.admin_autorizado = True
                    st.rerun()
                else:
                    st.error("Contraseña incorrecta.")
            except KeyError:
                st.error("Falta configurar admin_password en Streamlit Secrets.")
    else:
        if st.button("Cerrar sesión administrativa"):
            st.session_state.admin_autorizado = False
            st.rerun()

        st.subheader("Clientes registrados")
        if st.button("Actualizar listado"):
            st.rerun()

        try:
            supabase_admin = conectar_supabase_admin()
            respuesta = (
                supabase_admin.table("clientes")
                .select("id,empresa,correo,palabras_clave,activo,fecha_registro")
                .order("fecha_registro", desc=True)
                .limit(1000)
                .execute()
            )
            clientes = respuesta.data or []
            st.metric("Clientes mostrados", len(clientes))
            if clientes:
                datos = pd.DataFrame(clientes)
                datos = datos.rename(columns={
                    "id": "ID", "empresa": "Empresa", "correo": "Correo",
                    "palabras_clave": "Palabras clave", "activo": "Activo",
                    "fecha_registro": "Fecha de registro",
                })
                st.dataframe(datos, use_container_width=True, hide_index=True)
                st.caption("Se muestran hasta 1,000 registros. Este panel es solo de consulta.")
            else:
                st.info("Todavía no hay empresas registradas.")
        except KeyError:
            st.error("Falta configurar SUPABASE_ADMIN_KEY o SUPABASE_URL en Streamlit Secrets.")
        
        except Exception as error:
            st.error("No fue posible consultar los clientes. Revisa la clave administrativa y los permisos de Supabase.")
            st.caption(f"Detalle técnico: {error}")


st.divider()
st.caption("TAPPAD Radar | Desarrollado por TAPPAD Consultoría")
