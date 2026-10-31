"""Carga segura de catálogos oficiales SAT/CUCOP a Supabase.

Uso: python importar_catalogos_oficiales_tappad.py --archivo ruta.csv --simular
     python importar_catalogos_oficiales_tappad.py --archivo ruta.csv --ejecutar
Variables: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY. No envía correos.
CSV: sistema,clave,descripcion,version,fuente_url
"""
import argparse
import csv
import os
import urllib.request
import urllib.error
import json
from collections import Counter

def leer(archivo):
    with open(archivo, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        obligatorias = {"sistema","clave","descripcion","version","fuente_url"}
        if not obligatorias.issubset(reader.fieldnames or []):
            raise ValueError("Faltan columnas: " + str(obligatorias - set(reader.fieldnames or [])))
        vistos = set()
        for linea, r in enumerate(reader, start=2):
            r = {k:(r.get(k) or "").strip() for k in obligatorias}
            if r["sistema"] not in {"SAT","CUCOP"}:
                raise ValueError(f"Fila {linea}: sistema no permitido")
            if not all(r[k] for k in ("clave","descripcion","version")):
                raise ValueError(f"Fila {linea}: clave/descripcion/version vacíos")
            key = (r["sistema"],r["clave"],r["version"])
            if key in vistos:
                raise ValueError(f"Fila {linea}: clave duplicada {key}")
            vistos.add(key)
            yield r

def cargar(registros, tamano):
    url = os.environ["SUPABASE_URL"].rstrip("/") + "/rest/v1/catalogos_oficiales_tappad?on_conflict=sistema,clave,version"
    key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    for inicio in range(0,len(registros),tamano):
        lote = registros[inicio:inicio+tamano]
        req = urllib.request.Request(url, data=json.dumps(lote,ensure_ascii=False).encode("utf-8"),
            headers={"apikey":key,"Authorization":"Bearer "+key,"Content-Type":"application/json",
                     "Prefer":"resolution=merge-duplicates,return=minimal"}, method="POST")
        try:
            with urllib.request.urlopen(req,timeout=90) as res:
                if res.status not in (200,201,204):
                    raise RuntimeError("Error HTTP "+str(res.status))
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"Lote {inicio//tamano+1}: HTTP {e.code}: "+e.read(500).decode("utf-8","replace")) from e
        print(f"Importados {min(inicio+tamano,len(registros))}/{len(registros)}")

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--archivo",required=True)
    modo=p.add_mutually_exclusive_group(required=True)
    modo.add_argument("--simular",action="store_true")
    modo.add_argument("--ejecutar",action="store_true")
    p.add_argument("--lote",type=int,default=250)
    a=p.parse_args()
    if not 1<=a.lote<=500: p.error("--lote debe ser 1..500")
    registros=list(leer(a.archivo))
    print("Registros:",len(registros),"por sistema:",dict(Counter(r["sistema"] for r in registros)))
    if a.simular:
        print("SIMULACIÓN: no se escribió en Supabase")
        return
    cargar(registros,a.lote)
if __name__=="__main__": main()
