"""TAPPAD Radar: calendario verificable desde las bases PDF del ZIP SECOP.
Solo lectura. No guarda en Supabase ni envía mensajes.
Requiere: py -m pip install pymupdf
"""
import json,re,sys,unicodedata,zipfile
from datetime import datetime
from pathlib import Path
import pymupdf

ARCHIVO="BASES Y ANEXOS SIDUM-LPN-CO-E099-2026.zip"
MESES={m:i for i,m in enumerate("enero febrero marzo abril mayo junio julio agosto septiembre octubre noviembre diciembre".split(),1)}
MESES["setiembre"]=9
FECHA=re.compile(r"(?<!\d)(\d{1,2})\s+de\s+(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|setiembre|octubre|noviembre|diciembre)\s+(?:de|del)\s+(20\d{2})",re.I)
HORA=re.compile(r"\b(?:a\s+las|a\s+la|las)\s+(\d{1,2}):([0-5]\d)\s*horas",re.I)
REGLAS=[
 ("visita_obra",r"3\.1\s+VISITA AL SITIO",r"3\.2\s+JUNTA DE ACLARACIONES"),
 ("junta_aclaraciones",r"3\.2\s+JUNTA DE ACLARACIONES",r"4\.\s*PRESENTACI"),
 ("presentacion_apertura",r"4\.\s*PRESENTACI",r"5\.\s*FALLO"),
 ("fallo_programado",r"5\.\s*FALLO",r"6\.\s*FORMA"),
 ("inicio_obra",r"2\.4\s+FECHA DE INICIO",r"2\.5\s+NÚMERO DE CONVOCATORIA"),
 ("terminacion_obra",r"2\.4\s+FECHA DE INICIO",r"2\.5\s+NÚMERO DE CONVOCATORIA")
]
def norm(s):
 return "".join(c for c in unicodedata.normalize("NFD",s.lower()) if unicodedata.category(c)!="Mn")
def main():
 base=Path(__file__).resolve().parent
 archivo=base/ARCHIVO
 if not archivo.exists():
  print("No encuentro el ZIP:",archivo);sys.exit(1)
 with zipfile.ZipFile(archivo) as z:
  pdfs=[n for n in z.namelist() if Path(n).name.upper().startswith("BASES SIDUM") and n.lower().endswith(".pdf")]
  if not pdfs:
   print("No encontré las bases principales en el ZIP");sys.exit(1)
  doc=pymupdf.open(stream=z.read(pdfs[0]),filetype="pdf")
  paginas=[p.get_text("text") for p in doc]
  doc.close()
 texto="\n".join(paginas)
 # Construye offsets para conservar la página de origen.
 rangos=[];pos=0
 for i,p in enumerate(paginas,1):
  rangos.append((pos,pos+len(p),i));pos+=len(p)+1
 def pagina_de(offset):
  return next((i for a,b,i in rangos if a<=offset<=b),None)
 salida={"procedimiento":"SIDUM-LPN-CO-E099-2026","fuente":pdfs[0],"calendario":{},"advertencias":[],"estado":"requiere_validacion"}
 plano=norm(texto)
 for campo,inicio,fin in REGLAS:
  a=re.search(inicio,norm(texto),re.I)
  if not a:
   salida["advertencias"].append("No se encontró sección: "+campo);continue
  b=re.search(fin,plano[a.end():],re.I)
  segmento=texto[a.end():a.end()+b.start()] if b else texto[a.end():a.end()+1800]
  if len(segmento)>2500:segmento=segmento[:2500]
  fechas=list(FECHA.finditer(segmento))
  if not fechas:
   salida["advertencias"].append("Sin fecha en sección: "+campo);continue
  f=fechas[-1] if campo=="terminacion_obra" else fechas[0]
  try:
   fecha=datetime(int(f.group(3)),MESES[norm(f.group(2))],int(f.group(1))).date().isoformat()
  except (ValueError,KeyError):
   salida["advertencias"].append("Fecha no válida: "+campo);continue
  resto=segmento[f.end():f.end()+90]
  hora=HORA.search(resto) if campo not in ("inicio_obra","terminacion_obra") else None
  # Si el texto separa fecha y hora con puntuación, la evidencia queda visible.
  salida["calendario"][campo]={"fecha":fecha,"hora":f"{int(hora.group(1)):02d}:{hora.group(2)}" if hora else None,"pagina":pagina_de(a.end()+f.start()),"evidencia":segmento[max(0,f.start()-170):min(len(segmento),f.end()+130)].strip(),"validacion":"pendiente"}
 destino=base/"calendario_secop_validacion.json"
 destino.write_text(json.dumps(salida,ensure_ascii=False,indent=2),encoding="utf-8")
 print("Campos detectados:",len(salida["calendario"]))
 for k,v in salida["calendario"].items():print(k,v["fecha"],v["hora"],"página",v["pagina"])
 print("Advertencias:",len(salida["advertencias"]))
 print("Reporte:",destino)
if __name__=="__main__":main()
