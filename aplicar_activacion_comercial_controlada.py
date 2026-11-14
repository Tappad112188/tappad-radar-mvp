"""Aplicacion comercial controlada: apagada por defecto.

Solo invocar desde un worker privado, nunca desde HTTP publico ni navegador.
La evidencia se obtiene del proveedor EN ESTA MISMA ejecucion.
"""
import json
import os
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from conexion_segura_mercadopago_supabase import verificar_pago_desde_supabase
from verificar_pago_mercadopago_servidor import VerificacionRechazada


def ejecutar_activacion_controlada(pago_id, *, supabase_url, supabase_key,
                                  mercadopago_token, inicio, fin,
                                  habilitar=False, db_opener=urlopen,
                                  mp_opener=urlopen, rpc_opener=urlopen):
    """El indicador habilitar no sustituye autorizacion del operador.

    En modo normal solo verifica, sin escribir. Requiere habilitar=True Y
    TAPPAD_HABILITAR_ACTIVACION_PRODUCCION=SI para llamar al RPC.
    """
    resultado = verificar_pago_desde_supabase(
        pago_id, supabase_url=supabase_url, supabase_key=supabase_key,
        mercadopago_token=mercadopago_token,
        db_opener=db_opener, mp_opener=mp_opener)
    if not habilitar or os.environ.get("TAPPAD_HABILITAR_ACTIVACION_PRODUCCION") != "SI":
        return dict(resultado, aplicacion="simulada_sin_escrituras")
    if not isinstance(inicio, str) or not isinstance(fin, str):
        raise VerificacionRechazada("periodo_no_valido")
    if not supabase_url.startswith("https://") or not supabase_url.rstrip("/").endswith(".supabase.co"):
        raise VerificacionRechazada("supabase_url_invalida")
    payload = {
        "p_cliente": resultado["cliente_id"],
        "p_suscripcion": resultado["suscripcion_id"],
        "p_pago": resultado["pago_id"],
        "p_inicio": inicio,
        "p_fin": fin,
        "p_evidencia": resultado["evidencia"],
    }
    request = Request(
        supabase_url.rstrip("/") + "/rest/v1/rpc/tappad_aplicar_activacion_comercial",
        data=json.dumps(payload).encode("utf-8"),
        headers={"apikey": supabase_key,
                 "Authorization": "Bearer " + supabase_key,
                 "Content-Type": "application/json"},
        method="POST")
    try:
        with rpc_opener(request, timeout=15) as response:
            if response.status not in (200, 201):
                raise VerificacionRechazada("rpc_no_exitosa")
            applied = json.loads(response.read(4096))
    except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
        raise VerificacionRechazada("rpc_fallida") from exc
    if applied is not True:
        raise VerificacionRechazada("activacion_rechazada_por_base")
    return dict(resultado, aplicacion="aplicada")


if __name__ == "__main__":
    raise SystemExit("No exponer como endpoint publico.")
