"""TAPPAD Radar: extrae calendario de un ZIP SECOP sin modificar bases de datos.
Uso: py extraer_calendario_secop_v2.py "archivo.zip"
Requiere: py -m pip install pymupdf
"""
import argparse
import json
import re
import unicodedata
import zipfile
from datetime import date
from pathlib import Path
import pymupdf

MESES = {m:i for i,m in enumerate("enero febrero marzo abril mayo junio julio agosto septiembre octubre noviembre diciembre".split(),1)}
MESES["setiembre"] = 9
FECHA = re.compile(r"(?<!\d)(\d{1,2})\s+de\s+(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|setiembre|octubre|noviembre|diciembre)\s+(?:de|del)\s+(20\d{2})(?!\d)", re.I)
FECHA_NUM = re.compile(r"(?<!\d)(\d{1,2})[/.-](\d{1,2})[/.-](20\d{2})(?!\d)")
HORA = re.compile(r"\b(?:a\s+las|a\s+la|las)\s+(\d{1,2}):([0-5]\d)\s*horas",re.I)
REGLAS = {
 "visita_obra": (r"\bvisita\s+al\s+sitio\b", r"\bjunta\s+de\s+aclaraciones\b"),
 "junta_aclaraciones": (r"\bjunta\s+de\s+aclaraciones\b", r"\bpresentacion\s+de\s+proposiciones\b"),
 "presentacion_apertura": (r"\bpresentacion\s+de\s+proposiciones\s+y\s+apertura\b", r"\bfallo\b"),
 "fallo_programado": (r"\b(?:5\s*\.\s*)?fallo\b", r"\b(?:6\s*\.\s*)?(?:forma\s+de\s+pago|estimaciones|anticipo)\b"),
 "inicio_obra": (r"\bfecha\s+de\s+inicio\s+y\s+termino\s+de\s+la\s+obra\b", r"\bnumero\s+de\s+convocatoria\b"),
 "terminacion_obra": (r"\bfecha\s+de\s+inicio\s+y\s+termino\s+de\s+la\s+obra\b", r"\bnumero\s+de\s+convocatoria\b")
}
def normalizar(s):
 return "".join(c for c in unicodedata.normalize("NFD",s.lower()) if unicodedata.category(c)!="Mn")
def fechas_en(texto):
 encontrados=[]
 for patron in (FECHA, FECHA_NUM):
  for m in patron.finditer(texto):
   try:
    if patron is FECHA:
     d,mo,y=int(m.group(1)),MESES[normalizar(m.group(2))],int(m.group(3))
    else:
     d,mo,y=map(int,m.groups())
    f=date(y,mo,d).isoformat()
    encontrados.append((m.start(),m.end(),f))
   except (ValueError,KeyError):
    pass
 return sorted(encontrados)
