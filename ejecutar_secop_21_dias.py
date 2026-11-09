"""Pipeline aislado SECOP 21 dias. No escribe Supabase ni envia correos.
Ejecutar en Windows: py ejecutar_secop_21_dias.py
"""
import json, subprocess, sys, msvcrt
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
BASE=Path(__file__).resolve().parent
LOCK=BASE/"secop_21_dias.lock"
LOG=BASE/"secop_21_dias.log"
PASOS=("extractor_secop_ultimas_tres_semanas.py",
       "preparar_revision_secop_21_dias.py",
       "descargar_documentos_secop_21_dias.py",
       "generar_fichas_secop_21_dias.py",
       "generar_fichas_comerciales_secop_21_dias.py",
       "preparar_importacion_secop_21_dias.py")
def ejecutar(nombre,log):
 print("Ejecutando:",nombre,flush=True)
 log.write("PASO "+nombre+"\n");log.flush()
 try:
  r=subprocess.run([sys.executable,str(BASE/nombre)],cwd=str(BASE),stdout=log,stderr=subprocess.STDOUT,timeout=3600,check=False)
 except subprocess.TimeoutExpired:raise SystemExit("Tiempo agotado en "+nombre)
 if r.returncode:raise SystemExit("ERROR en "+nombre+"; revisa "+str(LOG))
def main():
 with LOCK.open("a+b") as lock:
  try:msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
  except OSError:raise SystemExit("Ya hay una ejecucion SECOP activa")
  try:
   with LOG.open("a",encoding="utf-8") as log:
    log.write("\nINICIO "+datetime.now().isoformat()+"\n")
    ejecutar(PASOS[0],log)
    ejecutar(PASOS[1],log)
    d=json.loads((BASE/"secop_revision_21_dias.json").read_text(encoding="utf-8-sig"))
    if d.get("fecha_consulta")!=datetime.now(ZoneInfo("America/Monterrey")).date().isoformat() or d.get("estado")!="SOLO_REVISION_SIN_IMPORTACION_NI_ENVIO":
     raise SystemExit("Lote no validado")
    if not d.get("total"):
     print("Sin procedimientos en ventana de 21 dias. No se reutilizan expedientes anteriores.")
     return
    for paso in PASOS[2:]:ejecutar(paso,log)
    destino=BASE/"documentos_secop_21_dias"/"secop_importacion_pendiente_revision.json"
    salida=json.loads(destino.read_text(encoding="utf-8-sig"))
    if salida.get("estado")!="PENDIENTE_VALIDACION_OFICIAL_NO_IMPORTAR_AUTOMATICAMENTE":
     raise SystemExit("Estado de salida inesperado")
    print("Fichas preparadas:",salida.get("total"))
    print("Reporte:",destino)
    print("PENDIENTE VALIDACION DOCUMENTAL: sin escrituras Supabase ni correos.")
  finally:
   msvcrt.locking(lock.fileno(),msvcrt.LK_UNLCK,1)
if __name__=="__main__":main()
