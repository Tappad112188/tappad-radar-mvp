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
