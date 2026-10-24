"""Ejecuta SECOP local en modo seguro. No importa ni envía alertas.
Uso: py ejecutar_secop_windows.py
"""
import subprocess
import sys
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent
LOG = BASE / "secop_ejecucion_windows.log"
PASOS = (
    "extractor_secop_hoy_vigentes.py",
    "descargar_documentos_secop_lote.py",
)

def main():
    with LOG.open("a", encoding="utf-8") as log:
        log.write("\nINICIO " + datetime.now().isoformat(timespec="seconds") + "\n")
        for nombre in PASOS:
            print("Ejecutando:", nombre, flush=True)
            log.write("PASO " + nombre + "\n")
            resultado = subprocess.run([sys.executable, str(BASE / nombre)],
                                       cwd=str(BASE), stdout=log, stderr=subprocess.STDOUT,
                                       timeout=1800, check=False)
            if resultado.returncode:
                log.write("ERROR " + nombre + " codigo=" + str(resultado.returncode) + "\n")
                raise SystemExit(resultado.returncode)
        log.write("FIN OK " + datetime.now().isoformat(timespec="seconds") + "\n")
    print("Extracción terminada. Revisa:", LOG)
    print("La sincronización y los correos permanecen desactivados hasta validar datos.")

if __name__ == "__main__":
    main()
