"""Diagnóstico de texto extraído de bases SECOP (solo lectura)."""
import zipfile
from pathlib import Path
import pymupdf
zip_path=Path(__file__).resolve().parent/"BASES Y ANEXOS SIDUM-LPN-CO-E099-2026.zip"
if not zip_path.exists():
 print("No se encontró:",zip_path)
 raise SystemExit(1)
with zipfile.ZipFile(zip_path) as z:
 nombres=[n for n in z.namelist() if n.lower().endswith(".pdf") and "BASES SIDUM" in n.upper()]
 if not nombres:
  print("No se encontró el PDF principal dentro del ZIP")
  raise SystemExit(1)
 doc=pymupdf.open(stream=z.read(nombres[0]),filetype="pdf")
 salida=zip_path.parent/"diagnostico_texto_bases_secop.txt"
 terminos=("junta","aclarac","apertura","fallo","visita","noviembre","octubre","2026","presentaci")
 with salida.open("w",encoding="utf-8") as f:
  for numero,pagina in enumerate(doc,1):
   texto=pagina.get_text("text")
   lineas=texto.splitlines()
   indices=[i for i,s in enumerate(lineas) if any(t in s.lower() for t in terminos)]
   if not indices:continue
   f.write(f"\n===== PAGINA {numero} =====\n")
   ya=set()
   for i in indices[:45]:
    for j in range(max(0,i-3),min(len(lineas),i+5)):
     if j not in ya:
      f.write(f"{j+1:03d}: {lineas[j]}\n")
      ya.add(j)
    f.write("---\n")
 print("Páginas:",len(doc))
 print("Diagnóstico:",salida)
 print("Adjunta el archivo TXT generado.")
 doc.close()
