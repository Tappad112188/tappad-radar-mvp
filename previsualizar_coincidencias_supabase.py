"""TAPPAD Radar: previsualización de coincidencias REALES de Supabase.
Solo lectura. No envía correos ni modifica registros.
Variables: SUPABASE_URL y SUPABASE_ADMIN_KEY (o SUPABASE_SERVICE_ROLE_KEY).
"""
import json
import os
import re
from collections import defaultdict
from datetime import datetime
from urllib.parse import urlencode
from urllib.request import Request, urlopen

def obtener(tabla, columnas, filtros=""):
    base = os.environ["SUPABASE_URL"].rstrip("/")
    clave = os.environ.get("SUPABASE_ADMIN_KEY") or os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    url = f"{base}/rest/v1/{tabla}?select={columnas}&limit=1000"
    if filtros:
        url += "&" + filtros
    req = Request(url, headers={"apikey": clave, "Authorization": "Bearer " + clave})
    with urlopen(req, timeout=40) as r:
        return json.load(r)

def normalizar(s):
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFKD", str(s or "").lower()) if not unicodedata.combining(c))

def tokens(texto):
    return [normalizar(x).strip() for x in re.split(r"[,;\n]", texto or "") if len(x.strip()) >= 4]

def ubicacion_valida(licitacion, ubicaciones):
    if not ubicaciones:
        return True
    entidad = normalizar(licitacion.get("entidad_federativa"))
    return any(normalizar(u.get("estado")) in entidad or entidad in normalizar(u.get("estado"))
               for u in ubicaciones if entidad and u.get("estado"))

def main():
    clientes = obtener("clientes", "id,empresa,correo,palabras_clave,activo", "activo=eq.true")
    ubicaciones = obtener("clientes_ubicaciones", "cliente_id,estado,municipio")
    ubic_por_cliente = defaultdict(list)
    for u in ubicaciones:
        ubic_por_cliente[u["cliente_id"]].append(u)
    # Paginar: no limitar la búsqueda a las primeras 1000 licitaciones.
    licitaciones = []
    offset = 0
    while True:
        base = os.environ["SUPABASE_URL"].rstrip("/")
        clave = os.environ.get("SUPABASE_ADMIN_KEY") or os.environ["SUPABASE_SERVICE_ROLE_KEY"]
        cols = "id,numero_procedimiento,nombre_procedimiento,descripcion,fuente,entidad_federativa,estatus,fecha_apertura,validacion_calendario,url_procedimiento"
        url = f"{base}/rest/v1/licitaciones?select={cols}&order=id.asc&limit=500&offset={offset}"
        req = Request(url, headers={"apikey":clave,"Authorization":"Bearer "+clave})
        with urlopen(req, timeout=40) as r:
            lote = json.load(r)
        licitaciones.extend(lote)
        if len(lote) < 500:
            break
        offset += len(lote)
    coincidencias = 0
    print(f"PROVEEDORES ACTIVOS: {len(clientes)} | LICITACIONES CONSULTADAS: {len(licitaciones)}")
    for c in clientes:
        claves = tokens(c.get("palabras_clave"))
        hallazgos = []
        for l in licitaciones:
            texto = normalizar((l.get("nombre_procedimiento") or "") + " " + (l.get("descripcion") or ""))
            hits = [k for k in claves if k in texto]
            if hits and ubicacion_valida(l, ubic_por_cliente[c["id"]]):
                hallazgos.append((l, hits))
        print(f"\n{c['empresa']} — {len(hallazgos)} coincidencias preliminares")
        for l, hits in hallazgos[:15]:
            print(f"  {l['numero_procedimiento']} | {l['fuente']} | {l['validacion_calendario']} | palabras: {', '.join(hits)}")
        if len(hallazgos) > 15:
            print(f"  ... y {len(hallazgos)-15} adicionales")
        coincidencias += len(hallazgos)
    print(f"\nTOTAL PRELIMINAR: {coincidencias}. SIN ENVÍOS NI CAMBIOS EN SUPABASE.")
    print("Nota: coincidencia de texto y estado; aún falta integrar giros, vigencia y deduplicación.")

if __name__ == "__main__":
    main()
