"""Evaluador puro de conciliacion Mercado Pago: nunca realiza cobros ni escrituras.

Recibe evidencia obtenida por un servidor confiable desde la API del proveedor.
No confia en datos de webhook, navegador o fecha del siguiente cobro por si solos.
"""
from datetime import datetime
from decimal import Decimal, InvalidOperation


def _fecha(valor):
    if not isinstance(valor, str):
        return None
    try:
        fecha = datetime.fromisoformat(valor.replace("Z", "+00:00"))
        return fecha if fecha.tzinfo is not None else None
    except ValueError:
        return None


def _importe(valor):
    try:
        n = Decimal(str(valor))
        return n if n.is_finite() else None
    except (InvalidOperation, ValueError, TypeError):
        return None


def evaluar_pago_comercial(suscripcion, pago_local, pago_proveedor, *,
                           ahora, importe_esperado, moneda="MXN"):
    """Devuelve (admisible, motivo), sin mutar los objetos de entrada.

    El llamador debe verificar la respuesta del proveedor mediante credenciales
    privadas y comprobar el ownership de la suscripcion antes de invocar.
    """
    if ahora.tzinfo is None:
        return False, "reloj_sin_zona"
    if not all(isinstance(x, dict) for x in
               (suscripcion, pago_local, pago_proveedor)):
        return False, "evidencia_incompleta"
    proveedor = str(suscripcion.get("proveedor_cobro") or "").casefold()
    if proveedor != "mercadopago_produccion":
        return False, "proveedor_no_comercial"
    if str(pago_local.get("proveedor_cobro") or "").casefold() != proveedor:
        return False, "proveedor_inconsistente"
    if str(pago_local.get("suscripcion_id")) != str(suscripcion.get("id")):
        return False, "suscripcion_inconsistente"
    if str(pago_local.get("estado")) != "pagado":
        return False, "pago_local_no_conciliado"
    if (_importe(pago_local.get("monto_mxn")) is None or
        _importe(pago_local["monto_mxn"]) != _importe(importe_esperado)):
        return False, "importe_local_incorrecto"
    if not str(suscripcion.get("referencia_externa") or "").strip():
        return False, "referencia_suscripcion_ausente"
    referencia = str(pago_local.get("referencia_externa") or "").strip()
    if not referencia or referencia != str(pago_proveedor.get("id") or "").strip():
        return False, "referencia_no_verificada"
    if pago_proveedor.get("status") != "approved":
        return False, "pago_no_aprobado"
    if str(pago_proveedor.get("currency_id") or "").upper() != moneda:
        return False, "moneda_incorrecta"
    if (_importe(pago_proveedor.get("transaction_amount")) is None or
        _importe(importe_esperado) is None or
        _importe(pago_proveedor["transaction_amount"]) != _importe(importe_esperado)):
        return False, "importe_incorrecto"
    fecha_pago = _fecha(pago_proveedor.get("date_approved"))
    if fecha_pago is None or fecha_pago > ahora:
        return False, "fecha_pago_invalida"
    fecha_local = _fecha(pago_local.get("fecha_pago"))
    if fecha_local is None or fecha_local > ahora:
        return False, "fecha_local_invalida"
    if not str(pago_proveedor.get("preapproval_id") or "").strip():
        return False, "suscripcion_remota_ausente"
    if str(pago_proveedor["preapproval_id"]) != str(suscripcion.get("referencia_externa") or ""):
        return False, "suscripcion_remota_inconsistente"
    return True, "evidencia_consistente_pendiente_aplicacion"
