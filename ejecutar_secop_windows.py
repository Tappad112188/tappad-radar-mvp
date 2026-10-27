"""Pipeline local SECOP Coahuila: solo extracción y preparación para revisión.
Uso Windows: py ejecutar_secop_windows.py
Sin escrituras a Supabase ni envíos de correo.
"""
import json
import subprocess
import sys
import msvcrt
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent
LOG = BASE / "secop_ejecucion_windows.log"
LOCK = BASE / "secop_ejecucion_windows.lock"
PASOS = (
    "descargar_documentos_secop_lote.py",
    "generar_fichas_secop_v3.py",
    "generar_fichas_comerciales_secop.py",
    "preparar_importacion_secop_supabase.py",
)

def ejecutar(nombre, log):
    print("Ejecutando:", nombre, flush=True)
    log.write("PASO " + nombre + "\n")
    log.flush()
    try:
        resultado = subprocess.run(
            [sys.executable, str(BASE / nombre)], cwd=str(BASE),
            stdout=log, stderr=subprocess.STDOUT, timeout=1800, check=False
        )
    except subprocess.TimeoutExpired:
        log.write("ERROR tiempo agotado: " + nombre + "\n")
        raise SystemExit(124)
    if resultado.returncode:
        log.write("ERROR " + nombre + " codigo=" + str(resultado.returncode) + "\n")
        raise SystemExit(resultado.returncode)

def main():
    with LOCK.open("a+b") as candado:
        try:
            msvcrt.locking(candado.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            raise SystemExit("Ya existe otra ejecución SECOP activa.")
        try:
            with LOG.open("a", encoding="utf-8") as log:
                log.write("\nINICIO " + datetime.now().isoformat(timespec="seconds") + "\n")
                ejecutar("extractor_secop_hoy_vigentes.py", log)
                fuente = BASE / "secop_hoy_vigentes.json"
                datos = json.loads(fuente.read_text(encoding="utf-8-sig"))
                if not datos.get("filtros_aplicados") or datos.get("errores") or datos.get("error"):
                    raise SystemExit("Extracción inválida; revisar el reporte.")
                if not datos.get("registros"):
                    log.write("SIN PROCEDIMIENTOS HOY: no reutilizar documentos anteriores.\n")
                    print("Sin procedimientos nuevos vigentes hoy. Sin cambios.")
                    return
                for paso in PASOS:
                    ejecutar(paso, log)
                log.write("FIN OK " + datetime.now().isoformat(timespec="seconds") + "\n")
            print("Lote preparado para revisión:", BASE / "documentos_secop_lote" / "secop_importacion_pendiente_revision.json")
            print("Sin importación a Supabase y sin correos.")
        finally:
            msvcrt.locking(candado.fileno(), msvcrt.LK_UNLCK, 1)

if __name__ == "__main__":
    main()
