"""Verifica acceso a enlaces de bases SECOP sin cookies ni sesion.
Lee diagnostico_navegacion_secop.json; NO modifica Supabase ni envia correos.
Solo solicita encabezados/respuesta inicial, no guarda documentos.
"""
import json,re,urllib.request,urllib.error
from pathlib import Path
from urllib.parse import urlparse

BASE=Path(__file__).resolve().parent
ORIGEN=BASE/"diagnostico_navegacion_secop.json"
SALIDA=BASE/"verificacion_externa_bases_secop.json"
PATRON=re.compile(r"^/sistemas/Secop/Procedimiento/GetFile/\d+$",re.I)

def verificar(url):
 p=urlparse(url)
 if p.scheme!="https" or p.hostname!="www.sefincoahuila.gob.mx" or not PATRON.fullmatch(p.path) or p.query or p.fragment:
  return {"estado":"url_no_permitida"}
 req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 (compatible; TAPPAD-Radar-URL-Check/1.0)","Range":"bytes=0-1023"},method="GET")
 try:
  with urllib.request.urlopen(req,timeout=25) as resp:
   tipo=resp.headers.get("Content-Type","").lower()
   disp=resp.headers.get("Content-Disposition","")
   inicio=resp.read(1024)
   html=tipo.startswith("text/html") or inicio.lstrip().lower().startswith((b"<!doctype html",b"<html"))
   archivo=bool(re.search(r"pdf|word|octet-stream|zip",tipo,re.I) or "attachment" in disp.lower() or inicio.startswith((b"%PDF-",b"PK\x03\x04",b"\xd0\xcf\x11\xe0")))
   return {"estado":"archivo_accesible_sin_sesion" if archivo and not html else "respuesta_no_confirmada",
           "http":resp.status,"url_final":resp.url,"content_type":tipo,"content_disposition":disp[:160],
           "firma_hex":inicio[:12].hex()}
 except urllib.error.HTTPError as e:
  return {"estado":"error_http","http":e.code,"detalle":str(e)[:160]}
 except Exception as e:
  return {"estado":"error_conexion","detalle":str(e)[:200]}

def main():
 if not ORIGEN.exists():raise SystemExit("No existe diagnostico_navegacion_secop.json en Descargas")
 data=json.loads(ORIGEN.read_text(encoding="utf-8-sig"))
 reporte={"metodo":"GET anonimo, sin cookies ni sesion, maximo 1024 bytes por enlace","procedimientos":[]}
 for r in data.get("procedimientos",[]):
  docs=[]
  for e in r.get("enlaces_visibles",[]):
   url=str(e.get("href") or "")
   texto=str(e.get("texto") or "")
   if "BASES" in texto.upper() and PATRON.fullmatch(urlparse(url).path):
    docs.append({"texto":texto,"url":url,**verificar(url)})
  reporte["procedimientos"].append({"codigo":r.get("codigo"),"referencia":r.get("referencia"),"bases":docs})
  print(r.get("codigo"),":",[(d["estado"],d.get("http")) for d in docs])
 SALIDA.write_text(json.dumps(reporte,ensure_ascii=False,indent=2),encoding="utf-8")
 print("Reporte:",SALIDA)
 print("No se modifico Supabase ni se enviaron correos.")

if __name__=="__main__":main()
