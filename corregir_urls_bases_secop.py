"""Corregir enlaces SECOP en Supabase usando reporte local existente.
Simulacion por defecto; --actualizar aplica solo a dos expedientes conocidos.
No ejecuta Chromium ni envia correos.
"""
import argparse,json,os,re
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.parse import urlencode
BASE=Path(__file__).resolve().parent/"documentos_secop_lote"
IDS={"AI3-CO-E100-2026":"secop-coahuila:ai3-co-e100-2026","AI3-CO-E101-2026":"secop-coahuila:ai3-co-e101-2026"}
def api(method,uid,payload=None):
 key=os.getenv("SUPABASE_ADMIN_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
 base=os.getenv("SUPABASE_URL")
 if not key or not base:raise SystemExit("Faltan credenciales Supabase en el entorno")
 url=base.rstrip("/")+"/rest/v1/licitaciones?"+urlencode({"uuid_procedimiento":"eq."+uid,"select":"uuid_procedimiento,numero_procedimiento,url_bases,documentos_disponibles"})
 headers={"apikey":key,"Authorization":"Bearer "+key,"Content-Type":"application/json","Prefer":"return=representation"}
 req=Request(url,headers=headers,method=method,data=json.dumps(payload).encode() if payload is not None else None)
 with urlopen(req,timeout=40) as response:return json.load(response)
def main():
 parser=argparse.ArgumentParser()
 parser.add_argument("--actualizar",action="store_true")
 args=parser.parse_args()
 ruta=BASE/"reporte_descargas.json"
 if not ruta.exists():raise SystemExit("No existe reporte_descargas.json")
 reporte=json.loads(ruta.read_text(encoding="utf-8-sig"))
 encontrados={}
 for item in reporte.get("procedimientos",[]):
  codigo=item.get("codigo")
  if codigo not in IDS:continue
  candidatos=item.get("bases_verificadas") or []
  pdf=[e for e in candidatos if e.get("estado")=="verificado_sin_sesion" and re.search(r"\.pdf\b",str(e.get("texto","")),re.I)]
  if len(pdf)!=1:raise SystemExit("No hay exactamente un PDF verificado para "+codigo)
  url=pdf[0]["url"]
  if not re.fullmatch(r"https://www\.sefincoahuila\.gob\.mx/sistemas/Secop/Procedimiento/GetFile/\d+",url,re.I):
   raise SystemExit("URL fuera del dominio oficial")
  docs=[]
  for e in candidatos:
   u=e.get("url")
   if not isinstance(u,str) or not re.fullmatch(r"https://www\.sefincoahuila\.gob\.mx/sistemas/Secop/Procedimiento/GetFile/\d+",u,re.I):continue
   docs.append({"tipo":"bases" if e is pdf[0] else "bases_y_anexos","texto":e.get("texto"),"url":u,"estado":e.get("estado")})
  encontrados[codigo]=(url,docs)
 if set(encontrados)!=set(IDS):raise SystemExit("Faltan expedientes esperados en reporte; sin cambios")
 for codigo,uid in IDS.items():
  actual=api("GET",uid)
  if len(actual)!=1:raise SystemExit("Expediente no unico en Supabase: "+uid)
  if codigo not in str(actual[0].get("numero_procedimiento","")):raise SystemExit("Referencia no coincide: "+codigo)
  url,docs=encontrados[codigo]
  print(codigo,"| PDF principal:",url,"| documentos:",len(docs))
  if args.actualizar:
   result=api("PATCH",uid,{"url_bases":url,"documentos_disponibles":docs,
    "documentos_bases_verificados":[{"url":url,"texto":next(d["texto"] for d in docs if d["url"]==url)}]})
   if len(result)!=1 or result[0].get("url_bases")!=url:raise SystemExit("No se confirmo actualizacion: "+uid)
   print("ACTUALIZADO Y CONFIRMADO:",uid)
 print("FINALIZADO.","Se actualizaron enlaces; no se enviaron correos." if args.actualizar else "SIMULACION sin cambios. Para aplicar: --actualizar")
if __name__=="__main__":main()
