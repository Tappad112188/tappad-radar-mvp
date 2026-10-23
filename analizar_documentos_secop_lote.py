"""TAPPAD Radar: revisión local de documentos SECOP (PDF y DOCX).
Solo lectura. Genera un reporte JSON con candidatos y evidencia; no valida fechas automáticamente.
Uso: py analizar_documentos_secop_lote.py
"""
import json,re,hashlib,unicodedata,zipfile
from pathlib import Path
from datetime import date
from collections import defaultdict
from xml.etree import ElementTree as ET
import pymupdf

ROOT=Path(__file__).resolve().parent
CARPETA=ROOT/"documentos_secop_lote"
FUENTE=ROOT/"secop_hoy_vigentes.json"
MESES={m:i for i,m in enumerate("enero febrero marzo abril mayo junio julio agosto septiembre octubre noviembre diciembre".split(),1)}
MESES["setiembre"]=9
PATRONES=[
 re.compile(r"(?<!\d)(\d{1,2})\s+de\s+(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|setiembre|octubre|noviembre|diciembre)\s+(?:de|del)\s+(20\d{2})(?!\d)",re.I),
 re.compile(r"(?<!\d)(\d{1,2})[/.-](\d{1,2})[/.-](20\d{2})(?!\d)")
]
ETAPAS={
 "visita_obra":r"visita\s+(?:al\s+sitio|de\s+obra|a\s+la\s+obra)",
 "junta_aclaraciones":r"junta\s+de\s+aclaraciones",
 "presentacion_apertura":r"(?:presentacion\s+(?:y\s+)?apertura|apertura\s+de\s+(?:proposiciones|propuestas)|presentacion\s+de\s+proposiciones)",
 "fallo_programado":r"(?:emision|acto|comunicacion|fecha)\s+(?:del?\s+)?fallo|\bfallo\s*:",
 "inicio_servicio_obra":r"(?:inicio|iniciacion)\s+(?:de\s+)?(?:los\s+)?(?:trabajos|servicios|obra|contrato)",
 "terminacion_servicio_obra":r"(?:terminacion|conclusion|finalizacion)\s+(?:de\s+)?(?:los\s+)?(?:trabajos|servicios|obra|contrato)"
}
OTROS={
 "costo_bases":r"(?:costo|precio|importe|venta)\s+(?:de\s+)?(?:las\s+)?bases",
 "garantias":r"(?:garantia\s+de\s+(?:cumplimiento|seriedad)|fianza)",
 "capital_contable":r"capital\s+contable",
 "experiencia":r"experiencia\s+(?:minima|requerida|en)",
 "requisitos":r"(?:requisitos\s+(?:para\s+participar|de\s+participacion)|documentacion\s+(?:legal|administrativa))",
 "plazo":r"(?:plazo\s+de\s+(?:ejecucion|prestacion|entrega)|vigencia\s+del\s+contrato)"
}
def normalizar(s):
 return "".join(c for c in unicodedata.normalize("NFD",s.lower()) if unicodedata.category(c)!="Mn")
def leer_docx(p):
 paginas=[]
 with zipfile.ZipFile(p) as z:
  for name in ["word/document.xml"]+sorted(n for n in z.namelist() if re.fullmatch(r"word/(?:header|footer)\d+\.xml",n)):
   if name not in z.namelist():continue
   root=ET.fromstring(z.read(name))
   ns="{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
   lineas=[]
   for para in root.iter(ns+"p"):
    texto="".join(t.text or "" for t in para.iter(ns+"t"))
    if texto.strip():lineas.append(texto)
   paginas.append((name,"\n".join(lineas)))
 return paginas
def leer_pdf(p):
 d=pymupdf.open(p)
 salida=[(f"pagina {i+1}",pg.get_text("text")) for i,pg in enumerate(d)]
 d.close()
 return salida
def fechas(texto):
 halladas=[]
 for patron in PATRONES:
  for m in patron.finditer(texto):
   try:
    d=int(m.group(1));mes=MESES[normalizar(m.group(2))] if patron is PATRONES[0] else int(m.group(2));anio=int(m.group(3))
    iso=date(anio,mes,d).isoformat()
    halladas.append((m.start(),m.end(),iso))
   except (ValueError,KeyError):pass
 return sorted(halladas)
