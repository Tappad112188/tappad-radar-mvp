"""Genera manifiesto compatible con motor_entrega_tappad_v2 sin enviar ni escribir Supabase."""
import hashlib
import json
from collections import defaultdict
from datetime import datetime,timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
from diagnosticar_vigencia_v4 import consulta
from preparador_alertas import preparar_alertas,filtrar_lote_para_envio_real
from plantilla_correo_html import construir_correo_html

ROOT=Path(__file__).resolve().parent
DEST=ROOT/"borradores_gmail_tappad_v3"
MANIFIESTO=ROOT/"manifiesto_notificaciones_tappad.json"

def construir():
    hoy=datetime.now(ZoneInfo("America/Monterrey")).date()
    desde=hoy-timedelta(days=2)
    clientes=consulta("clientes","id,empresa,correo,activo,palabras_clave",{"activo":"eq.true"})
    ubicaciones=consulta("clientes_ubicaciones","cliente_id,estado,municipio")
    giros=consulta("clientes_giros_preferencias_tappad","cliente_id,origen,clave,descripcion,activo",{"activo":"eq.true"})
    licitaciones=consulta("licitaciones","id,numero_procedimiento,nombre_procedimiento,descripcion,fuente,entidad_federativa,estatus,fecha_publicacion,fecha_apertura,fecha_junta_aclaraciones,fecha_fallo_programado,url_procedimiento,validacion_calendario")
    historial=consulta("notificaciones_enviadas","cliente_id,licitacion_id,estado")
    coberturas,preferencias=defaultdict(list),defaultdict(list)
    for item in ubicaciones: coberturas[item["cliente_id"]].append(item)
    for item in giros: preferencias[item["cliente_id"]].append(item)
    recientes=[l for l in licitaciones if str(l.get("fuente") or "").strip().casefold()=="comprasmx"
              and desde.isoformat()<=str(l.get("fecha_publicacion") or "")[:10]<=hoy.isoformat()]
    resultado=preparar_alertas(clientes,recientes,coberturas,historial,preferencias_por_cliente=preferencias)
    # La preparacion no autoriza SMTP: la compuerta final exige interruptor general.
    # Solo para construir borradores, se aplica una compuerta de vigencia simulando habilitacion.
    aprobadas=filtrar_lote_para_envio_real(resultado,recientes,historial,{"alertas_automaticas_habilitadas":"true"})
    por_id={l["id"]:l for l in recientes}
    por_cliente={c["id"]:c for c in clientes}
    lotes=[]
    DEST.mkdir(parents=True,exist_ok=True)
    for cid,oportunidades in sorted(aprobadas["por_proveedor"].items()):
        cliente=por_cliente[cid]
        ids=sorted({o["licitacion_id"] for o in oportunidades})
        if not ids: continue
        if not str(cliente.get("correo") or "").strip(): continue
        html=construir_correo_html(cliente["empresa"],[por_id[lid] for lid in ids])
        nombre=f"comprasmx_proveedor_{cid}.html"
        contenido=html.encode("utf-8")
        (DEST/nombre).write_bytes(contenido)
        lotes.append({"cliente_id":cid,"licitacion_ids":ids,"html":nombre,
                      "sha256_html":hashlib.sha256(contenido).hexdigest()})
    MANIFIESTO.write_text(json.dumps({"modo":"SOLO_PREPARACION","proveedores":lotes},
                                   ensure_ascii=False,indent=2),encoding="utf-8")
    print("MANIFIESTO PREPARADO:",len(lotes),"proveedores;",
          sum(len(l["licitacion_ids"]) for l in lotes),"oportunidades; sin SMTP ni escrituras Supabase.")
    print("BLOQUEADAS:",aprobadas["bloqueadas"])
    return lotes

if __name__=="__main__": construir()
