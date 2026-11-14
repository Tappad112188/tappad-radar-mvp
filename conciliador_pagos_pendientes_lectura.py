"""Auditoria comercial automatizable, estrictamente de solo lectura.

No activa suscripciones, no modifica pagos y no ejecuta cobros.
Solo procesa pagos locales de Mercado Pago produccion.
"""
import json
import os
from datetime import datetime, timezone
from urllib.request import urlopen
from conexion_segura_mercadopago_supabase import verificar_pago_desde_supabase, _filas
from verificar_pago_mercadopago_servidor import VerificacionRechazada


def pendientes(*, supabase_url, supabase_key, opener=urlopen):
    from urllib.parse import urlencode
    from urllib.request import Request
    base = supabase_url.rstrip("/")
    if not base.startswith("https://") or not base.endswith(".supabase.co"):
        raise VerificacionRechazada("supabase_url_invalida")
    if not supabase_key:
        raise VerificacionRechazada("supabase_clave_ausente")
    params = urlencode({"select":"id,estado,proveedor_cobro",
                        "proveedor_cobro":"eq.mercadopago_produccion",
                        "estado":"eq.pagado","order":"id.asc","limit":"1000"})
    req = Request(base+"/rest/v1/pagos_tappad?"+params,
                  headers={"apikey":supabase_key,"Authorization":"Bearer "+supabase_key})
    with opener(req, timeout=20) as response:
        filas = json.loads(response.read(524288))
    if not isinstance(filas,list) or len(filas)>=1000:
        raise VerificacionRechazada("paginacion_pendiente")
    return [int(f["id"]) for f in filas]


def auditar(*, supabase_url, supabase_key, mercadopago_token, opener=urlopen):
    ids=pendientes(supabase_url=supabase_url,supabase_key=supabase_key,opener=opener)
    resultados=[]
    for pid in ids:
        try:
            verificacion=verificar_pago_desde_supabase(
                pid,supabase_url=supabase_url,supabase_key=supabase_key,
                mercadopago_token=mercadopago_token)
            resultados.append({"pago_id":pid,"resultado":"verificado_sin_activar",
                               "cliente_id":verificacion["cliente_id"]})
        except VerificacionRechazada as exc:
            resultados.append({"pago_id":pid,"resultado":"bloqueado","motivo":str(exc)})
    return {"modo":"SOLO_LECTURA","fecha":datetime.now(timezone.utc).isoformat(),
            "pagos_revisados":len(ids),"resultados":resultados}


if __name__=="__main__":
    requeridos=("TAPPAD_SUPABASE_URL","TAPPAD_SUPABASE_SERVICE_ROLE_KEY",
                "TAPPAD_MERCADOPAGO_PROD_ACCESS_TOKEN")
    faltantes=[v for v in requeridos if not os.getenv(v)]
    if faltantes: raise SystemExit("Configuracion incompleta: "+", ".join(faltantes))
    reporte=auditar(supabase_url=os.environ[requeridos[0]],
                   supabase_key=os.environ[requeridos[1]],
                   mercadopago_token=os.environ[requeridos[2]])
    print(json.dumps(reporte,ensure_ascii=False))
