"""Panel de prueba SMTP: solo dos destinatarios, ejecución manual."""
import streamlit as st
from preparador_alertas import preparar_alertas, vista_previa_correo
from envio_gmail_pruebas import enviar_prueba_gmail, DESTINATARIOS_PRUEBA


def mostrar_envio_prueba(conectar):
    st.divider()
    st.subheader("Prueba real de Gmail")
    st.caption("Solo los dos proveedores de prueba. No habilita envíos automáticos.")
    if not st.checkbox("Autorizo enviar correos reales a los dos destinatarios de prueba.", key="autorizar_smtp"):
        return
    if not st.button("Enviar correos reales de prueba", key="enviar_smtp_controlado"):
        return
    try:
        usuario = st.secrets["GMAIL_USER"]
        clave = st.secrets["GMAIL_APP_PASSWORD"]
        db = conectar()
        proveedores = db.table("clientes").select("id,empresa,correo,palabras_clave,activo").in_("id", [1, 4]).eq("activo", True).execute().data or []
        coberturas = db.table("clientes_ubicaciones").select("cliente_id,estado,municipio").in_("cliente_id", [1, 4]).execute().data or []
        licitaciones = db.table("licitaciones").select("id,numero_procedimiento,nombre_procedimiento,descripcion,tipo_contratacion,entidad_federativa,fecha_apertura,estatus,url_procedimiento").limit(1000).execute().data or []
        historial = db.table("notificaciones_enviadas").select("cliente_id,licitacion_id,estado").execute().data or []
        ubicaciones = {}
        for item in coberturas:
            ubicaciones.setdefault(item["cliente_id"], []).append(item)
        grupos = preparar_alertas(proveedores, licitaciones, ubicaciones, historial)["por_proveedor"]
        for proveedor in proveedores:
            identificador = proveedor["id"]
            oportunidades = grupos.get(identificador, [])
            if not oportunidades:
                continue
            if proveedor["correo"].strip().lower() != DESTINATARIOS_PRUEBA.get(identificador):
                st.error("El destinatario registrado no coincide con el autorizado.")
                continue
            reservadas = []
            for oportunidad in oportunidades:
                try:
                    db.table("notificaciones_enviadas").insert({"cliente_id": identificador, "licitacion_id": oportunidad["licitacion_id"], "estado": "pendiente"}).execute()
                    reservadas.append(oportunidad)
                except Exception:
                    st.warning("Una oportunidad ya está reservada o no pudo registrarse.")
            if not reservadas:
                continue
            mensaje = vista_previa_correo(proveedor["empresa"], reservadas)
            try:
                enviar_prueba_gmail(identificador, proveedor["correo"], mensaje["asunto"], mensaje["cuerpo"], usuario, clave)
            except Exception as error:
                st.error("Error SMTP para " + proveedor["empresa"] + ": " + type(error).__name__)
                for oportunidad in reservadas:
                    db.table("notificaciones_enviadas").update({"estado": "error", "ultimo_error": type(error).__name__}).eq("cliente_id", identificador).eq("licitacion_id", oportunidad["licitacion_id"]).execute()
                continue
            from datetime import datetime, timezone
            for oportunidad in reservadas:
                db.table("notificaciones_enviadas").update({"estado": "enviado", "enviado_en": datetime.now(timezone.utc).isoformat(), "ultimo_error": None}).eq("cliente_id", identificador).eq("licitacion_id", oportunidad["licitacion_id"]).execute()
            st.success("Enviado a " + proveedor["empresa"] + ": " + str(len(reservadas)) + " oportunidades.")
        if not grupos:
            st.info("No hay oportunidades nuevas para enviar.")
    except KeyError:
        st.error("Faltan GMAIL_USER o GMAIL_APP_PASSWORD en Streamlit Secrets.")
    except Exception as error:
        st.error("No se completó la prueba: " + type(error).__name__)
