"""Consulta verificable y de solo lectura de Mercado Pago (sin cobros ni escrituras).

No aceptar un ID de pago del navegador sin cotejarlo con una suscripcion
y un pago local cargados desde Supabase por un proceso servidor confiable.
"""
import json
import os
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from conciliacion_comercial_mercadopago import evaluar_pago_comercial


class VerificacionRechazada(Exception):
    pass


def _get_json(path, token, *, opener=urlopen):
    if not token or not token.strip():
        raise VerificacionRechazada("token_proveedor_ausente")
    if not path.startswith("/") or "?" in path or "#" in path:
        raise VerificacionRechazada("ruta_invalida")
    req = Request("https://api.mercadopago.com" + path,
                  headers={"Authorization": "Bearer " + token.strip(),
                           "Accept": "application/json"},
                  method="GET")
    try:
        with opener(req, timeout=15) as resp:
            if getattr(resp, "status", 200) != 200:
                raise VerificacionRechazada("respuesta_no_exitosa")
            data = json.loads(resp.read(262145))
    except (HTTPError, URLError, TimeoutError, ValueError, OSError) as exc:
        raise VerificacionRechazada("consulta_proveedor_fallida") from exc
    if not isinstance(data, dict):
        raise VerificacionRechazada("respuesta_invalida")
    return data


def verificar_pago_servidor(suscripcion, pago_local, *, importe_esperado,
                           token, ahora=None, opener=urlopen):
    """Solo evidencia de lectura; requiere token de PRODUCCION aislado.

    El llamador debe cargar suscripcion, pago y plan de la base con permisos
    servidor. Nunca confiar en esos objetos si provienen del navegador.
    """
    ahora = ahora or datetime.now(timezone.utc)
    if not isinstance(suscripcion, dict) or not isinstance(pago_local, dict):
        raise VerificacionRechazada("registros_invalidos")
    if suscripcion.get("proveedor_cobro") != "mercadopago_produccion":
        raise VerificacionRechazada("entorno_no_comercial")
    pid = str(pago_local.get("referencia_externa") or "").strip()
    sid = str(suscripcion.get("referencia_externa") or "").strip()
    if not pid or not sid or not pid.isascii() or not sid.isascii() or not all(
        x.isalnum() or x in "-_" for x in pid + sid
    ):
        raise VerificacionRechazada("identificadores_invalidos")
    vendedor = _get_json("/users/me", token, opener=opener)
    if vendedor.get("site_id") != "MLM" or "test_user" in (vendedor.get("tags") or []):
        raise VerificacionRechazada("vendedor_no_productivo_mexico")
    pre = _get_json("/preapproval/" + quote(sid, safe=""), token, opener=opener)
    ar = pre.get("auto_recurring") or {}
    if (str(pre.get("id")) != sid or pre.get("status") != "authorized"
        or str(ar.get("currency_id")) != "MXN"
        or str(ar.get("frequency_type")) != "months"
        or str(ar.get("frequency")) != "1"):
        raise VerificacionRechazada("suscripcion_remota_invalida")
    try:
        if Decimal(str(ar.get("transaction_amount"))) != Decimal(str(importe_esperado)):
            raise VerificacionRechazada("importe_suscripcion_invalido")
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise VerificacionRechazada("importe_suscripcion_invalido") from exc
    pago = _get_json("/v1/payments/" + quote(pid, safe=""), token, opener=opener)
    # El endpoint /v1/payments puede no incluir preapproval_id. No inferir
    # ownership: sin enlace verificable se rechaza, nunca se activa.
    if not pago.get("preapproval_id"):
        raise VerificacionRechazada("vinculo_pago_suscripcion_no_verificable")
    ok, motivo = evaluar_pago_comercial(
        suscripcion, pago_local, pago, ahora=ahora,
        importe_esperado=importe_esperado)
    if not ok:
        raise VerificacionRechazada(motivo)
    return {"verificacion_remota": "confirmada", "entorno": "produccion",
            "payment_id": pid, "preapproval_id": sid,
            "seller_id": str(vendedor.get("id") or ""),
            "fecha_verificacion": ahora.isoformat()}
