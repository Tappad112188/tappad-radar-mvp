"""Politica conservadora de ciclos de cobro. Pura, sin IO ni activaciones.

No se concede acceso por evidencia de un webhook ni por next_payment_date.
Los casos pendientes requieren reconciliacion; no se descartan pagos.
"""
from datetime import timedelta


def evaluar_inicio_ciclo(*, fecha_pago, vencimiento, ahora):
    """Retorna (decision, inicio). Solo 'aplicar' permite invocar SQL.

    'pendiente_anticipada' y 'revision_tardia' conservan el pago pendiente
    para una reconciliacion posterior, sin ampliar acceso por suposicion.
    """
    if any(x is None or x.tzinfo is None or x.utcoffset() is None
           for x in (fecha_pago, ahora)):
        return "fecha_invalida", None
    if vencimiento is not None and (
        vencimiento.tzinfo is None or vencimiento.utcoffset() is None
    ):
        return "fecha_invalida", None
    if fecha_pago > ahora:
        return "fecha_futura", None
    if fecha_pago < ahora - timedelta(days=7):
        return "revision_tardia", None
    inicio = vencimiento if vencimiento is not None else fecha_pago
    if inicio > ahora:
        return "pendiente_anticipada", None
    return "aplicar", inicio
