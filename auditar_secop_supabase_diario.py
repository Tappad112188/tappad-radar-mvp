"""Auditoria SECOP diario vs Supabase: solo lectura, sin correos ni escrituras."""
import json, os
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parent
EXTRACCION=ROOT/"secop_hoy_vigentes.json"
LOTE=ROOT/"documentos_secop_lote"/"secop_importacion_pendiente_revision.json"
REPORTE=ROOT/"documentos_secop_lote"/"auditoria_supabase_secop.json"

def main():
    hoy=datetime.now(ZoneInfo("America/Monterrey")).date().isoformat()
    fuente=json.loads(EXTRACCION.read_text(encoding="utf-8-sig"))
    if (fuente.get("fecha_consulta")!=hoy or not fuente.get("filtros_aplicados")
        or fuente.get("error") or fuente.get("errores") or fuente.get("coincide_total") is False):
        raise SystemExit("Extraccion SECOP no valida para el dia actual")
    registros=fuente.get("registros") or []
    if any(x.get("fecha_publicacion")!=hoy or str(x.get("estatus","")).casefold()!="vigente" for x in registros):
        raise SystemExit("SECOP: registro fuera de fecha o no vigente")
    if not registros:
        print("SECOP: 0 publicaciones vigentes hoy. Sin escrituras ni correos.")
        return
    lote=json.loads(LOTE.read_text(encoding="utf-8-sig"))
    if lote.get("estado")!="PENDIENTE_VALIDACION_OFICIAL_NO_IMPORTAR_AUTOMATICAMENTE":
        raise SystemExit("Estado inesperado del lote; detener auditoria")
    preparados=lote.get("registros") or []
    ids=[r.get("uuid_procedimiento") for r in preparados]
    codigos={str(r.get("codigo")).strip().casefold() for r in registros}
    if len(ids)!=len(set(ids)) or len(preparados)!=len(registros):
        raise SystemExit("Lote incompleto o duplicado")
    if any(str(r.get("cod_expediente")).strip().casefold() not in codigos
           or str(r.get("fuente"))!="SECOP Coahuila"
           or str(r.get("estatus","")).casefold()!="vigente"
           or str(r.get("fecha_publicacion",""))[:10]!=hoy
           for r in preparados):
        raise SystemExit("Lote SECOP no coincide con la extraccion de hoy")
    salida={"fecha_consulta":hoy,"total":len(ids),"estado":"SOLO_LECTURA",
            "importacion_habilitada":False,"notificaciones_habilitadas":False}
    url=os.getenv("SUPABASE_URL")
    key=os.getenv("SUPABASE_ADMIN_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if url and key:
        existentes=[]
        for uid in ids:
            params=urlencode({"select":"uuid_procedimiento","uuid_procedimiento":"eq."+uid})
            req=Request(url.rstrip("/")+"/rest/v1/licitaciones?"+params,
                        headers={"apikey":key,"Authorization":"Bearer "+key})
            with urlopen(req,timeout=25) as resp:
                encontrado=json.load(resp)
            if encontrado: existentes.append(uid)
        salida.update({"consulta_supabase":"realizada","existentes":existentes,
                       "nuevos":[uid for uid in ids if uid not in set(existentes)]})
    else:
        salida.update({"consulta_supabase":"no_realizada_faltan_variables",
                       "identificadores":ids})
    REPORTE.parent.mkdir(exist_ok=True)
    REPORTE.write_text(json.dumps(salida,ensure_ascii=False,indent=2),encoding="utf-8")
    print("SECOP hoy:",len(ids),"| Consulta Supabase:",salida["consulta_supabase"])
    if "nuevos" in salida:print("Existentes:",len(salida["existentes"]),"| Nuevos:",len(salida["nuevos"]))
    print("Reporte:",REPORTE)
    print("MODO SEGURO: sin escrituras Supabase ni correos")

if __name__=="__main__":
    main()
