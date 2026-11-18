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
    ids = [int(f["id"]) for f in filas]
    if len(ids) != len(set(ids)) or any(i <= 0 for i in ids):
        raise VerificacionRechazada("pagos_duplicados_o_invalidos")
    if not ids:
        return []
    # Excluir pagos ya activados: una ejecucion recurrente no debe
    # intentar aplicar nuevamente el mismo cobro. Fallar cerrado si
    # la consulta de activaciones es incompleta.
    params_activaciones = urlencode({
        "select": "pago_id",
        "pago_id": "in.(" + ",".join(str(i) for i in ids) + ")",
        "order": "pago_id.asc",
        "limit": "1000",
    })
    req_activaciones = Request(
        base + "/rest/v1/activaciones_comerciales_tappad?" + params_activaciones,
        headers={"apikey":supabase_key,"Authorization":"Bearer "+supabase_key})
    with opener(req_activaciones, timeout=20) as response:
        activaciones = json.loads(response.read(524288))
    if not isinstance(activaciones, list) or len(activaciones) >= 1000:
        raise VerificacionRechazada("activaciones_incompletas")
    activados = set()
    for fila in activaciones:
        if not isinstance(fila, dict) or type(fila.get("pago_id")) is not int:
            raise VerificacionRechazada("activaciones_invalidas")
        if fila["pago_id"] not in ids:
            raise VerificacionRechazada("activaciones_inconsistentes")
        activados.add(fila["pago_id"])
    return [i for i in ids if i not in activados]


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
