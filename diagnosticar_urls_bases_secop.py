"""Diagnostico local de URLs de bases SECOP, sin navegador, escrituras ni correos."""
import json
from pathlib import Path
from urllib.parse import urlparse
BASE=Path(__file__).resolve().parent/"documentos_secop_lote"
P=BASE/"reporte_descargas.json"
if not P.exists():raise SystemExit("No existe reporte_descargas.json")
data=json.loads(P.read_text(encoding="utf-8-sig"))
for item in data.get("procedimientos",[]):
 print("\nEXPEDIENTE:",item.get("codigo"),"| referencia:",item.get("referencia"))
 print("Estado:",item.get("estado_enlace"),"| bases candidata:",item.get("url_bases_candidata"))
 print("Bases verificadas:",json.dumps(item.get("bases_verificadas",[]),ensure_ascii=False))
 print("Documentos oficiales encontrados:")
 for e in item.get("enlaces_documentos",[]):
  u=str(e.get("url") or "")
  if urlparse(u).hostname=="www.sefincoahuila.gob.mx":
   print(" -",e.get("texto"),"|",u)
 print("Descargas locales:",len(item.get("archivos",[])))
 for a in item.get("archivos",[]):print(" -",a.get("nombre"))
 print("Errores:",json.dumps(item.get("errores",[]),ensure_ascii=False))
