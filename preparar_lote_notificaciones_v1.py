"""Prepara manifiesto verificable para envio futuro; sin SMTP ni escrituras.
Relaciona cada borrador con su proveedor por el encabezado original y su
posicion en el generador v3; verifica los identificadores del preflight.
"""
import hashlib
import json
import re
from pathlib import Path
from diagnosticar_vigencia_v4 import consulta

BASE=Path(__file__).resolve().parent
VISTA=BASE/"vista_previa_alertas_tappad_v7.txt"
PLAN=BASE/"plan_envios_seco_tappad.json"
CARPETA=BASE/"borradores_gmail_tappad_v3"
SALIDA=BASE/"manifiesto_notificaciones_tappad.json"

def main():
    if not PLAN.is_file():\n        raise SystemExit("Falta plan_envios_seco_tappad.json: generar primero con preparar_plan_controlado_comprasmx.py")\n    plan=json.loads(PLAN.read_text(encoding="utf-8"))
    if plan.get("modo")!="SIMULACION_SIN_ENVIO":
        raise SystemExit("El plan no es una simulacion autorizada")
    proveedores=plan["proveedores"]\n    if not proveedores: raise SystemExit("Plan sin coincidencias nuevas; no se enviara ningun correo")
    if len({p["cliente_id"] for p in proveedores})!=len(proveedores):
        raise SystemExit("Proveedores repetidos en plan")
    clientes=consulta("clientes","id,empresa,correo,activo",{"activo":"eq.true"})
    por_nombre={str(c["empresa"]).strip().casefold():c for c in clientes}
    bloques=re.split(r"\n={20,}\n",VISTA.read_text(encoding="utf-8"))
    lote=[]
    usados=set()
    for indice,bloque in enumerate(bloques,1):
        m=re.search(r"^TAPPAD Radar \| Vista previa para (.+)$",bloque,re.M)
        if not m: continue
        nombre=m.group(1).strip()
        cliente=por_nombre.get(nombre.casefold())
        if not cliente: raise SystemExit("Proveedor sin identificador: "+nombre)
        matches=[p for p in proveedores if p["cliente_id"]==cliente["id"]]
        if len(matches)!=1: raise SystemExit("Plan ambiguo para "+nombre)
        archivo=CARPETA/("correo_proveedor_"+str(indice)+".html")
        if not archivo.is_file(): raise SystemExit("HTML faltante: "+archivo.name)
        html=archivo.read_bytes()
        if b"cid:tappad-logo" not in html: raise SystemExit("HTML sin logo integrado")
        if cliente["id"] in usados: raise SystemExit("Proveedor repetido")
        usados.add(cliente["id"])
        lote.append({"cliente_id":cliente["id"],"licitacion_ids":matches[0]["licitacion_ids"],"html":archivo.name,"sha256_html":hashlib.sha256(html).hexdigest(),"destinatario_configurado":bool(str(cliente.get("correo") or "").strip())})
    if len(lote)!=len(proveedores): raise SystemExit("Cantidad de proveedores no coincide")
    salida={"modo":"SOLO_PREPARACION","proveedores":lote,"cantidad_correos":len(lote),"cantidad_oportunidades":sum(len(p["licitacion_ids"]) for p in lote)}
    SALIDA.write_text(json.dumps(salida,ensure_ascii=False,indent=2),encoding="utf-8")
    print("LOTE PREPARADO:",len(lote),"correos |",salida["cantidad_oportunidades"],"oportunidades")
    print("Sin envio SMTP y sin cambios en Supabase")

if __name__=="__main__":
    main()
