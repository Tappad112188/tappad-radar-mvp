"""Inspecciona columnas de fechas del archivo oficial ComprasMX; solo lectura."""
import csv, shutil, tempfile, urllib.request
from pathlib import Path
from tappad_importador_automatico import CSV_URL

def main():
    with tempfile.TemporaryDirectory() as carpeta:
        ruta=Path(carpeta)/"Expedientes_ComprasMX_2026.csv"
        req=urllib.request.Request(CSV_URL,headers={"User-Agent":"TAPPAD-Radar/1.0"})
        with urllib.request.urlopen(req,timeout=180) as respuesta, ruta.open("wb") as salida:
            shutil.copyfileobj(respuesta,salida)
        if ruta.stat().st_size<1000: raise RuntimeError("Descarga incompleta")
        with ruta.open(encoding="latin1",newline="") as archivo:
            lector=csv.DictReader(archivo)
            columnas=lector.fieldnames or []
            relevantes=[c for c in columnas if any(k in c.casefold() for k in ("fecha","junta","aclaraci","fallo","apertura","propuesta","publicaci"))]
            print("COLUMNAS RELACIONADAS CON CALENDARIO:")
            for c in relevantes: print(" -",repr(c))
            print("\nEJEMPLOS DE FECHAS (primeros 5 registros):")
            for i,fila in zip(range(5),lector):
                print("\nRegistro",i+1,":",fila.get("Número de procedimiento/proyecto"))
                for c in relevantes: print(" ",c,":",repr(fila.get(c)))
        print("\nSOLO LECTURA. NO SE MODIFICO SUPABASE NI SE ENVIARON CORREOS.")

if __name__=="__main__": main()
