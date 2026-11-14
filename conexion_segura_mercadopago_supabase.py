"""Orquestador de verificacion remota: solo lectura y fallo cerrado.

Ejecutar unicamente en backend con secretos privados:
SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, MERCADOPAGO_PROD_ACCESS_TOKEN.
No acepta IDs de clientes desde una solicitud publica ni aplica activaciones.
"""
import json
import os
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from datetime import datetime, timezone

from verificar_pago_mercadopago_servidor import (
    verificar_pago_servidor, VerificacionRechazada)


def _filas(url, key, tabla, filtros, *, opener=urlopen):
    base = url.rstrip("/")
    if not base.startswith("https://") or not base.endswith(".supabase.co"):
        raise VerificacionRechazada("supabase_url_invalida")
    if not key:
        raise VerificacionRechazada("supabase_clave_ausente")
    query = urlencode(filtros)
    req = Request(base + "/rest/v1/" + tabla + "?" + query,
                  headers={"apikey": key, "Authorization": "Bearer " + key,
                           "Accept": "application/json"}, method="GET")
    try:
        with opener(req, timeout=15) as resp:
            if resp.status != 200:
                raise VerificacionRechazada("supabase_respuesta_invalida")
            rows = json.loads(resp.read(262145))
    except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
        raise VerificacionRechazada("supabase_consulta_fallida") from exc
    if not isinstance(rows, list) or len(rows) != 1:
        raise VerificacionRechazada("registro_no_unico_o_ausente")
    return rows[0]


def verificar_pago_desde_supabase(pago_id, *, supabase_url, supabase_key,
                                 mercadopago_token, db_opener=urlopen,
                                 mp_opener=urlopen, ahora=None):
    """Devuelve evidencia sin activar; solo el servidor elige pago_id."""
    if not isinstance(pago_id, int) or isinstance(pago_id, bool) or pago_id <= 0:
        raise VerificacionRechazada("pago_id_invalido")
    pago = _filas(supabase_url, supabase_key, "pagos_tappad",
                  {"select": "id,suscripcion_id,monto_mxn,estado,proveedor_cobro,referencia_externa,fecha_pago",
                   "id": "eq." + str(pago_id)}, opener=db_opener)
    if pago.get("proveedor_cobro") != "mercadopago_produccion":
        raise VerificacionRechazada("pago_no_productivo")
    sub = _filas(supabase_url, supabase_key, "suscripciones_tappad",
                {"select": "id,cliente_id,plan_id,estado,proveedor_cobro,referencia_externa",
                 "id": "eq." + str(pago["suscripcion_id"])}, opener=db_opener)
    if sub.get("estado") not in ("pendiente", "activa"):
        raise VerificacionRechazada("suscripcion_no_admisible")
    plan = _filas(supabase_url, supabase_key, "planes_tappad",
                 {"select": "id,precio_mxn,activo,periodicidad",
                  "id": "eq." + str(sub["plan_id"])}, opener=db_opener)
    if plan.get("activo") is not True:
        raise VerificacionRechazada("plan_inactivo")
    evidencia = verificar_pago_servidor(
        sub, pago, importe_esperado=plan["precio_mxn"],
        token=mercadopago_token, ahora=ahora or datetime.now(timezone.utc),
        opener=mp_opener)
    return {"cliente_id": sub["cliente_id"], "suscripcion_id": sub["id"],
            "pago_id": pago["id"], "evidencia": evidencia,
            "aplicacion": "bloqueada_hasta_rpc_autorizada"}


if __name__ == "__main__":
    raise SystemExit(
        "Modulo servidor de solo lectura. No ejecutar como endpoint publico.")
