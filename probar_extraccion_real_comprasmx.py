"""Prueba real de extracción ComprasMX. Sin Supabase ni correos."""
import csv, shutil, tempfile, urllib.request
from pathlib import Path
from tappad_importador_automatico import CSV_URL, registro

COLUMNAS = [
    ("Descripción del procedimiento", "Descripción anuncio", "descripcion"),
    ("Número de procedimiento", "Número de procedimiento/proyecto", "numero_procedimiento"),
    ("Fecha de publicación", "Fecha publicación", "fecha_publicacion"),
    ("Fecha de Junta de aclaraciones", "Fecha y hora junta de aclaraciones", "fecha_junta_aclaraciones"),
    ("Fecha de apertura de proposiciones", "Fecha apertura", "fecha_apertura"),
    ("Fecha de fallo", "Fecha de fallo", "fecha_fallo_programado"),
    ("Enlace a documentos del procedimiento", "Dirección del anuncio", "url_procedimiento"),
]
AVISO = "Fecha no disponible, verificar enlace"
FECHAS = {2,3,4,5}

def probar():
    with tempfile.TemporaryDirectory() as d:
        archivo = Path(d) / "oficial.csv"
        req = urllib.request.Request(CSV_URL, headers={"User-Agent":"TAPPAD-Radar/1.0"})
        with urllib.request.urlopen(req, timeout=180) as resp, archivo.open("wb") as out:
            shutil.copyfileobj(resp,out)
        if archivo.stat().st_size < 1000: raise RuntimeError("CSV oficial vacío o incompleto")
        with archivo.open(encoding="latin1", newline="") as f:
            reader=csv.DictReader(f)
            faltan=[col for _,col,_ in COLUMNAS if col not in (reader.fieldnames or [])]
            if faltan: raise RuntimeError("Faltan columnas oficiales: "+repr(faltan))
            muestras=[]; examinados=0; faltantes=[0]*7; diferencias=[]
            for fila in reader:
                item=registro(fila)
                if not item: continue
                examinados+=1
                for i,(etiqueta,columna,campo) in enumerate(COLUMNAS):
                    esperado=(fila.get(columna) or "").strip()
                    obtenido=(item.get(campo) or "").strip()
                    if esperado!=obtenido and len(diferencias)<12:
                        diferencias.append({"procedimiento":item.get("numero_procedimiento"),"campo":etiqueta,"esperado":esperado[:120],"obtenido":obtenido[:120]})
                    if not obtenido: faltantes[i]+=1
                if len(muestras)<3 and item.get("descripcion") and item.get("numero_procedimiento"):
                    muestras.append(item)
        print("Archivo oficial descargado. Tamaño bytes:",archivo.stat().st_size)
        print("Procedimientos con identificador examinados:",examinados)
        print("COLUMNAS Y COBERTURA:")
        for i,(etiqueta,columna,campo) in enumerate(COLUMNAS):
            print(f" {i+1}. {etiqueta} | {columna} | faltantes={faltantes[i]}")
        print("DIFERENCIAS DE EXTRACCION:",len(diferencias))
        for x in diferencias: print("ERROR:",x)
        for n,item in enumerate(muestras,1):
            print("MUESTRA REAL",n)
            for i,(etiqueta,columna,campo) in enumerate(COLUMNAS):
                valor=item.get(campo)
                print(f" {i+1}. {etiqueta}: {valor if valor else (AVISO if i in FECHAS else 'No disponible')}")
        if diferencias: raise SystemExit("PRUEBA RECHAZADA: diferencias contra CSV")
        if not muestras: raise SystemExit("PRUEBA RECHAZADA: no se encontraron muestras")
        print("PRUEBA DE EXTRACCION APROBADA. Solo lectura; cero correos; cero escrituras.")
if __name__=="__main__": probar()