def main():
 parser=argparse.ArgumentParser(description="Calendario SECOP: extracción local con evidencia")
 parser.add_argument("zip",type=Path,help="ZIP descargado desde SECOP")
 args=parser.parse_args()
 if not args.zip.is_file():
  parser.error("No existe el ZIP: "+str(args.zip))
 with zipfile.ZipFile(args.zip) as z:
  pdfs=[n for n in z.namelist() if n.lower().endswith(".pdf") and "bases" in Path(n).name.lower() and not n.startswith("__MACOSX")]
  pdfs.sort(key=lambda n:(0 if re.search(r"^bases\s",Path(n).name,re.I) else 1,len(n)))
  if not pdfs:
   parser.error("No encontré un PDF de bases en el ZIP")
  elegido=pdfs[0]
  doc=pymupdf.open(stream=z.read(elegido),filetype="pdf")
  paginas=[p.get_text("text") for p in doc]
  doc.close()
 salida={"expediente":args.zip.name,"documento_base":elegido,"paginas":len(paginas),"calendario":{},"advertencias":[],"estado":"pendiente_validacion_humana"}
 # Buscar por página y en páginas consecutivas, conservando evidencia y localización.
 bloques=[]
 for i in range(len(paginas)):
  bloques.append((i+1,paginas[i] + ("\n"+paginas[i+1] if i+1<len(paginas) else "")))
 for campo,(inicio,fin) in REGLAS.items():
  candidatos=[]
  if campo=="fallo_programado":
   # Buscar encabezado "FALLO:" aun cuando incluya referencias legales en la misma línea.
   # La fecha se toma del texto posterior inmediato, no de menciones incidentales.
   for indice,pagina_texto in enumerate(paginas):
    limpio=normalizar(pagina_texto)
    for enc in re.finditer(r"\bfallo\s*:",limpio,re.I):
     antes=limpio[max(0,enc.start()-70):enc.start()]
     despues=pagina_texto[enc.end():enc.end()+1100]
     # Debe ser un encabezado de acto: numerado o con referencias a artículos legales.
     if not (re.search(r"(?:^|\n)\s*\d{1,2}\s*\.\s*$",antes) or re.search(r"art[ií]culos?\s+32",normalizar(despues[:180])) or re.search(r"\b5\s*\.\s*$",antes)):
      continue
     # Cortar al próximo encabezado numerado para evitar capturar otras etapas.
     corte=re.search(r"(?m)^\s*\d{1,2}\s*\.\s*[A-ZÁÉÍÓÚÑ]",despues)
     if corte: despues=despues[:corte.start()]
     fechas=fechas_en(despues)
     if not fechas: continue
     pos_inicio,pos_fin,fecha=fechas[0]
     m=HORA.search(despues[pos_fin:pos_fin+120])
     hora=f"{int(m.group(1)):02d}:{m.group(2)}" if m and int(m.group(1))<24 else None
     candidatos.append({"fecha":fecha,"hora":hora,"pagina":indice+1,"evidencia":despues[max(0,pos_inicio-130):min(len(despues),pos_fin+120)].strip(),"validacion":"pendiente"})
   if len(candidatos)==1:
    salida["calendario"][campo]=candidatos[0]
   elif len(candidatos)>1:
    salida["calendario"][campo]={"candidatos":candidatos,"validacion":"ambigua"}
    salida["advertencias"].append("Múltiples fechas bajo encabezados FALLO")
   else:
    salida["advertencias"].append("No identificado: fallo_programado (no se halló fecha próxima al encabezado FALLO)")
   continue
  for pagina,contenido in bloques:
   limpio=normalizar(contenido)
   encabezados=list(re.finditer(inicio,limpio,re.I))
   for enc in encabezados:
    limite=re.search(fin,limpio[enc.end():],re.I)
    tope=enc.end()+limite.start() if limite else min(len(contenido),enc.end()+1000)
    fragmento=contenido[enc.end():tope][:1400]
    fechas=fechas_en(fragmento)
    if not fechas:continue
    # Inicio/terminación comparten sección y pueden tener dos fechas.
    seleccionado=fechas[-1] if campo=="terminacion_obra" else fechas[0]
    a,b,fecha=seleccionado
    contexto=fragmento[max(0,a-150):min(len(fragmento),b+120)].strip()
    hora=None
    if campo not in ("inicio_obra","terminacion_obra"):
     m=HORA.search(fragmento[b:b+100])
     if m and int(m.group(1))<24:hora=f"{int(m.group(1)):02d}:{m.group(2)}"
    # Cálculo de página si el evento cae en la página siguiente.
    offset=enc.end()+a
    pagina_origen=pagina+1 if offset>=len(paginas[pagina-1])+1 else pagina
    candidatos.append({"fecha":fecha,"hora":hora,"pagina":pagina_origen,"evidencia":contexto,"validacion":"pendiente"})
  unicos={(c["fecha"],c["hora"],c["pagina"]):c for c in candidatos}
  if len(unicos)==1:
   salida["calendario"][campo]=next(iter(unicos.values()))
  elif not unicos:
   salida["advertencias"].append("No identificado: "+campo)
  else:
   salida["advertencias"].append("Múltiples candidatos para "+campo+"; requiere revisión")
   salida["calendario"][campo]={"candidatos":list(unicos.values()),"validacion":"ambigua"}
 if "presentacion_apertura" in salida["calendario"] and "fecha" in salida["calendario"]["presentacion_apertura"]:
  salida["calendario"]["limite_presentacion_propuestas"]=dict(salida["calendario"]["presentacion_apertura"])
  salida["calendario"]["limite_presentacion_propuestas"]["criterio"]="Misma fecha y hora del acto de apertura, sujeto a validación"
 destino=args.zip.with_name(args.zip.stem+"_calendario_v2.json")
 destino.write_text(json.dumps(salida,ensure_ascii=False,indent=2),encoding="utf-8")
 print("Documento:",elegido)
 for k,v in salida["calendario"].items():
  print(k,v.get("fecha","AMBIGUO"),v.get("hora",""),"página",v.get("pagina",""))
 print("Advertencias:",len(salida["advertencias"]))
 for aviso in salida["advertencias"]: print(" -",aviso)
 print("Resultado:",destino)
 print("No se modificó Supabase ni se enviaron correos.")
if __name__=="__main__":
 main()
