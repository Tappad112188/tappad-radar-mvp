"""TAPPAD Radar: simulacion de correo consolidado de varias fuentes.
Solo lectura de archivos locales. No envia correos ni escribe en servicios.
"""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
BASE=ROOT/"documentos_secop_lote"
SECOP=BASE/"simulacion_coincidencias_secop.json"
COMPRAS=ROOT/"coincidencias_comprasmx.json"
SALIDA=BASE/"vista_previa_unificada_tappad.txt"
HISTORIAL=ROOT/"historial_alertas_simulado.json"
def cargar(path):
 if not path.exists():return None
 return json.loads(path.read_text(encoding="utf-8-sig"))
def evento(v):
 if not isinstance(v,dict) or not v.get("fecha"):return "No identificada"
 return str(v["fecha"])+(" "+str(v["hora"]) if v.get("hora") else "")
def normalizar(d,fuente):
 resultado=[]
 for p in d.get("proveedores",[]):
  for f in p.get("coincidencias",[]):
   codigo=str(f.get("referencia") or f.get("codigo") or "").strip()
   if not codigo:continue
   resultado.append({"proveedor":p["proveedor"],"fuente":fuente,"codigo":codigo,"objeto":f.get("objeto") or "Sin objeto","publicacion":f.get("publicacion"),"junta":f.get("junta_aclaraciones"),"apertura":f.get("presentacion_apertura"),"fallo":f.get("fallo_programado"),"url":f.get("url")})
 return resultado
def main():
 d=cargar(SECOP)
 if d is None:raise SystemExit("Falta documentos_secop_lote/simulacion_coincidencias_secop.json")
 entradas=normalizar(d,"SECOP Coahuila")
 otra=cargar(COMPRAS)
 if otra is not None:entradas+=normalizar(otra,"ComprasMX")
 historico=cargar(HISTORIAL) or {}
 enviados=set(historico.get("claves_notificadas",[]))
 por_proveedor={}
 vistos=set()
 duplicados=0
 for a in entradas:
  clave="|".join([a["proveedor"].casefold(),a["fuente"].casefold(),a["codigo"].casefold()])
  if clave in vistos or clave in enviados:
   duplicados+=1;continue
  vistos.add(clave)
  por_proveedor.setdefault(a["proveedor"],[]).append(a)
 lineas=["TAPPAD RADAR - VISTA PREVIA CONSOLIDADA","SIMULACION, SIN ENVIOS","ComprasMX: "+("archivo local encontrado" if otra is not None else "sin archivo de coincidencias; no se incluyen oportunidades de esa fuente"),""]
 for proveedor,items in sorted(por_proveedor.items()):
  lineas.extend(["="*70,"PARA: "+proveedor,"ASUNTO: TAPPAD Radar | "+str(len(items))+" oportunidad(es) nueva(s)",""])
  for i,a in enumerate(items,1):
   lineas.extend([str(i)+". "+a["objeto"],"Fuente: "+a["fuente"],"Procedimiento: "+a["codigo"],"Publicacion: "+str(a["publicacion"] or "No identificada"),"Junta de aclaraciones: "+evento(a["junta"]),"Presentacion y apertura (fecha limite): "+evento(a["apertura"]),"Fallo programado: "+evento(a["fallo"])])
   if a["url"]:lineas.append("Fuente oficial: "+a["url"])
   lineas.append("")
  lineas.extend(["Para asesoria en requisitos y preparacion de propuestas: TAPPAD Consultoria.","Las fechas pueden cambiar por modificaciones oficiales; la coincidencia por giro no garantiza elegibilidad.",""])
 SALIDA.write_text("\n".join(lineas),encoding="utf-8")
 print("Proveedores con alertas:",len(por_proveedor))
 print("Oportunidades nuevas:",sum(map(len,por_proveedor.values())))
 print("Duplicados omitidos:",duplicados)
 print("ComprasMX:", "incluido desde archivo local" if otra is not None else "pendiente de integrar")
 print("Vista previa:",SALIDA)
 print("No se enviaron correos ni se modificaron bases de datos o historial.")
if __name__=="__main__":main()
