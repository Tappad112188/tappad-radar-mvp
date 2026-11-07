"""Prioriza expedientes SECOP recientes para revision documental, sin asumir vigencia legal.
No conecta Supabase, no descarga bases y no envia alertas.
"""
import json
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
BASE=Path(__file__).resolve().parent
def main():
 d=json.loads((BASE/"secop_vigentes_actuales.json").read_text(encoding="utf-8-sig"))
 hoy=datetime.now(ZoneInfo("America/Monterrey")).date()
 if d.get("fecha_consulta")!=hoy.isoformat() or not d.get("filtros_aplicados") or d.get("error") or d.get("errores") or d.get("coincide_total") is False:
  raise SystemExit("Extraccion invalida o de otra fecha")
 registros=d.get("registros") or []
 if len(registros)!=d.get("total_unicos"):raise SystemExit("Total inconsistente")
 grupos={"ultimos_30_dias":[],"31_a_90_dias":[],"mas_de_90_dias":[]}
 for r in registros:
  try:publicacion=datetime.fromisoformat(r["fecha_publicacion"]).date()
  except (ValueError,TypeError,KeyError):raise SystemExit("Fecha invalida: "+str(r.get("codigo")))
  dias=(hoy-publicacion).days
  if dias<0:raise SystemExit("Fecha de publicacion futura: "+str(r.get("codigo")))
  clave="ultimos_30_dias" if dias<=30 else "31_a_90_dias" if dias<=90 else "mas_de_90_dias"
  grupos[clave].append({"codigo":r["codigo"],"fecha_publicacion":r["fecha_publicacion"],"dias_desde_publicacion":dias,"descripcion":r.get("descripcion") or "","estatus_portal":r.get("estatus"),"revision_calendario":"pendiente"})
 for v in grupos.values():v.sort(key=lambda r:(r["fecha_publicacion"],r["codigo"]),reverse=True)
 salida={"fecha_consulta":hoy.isoformat(),"total":len(registros),"advertencia":"Estatus Vigente no acredita apertura futura; verificar bases antes de alertar.","grupos":grupos}
 ruta=BASE/"secop_prioridades_revision.json"
 ruta.write_text(json.dumps(salida,ensure_ascii=False,indent=2),encoding="utf-8")
 for k,v in grupos.items():print(k,":",len(v))
 print("PRIMEROS 15 PARA REVISION:")
 for r in (grupos["ultimos_30_dias"]+grupos["31_a_90_dias"]+grupos["mas_de_90_dias"])[:15]:
  print(r["fecha_publicacion"],"|",r["codigo"],"|",r["descripcion"][:90])
 print("Reporte:",ruta)
 print("SOLO LECTURA. Ningun expediente autorizado para alerta sin verificar calendario.")
if __name__=="__main__":main()
