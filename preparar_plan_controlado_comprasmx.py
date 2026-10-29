"""Genera plan de prueba ComprasMX con coincidencias reales, sin envios ni escrituras."""
import json
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from diagnosticar_vigencia_v4 import consulta, norm, contiene, RUBROS, GENERICAS, estado_equivalente, objeto_principal
from compuerta_alertas_v3 import evaluar

BASE=Path(__file__).resolve().parent
CLIENTES_PRUEBA={1:"gerardotapia112188@gmail.com",4:"tappadcons@gmail.com"}

def preparar():
    clientes=consulta("clientes","id,empresa,correo,activo,palabras_clave",{"activo":"eq.true"})
    giros=consulta("clientes_giros","cliente_id,giro_id")
    ubicaciones=consulta("clientes_ubicaciones","cliente_id,estado,municipio")
    licitaciones=consulta("licitaciones","id,numero_procedimiento,nombre_procedimiento,descripcion,fuente,entidad_federativa,estatus,fecha_apertura")
    historial=consulta("notificaciones_enviadas","cliente_id,licitacion_id,estado")
    ocupados={(r["cliente_id"],r["licitacion_id"]) for r in historial}
    gs={cid:set() for cid in CLIENTES_PRUEBA}
    us={cid:[] for cid in CLIENTES_PRUEBA}
    for g in giros:
        if g["cliente_id"] in gs:gs[g["cliente_id"]].add(g["giro_id"])
    for u in ubicaciones:
        if u["cliente_id"] in us:us[u["cliente_id"]].append(u)
    ahora=datetime.now(ZoneInfo("America/Monterrey")).replace(tzinfo=None)
    plan=[]
    for c in clientes:
        cid=c["id"]
        if cid not in CLIENTES_PRUEBA:continue
        if str(c.get("correo") or "").strip().casefold()!=CLIENTES_PRUEBA[cid]:
            raise SystemExit("Correo de prueba no coincide con lista permitida: "+str(cid))
        import re
        claves=[norm(x.strip()) for x in re.split(r"[,;\\n]",c.get("palabras_clave") or "") if len(x.strip())>=4] 
        ids=[]
        for l in licitaciones:
            if str(l.get("fuente") or "").strip().casefold()!="comprasmx":continue
            if (cid,l["id"]) in ocupados:continue
            ok,_=evaluar(l,cid,ocupados,ahora)
            if not ok:continue
            u=us[cid]
            entidad=norm(l.get("entidad_federativa"))
            if u and (not entidad or not any(estado_equivalente(x.get("estado"),entidad) for x in u)):continue
            texto=norm((l.get("nombre_procedimiento") or "")+" "+(l.get("descripcion") or ""))
            rubros=[g for g in gs[cid] if any(contiene(texto,k) for k in RUBROS.get(g,()))]
            objeto=objeto_principal(l)
            if objeto is not None:
                if gs[cid] and objeto not in gs[cid]:continue
                rubros=[g for g in rubros if g==objeto]
            if gs[cid] and not rubros:continue
            fuertes=[k for k in claves if k not in GENERICAS]
            palabras=[k for k in fuertes if contiene(texto,k)]
            if fuertes and not palabras and not rubros:continue
            if not rubros and not palabras:continue
            ids.append(l["id"])
        if ids:plan.append({"cliente_id":cid,"licitacion_ids":ids})
    for cid in CLIENTES_PRUEBA:
        print("CLIENTE",cid,"coincidencias nuevas:",next((len(p["licitacion_ids"]) for p in plan if p["cliente_id"]==cid),0))
    if not plan:
        raise SystemExit("Sin coincidencias nuevas; no se crea plan.")
    ruta=BASE/"plan_envios_seco_tappad.json"
    ruta.write_text(json.dumps({"modo":"SIMULACION_SIN_ENVIO","proveedores":plan},indent=2),encoding="utf-8")
    print("PLAN CONTROLADO:",[(p["cliente_id"],len(p["licitacion_ids"])) for p in plan])
    print("SOLO LECTURA: sin correos y sin escrituras Supabase")

if __name__=="__main__":preparar()