def analizar(p):
 paginas=leer_pdf(p) if p.suffix.lower()==".pdf" else leer_docx(p)
 resultado={"archivo":p.name,"sha256":hashlib.sha256(p.read_bytes()).hexdigest(),"secciones":len(paginas),"texto_extraido":sum(len(t.strip()) for _,t in paginas),"etapas":{},"datos_adicionales":{},"advertencias":[]}
 for grupo,reglas in [("etapas",ETAPAS),("datos_adicionales",OTROS)]:
  for campo,patron in reglas.items():
   candidatos=[]
   for ubicacion,texto in paginas:
    norm=normalizar(texto)
    for m in list(re.finditer(patron,norm,re.I))[:15]:
     # Contexto a continuación y antes del encabezado.
     a=max(0,m.start()-90);b=min(len(texto),m.end()+650)
     fragmento=texto[a:b]
     fs=fechas(texto[m.end():min(len(texto),m.end()+650)])
     c={"ubicacion":ubicacion,"evidencia":fragmento[:740].strip()}
     if fs:
      c["fechas_cercanas"]=[f for _,_,f in fs[:4]]
     candidatos.append(c)
     if len(candidatos)>=12:break
    if len(candidatos)>=12:break
   if candidatos:resultado[grupo][campo]=candidatos
 if resultado["texto_extraido"]<100:resultado["advertencias"].append("Texto insuficiente; podría requerir OCR")
 return resultado
def main():
 if not FUENTE.is_file() or not CARPETA.is_dir():
  print("Faltan secop_hoy_vigentes.json o documentos_secop_lote");return
 fuente=json.loads(FUENTE.read_text(encoding="utf-8-sig"))
 reporte={"fecha_fuente":fuente.get("fecha_consulta"),"procedimientos":[],"advertencias":[],"estado":"pendiente_validacion_humana"}
 for r in fuente.get("registros",[]):
  codigo=r["codigo"]
  folder=CARPETA/re.sub(r"[^A-Za-z0-9._-]+","_",codigo).strip("._")[:110]
  item={"codigo":codigo,"referencia":r.get("documentos_referencia"),"descripcion":r.get("descripcion"),"estatus":r.get("estatus"),"fecha_publicacion":r.get("fecha_publicacion"),"documentos":[],"advertencias":[]}
  for p in sorted(folder.glob("*")) if folder.exists() else []:
   if p.suffix.lower() not in (".pdf",".docx"):continue
   try:item["documentos"].append(analizar(p))
   except Exception as e:item["advertencias"].append(f"No se pudo analizar {p.name}: {e}")
  hashes=defaultdict(list)
  for doc in item["documentos"]:hashes[doc["sha256"]].append(doc["archivo"])
  for archivos in hashes.values():
   if len(archivos)>1:item["advertencias"].append("Archivos idénticos: "+", ".join(archivos))
  if not item["documentos"]:item["advertencias"].append("Sin documentos PDF/DOCX para analizar")
  reporte["procedimientos"].append(item)
  print("\n",codigo,"| documentos:",len(item["documentos"]))
  for doc in item["documentos"]:
   print(" ",doc["archivo"],"| texto:",doc["texto_extraido"],"caracteres")
   for campo,datos in doc["etapas"].items():
    fechas_detectadas=sorted({f for c in datos for f in c.get("fechas_cercanas",[])})
    print("   ",campo,"| candidatos:",len(datos),"| fechas cercanas:",", ".join(fechas_detectadas[:8]) or "sin fecha")
  for adv in item["advertencias"]:print("  AVISO:",adv)
 destino=CARPETA/"reporte_analisis_documental.json"
 destino.write_text(json.dumps(reporte,ensure_ascii=False,indent=2),encoding="utf-8")
 print("\nReporte:",destino)
 print("IMPORTANTE: Fechas candidatas, no validadas. Sin modificaciones a Supabase ni correos.")
if __name__=="__main__":main()
