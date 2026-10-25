"""TAPPAD Radar: plan de envio en seco, sin SMTP ni cambios en Supabase.
Reutiliza los borradores generados por diagnosticar_vigencia_v4.py.
No habilita envio real.
"""
import json
import re
from collections import Counter
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from diagnosticar_vigencia_v4 import consulta
from compuerta_alertas_v3 import evaluar

BASE=Path(__file__).resolve().parent
VISTA=BASE/"vista_previa_alertas_tappad_v7.txt"
SALIDA=BASE/"plan_envios_seco_tappad.json"

def main():
    if not VISTA.exists():
        raise SystemExit("Falta vista previa; ejecutar diagnostico primero.")
    clientes=consulta("clientes","id,empresa,correo,activo",{"activo":"eq.true"})
    licitaciones=consulta("licitaciones","id,numero_procedimiento,fecha_apertura,estatus")
    registros=consulta("notificaciones_enviadas","cliente_id,licitacion_id,estado")
    por_nombre={}
    for c in clientes:
        clave=str(c["empresa"]).strip().casefold()
        if clave in por_nombre: raise SystemExit("Nombre de proveedor duplicado: imposible asociar borrador")
        por_nombre[clave]=c
    por_numero={}
    for l in licitaciones:
        clave=str(l.get("numero_procedimiento") or "").strip()
        if clave:
            por_numero.setdefault(clave,[]).append(l)
    enviados={(r["cliente_id"],r["licitacion_id"]) for r in registros if r["estado"]=="enviado"}
    bloqueados={(r["cliente_id"],r["licitacion_id"]) for r in registros if r["estado"]!="enviado"}
    bloques=re.split(r"\n={20,}\n",VISTA.read_text(encoding="utf-8"))
    ahora=datetime.now(ZoneInfo("America/Monterrey")).replace(tzinfo=None)
    plan=[]
    for bloque in bloques:
        encabezado=re.search(r"^TAPPAD Radar \| Vista previa para (.+)$",bloque,re.M)
        if not encabezado: continue
        nombre=encabezado.group(1).strip()
        c=por_nombre.get(nombre.casefold())
        if not c: raise SystemExit("Proveedor del borrador no encontrado en clientes activos")
        numeros=re.findall(r"^Procedimiento: (.+)$",bloque,re.M)
        ids=[]
        for numero in numeros:
            encontrados=por_numero.get(numero.strip(),[])
            if len(encontrados)!=1: raise SystemExit("Numero de procedimiento ambiguo o ausente: "+numero)
            l=encontrados[0]
            par=(c["id"],l["id"])
            if par in bloqueados: raise SystemExit("Notificacion previa pendiente/error: requiere conciliacion manual")
            ok,motivo=evaluar(l,c["id"],enviados,ahora)
            if not ok: raise SystemExit("Bloqueo en preflight: "+motivo+" | "+numero)
            if l["id"] in ids: raise SystemExit("Procedimiento repetido dentro del mismo correo")
            ids.append(l["id"])
        if not ids: raise SystemExit("Borrador sin oportunidades")
        plan.append({"cliente_id":c["id"],"licitacion_ids":ids,"cantidad":len(ids),"correo_configurado":bool(str(c.get("correo") or "").strip())})
    if len(plan)!=len([b for b in bloques if re.search(r"^TAPPAD Radar \| Vista previa para ",b,re.M)]):
        raise SystemExit("Cantidad de borradores inconsistente")
    SALIDA.write_text(json.dumps({"modo":"SIMULACION_SIN_ENVIO","generado_en":datetime.now(ZoneInfo("America/Monterrey")).isoformat(),"proveedores":plan},ensure_ascii=False,indent=2),encoding="utf-8")
    print("SIMULACION VALIDADA | Proveedores:",len(plan),"| Oportunidades:",sum(p["cantidad"] for p in plan))
    print("Sin SMTP, sin envios, sin escrituras en Supabase. Plan:",SALIDA.name)

if __name__=="__main__":
    main()
