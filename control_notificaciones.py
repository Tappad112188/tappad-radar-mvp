"""Filtrado de duplicados previo al envío de alertas.

El historial es privado y lo consulta exclusivamente el servicio administrativo.
No escribe en Supabase ni envía correos.
"""


def separar_notificaciones(candidatas, historial):
    """Separa novedades de pares proveedor/licitación ya registrados.

    Los estados pendiente y enviado se retienen para evitar duplicados.
    El estado error se reserva para un flujo de reintentos controlado.
    """
    registros = {
        (r["cliente_id"], r["licitacion_id"]): r["estado"]
        for r in historial
    }
    nuevas, retenidas, reintentos = [], [], []
    vistos = set()
    for candidata in candidatas:
        clave = (candidata["cliente_id"], candidata["licitacion_id"])
        if clave in vistos:
            continue
        vistos.add(clave)
        estado = registros.get(clave)
        if estado is None:
            nuevas.append(candidata)
        elif estado == "error":
            reintentos.append(candidata)
        else:
            retenidas.append(candidata)
    return {"nuevas": nuevas, "retenidas": retenidas, "reintentos": reintentos}


def autorizar_envio_real(configuracion, oportunidad, estado_previo=None, ahora=None):
    """Compuerta final fail-closed; debe llamarse antes de cualquier SMTP real.

    configuracion: mapa clave->valor obtenido de configuracion_operativa_tappad.
    No envia correo ni modifica registros.
    """
    if str(configuracion.get("alertas_automaticas_habilitadas", "false")).strip().lower() != "true":
        return False, "alertas_automaticas_desactivadas"
    if estado_previo is not None:
        return False, "notificacion_existente_requiere_revision"
    from validador_plazo_oficial import _fecha_apertura, ZONA_OPERATIVA
    from datetime import datetime
    if str(oportunidad.get("estatus") or "").strip().casefold() not in ("vigente", "en aclaraciones"):
        return False, "estatus_no_vigente"
    apertura = _fecha_apertura(oportunidad.get("fecha_apertura"))
    if apertura is None:
        return False, "fecha_apertura_no_verificada"
    ahora = ahora or datetime.now(ZONA_OPERATIVA)
    if ahora.tzinfo is None:
        ahora = ahora.replace(tzinfo=ZONA_OPERATIVA)
    if apertura <= ahora.astimezone(ZONA_OPERATIVA):
        return False, "plazo_vencido"
    return True, "apto_para_revision_previa_al_envio"
