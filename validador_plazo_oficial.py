"""Validación operativa de alertas según fecha del acto de apertura.

La fecha_apertura registrada en ComprasMX se utiliza como fecha límite de
presentación. Los datos sin fecha, vencidos o con estatus de cierre se bloquean.
No consulta fuentes externas ni envía correos.
"""
from datetime import date, datetime
from zoneinfo import ZoneInfo
from motor_coincidencias import normalizar

ZONA_OPERATIVA = ZoneInfo("America/Monterrey")
ESTATUS_CERRADOS = {"adjudicado", "cancelado", "desierto", "concluido", "finalizado"}


def _fecha_apertura(valor):
    if not valor:
        return None
    try:
        if isinstance(valor, datetime):
            fecha = valor
        elif isinstance(valor, date):
            fecha = datetime.combine(valor, datetime.min.time())
        else:
            fecha = datetime.fromisoformat(str(valor).strip().replace("Z", "+00:00"))
        return fecha.replace(tzinfo=ZONA_OPERATIVA) if fecha.tzinfo is None else fecha.astimezone(ZONA_OPERATIVA)
    except (ValueError, TypeError, OverflowError):
        return None


def validar_envio_oportunidad(oportunidad, verificacion=None, ahora=None):
    """Autoriza por apertura futura y estatus activo, nunca por una fecha ausente.

    'verificacion' se conserva como argumento opcional por compatibilidad.
    El campo fecha_apertura proviene del expediente almacenado.
    """
    if oportunidad.get("categoria_alerta") != "candidata_revision":
        return {"autorizada": False, "motivo": "La oportunidad no es candidata a revisión"}
    estatus = normalizar(oportunidad.get("estatus"))
    if estatus in ESTATUS_CERRADOS:
        return {"autorizada": False, "motivo": "Estatus del procedimiento: " + estatus}
    if estatus not in {"vigente", "en aclaraciones"}:
        return {"autorizada": False, "motivo": "Estatus no confirmado como activo"}
    apertura = _fecha_apertura(oportunidad.get("fecha_apertura"))
    if apertura is None:
        return {"autorizada": False, "motivo": "Falta fecha válida de apertura de propuestas"}
    ahora = ahora or datetime.now(ZONA_OPERATIVA)
    if ahora.tzinfo is None:
        ahora = ahora.replace(tzinfo=ZONA_OPERATIVA)
    else:
        ahora = ahora.astimezone(ZONA_OPERATIVA)
    if apertura <= ahora:
        return {"autorizada": False, "motivo": "Ya transcurrió la fecha límite de presentación (apertura)"}
    return {"autorizada": True, "motivo": "Fecha de apertura futura y estatus activo; sujeto a control de duplicados"}
