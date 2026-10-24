"""Extrae URL oficiales de bases del diagnostico de navegacion SECOP.
No inventa URL ni modifica Supabase. Los enlaces quedan pendientes de prueba externa.
"""
import json,re
from pathlib import Path
from urllib.parse import urlparse

BASE=Path(__file__).resolve().parent
ORIGEN=BASE/"diagnostico_navegacion_secop.json"
DESTINO=BASE/"enlaces_bases_secop_pendientes_verificacion.json"

def es_url_documento(url):
 p=urlparse(str(url or ""))
 return (p.scheme=="https" and p.hostname=="www.sefincoahuila.gob.mx"
         and bool(re.fullmatch(r"/sistemas/Secop/Procedimiento/GetFile/\d+",p.path,re.I))
         and not p.query and not p.fragment)

def main():
 if not ORIGEN.exists():raise SystemExit("Falta diagnostico_navegacion_secop.json")
 data=json.loads(ORIGEN.read_text(encoding="utf-8-sig"))
 resultado={"estado":"pendiente_verificar_acceso_sin_sesion","procedimientos":[]}
 for r in data.get("procedimientos",[]):
  docs=[]
  for e in r.get("enlaces_visibles",[]):
   texto=str(e.get("texto") or "").strip()
   url=str(e.get("href") or "").strip()
   if es_url_documento(url):
    docs.append({"texto":texto,"url":url,"tipo":"bases" if "BASES" in texto.upper() else "otro_documento"})
  bases=[d for d in docs if d["tipo"]=="bases"]
  item={"codigo":r.get("codigo"),"referencia":r.get("referencia"),"documentos":docs,
        "url_bases_candidata":bases[0]["url"] if len(bases)==1 else None,
        "estado":"pendiente_verificacion_externa" if len(bases)==1 else "requiere_revision"}
  resultado["procedimientos"].append(item)
  print(item["codigo"],"| bases candidatas:",len(bases),"|",item["estado"])
 DESTINO.write_text(json.dumps(resultado,ensure_ascii=False,indent=2),encoding="utf-8")
 print("Reporte:",DESTINO)
 print("No se modifico Supabase ni se enviaron correos.")

if __name__=="__main__":main()
