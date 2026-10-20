"""Clasificación orientativa de licitaciones para TAPPAD Radar.

No sustituye la verificación del calendario oficial del procedimiento.
No modifica datos ni envía notificaciones.
"""
from datetime import datetime, date
from motor_coincidencias import normalizar


def _fecha(valor):
    if isinstance(valor, datetime):
        return valor
    if isinstance(valor, date):
        return datetime.combine(valor, datetime.min.time())
    if not valor:
        return None
    try:
        return datetime.fromisoformat(str(valor).replace("Z", "+00:00")).replace(tzinfo=None)
    except (ValueError, TypeError):
        return None


def clasificar_licitacion(licitacion, ahora=None):
    """Devuelve una categoría explicable sin afirmar que aún admite ofertas."""
    ahora = ahora or datetime.now()
    estatus = normalizar(licitacion.get("estatus"))
    apertura = _fecha(licitacion.get("fecha_apertura"))

    if estatus in {"adjudicado", "cancelado", "desierto", "concluido", "finalizado"}:
        return {"categoria": "concluida", "motivo": "Estatus oficial: " + estatus}

    if apertura is not None and apertura <= ahora:
        return {"categoria": "requiere_revision", "motivo": "La fecha de apertura ya transcurrió"}

    if estatus in {"vigente", "en aclaraciones"} and apertura is not None and apertura > ahora:
        return {"categoria": "potencialmente_abierta", "motivo": "Estatus activo y apertura futura; verificar plazo de presentación"}

    return {"categoria": "requiere_revision", "motivo": "Estatus o fecha insuficiente para confirmar vigencia"}
