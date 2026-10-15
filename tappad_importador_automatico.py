"""TAPPAD Radar: descarga e importación controlada de expedientes ComprasMX.

Modo prueba (sin escrituras):
    python tappad_importador_automatico.py --dias 2 --limite 1000

Modo importación (requiere SUPABASE_URL y SUPABASE_ADMIN_KEY):
    python tappad_importador_automatico.py --dias 2 --limite 1000 --importar
"""
import argparse
import csv
import os
import re
import shutil
import tempfile
import urllib.request
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

CSV_URL = (
    "https://upcp-cnetservicios.buengobierno.gob.mx/norah/documentos/"
    "recursos/lck/expedientes/obtener/Expedientes_ComprasMX_2026.csv"
)
UUID_RE = re.compile(r"/detalle/([0-9a-f]{32})/procedimiento", re.I)


def fecha(valor):
    try:
        return datetime.fromisoformat((valor or "").strip())
    except (ValueError, TypeError):
        return None


def registro(fila):
    def campo(nombre):
        return (fila.get(nombre) or "").strip() or None

    url = campo("Dirección del anuncio") or ""
    match = UUID_RE.search(url)
    if not match:
        return None
    return {
        "uuid_procedimiento": match.group(1).lower(),
        "numero_procedimiento": campo("Número de procedimiento/proyecto"),
        "cod_expediente": campo("Código del expediente"),
        "nombre_procedimiento": campo("Nombre anuncio") or campo("Título del expediente"),
        "descripcion": campo("Descripción anuncio"),
        "nombre_dependencia": campo("Institución"),
        "unidad_compradora": campo("Nombre de la UC"),
        "tipo_procedimiento": campo("Tipo Procedimiento"),
        "tipo_contratacion": campo("Tipo de contratación"),
        "estatus": campo("Estatus procedimiento"),
        "entidad_federativa": campo("Entidad Federativa"),
        "fecha_publicacion": campo("Fecha publicación"),
        "fecha_apertura": campo("Fecha apertura"),
        "fecha_fallo": campo("Fecha de fallo"),
        "forma_participacion": campo("Forma de participación"),
        "caracter": campo("Carácter del anuncio"),
        "fuente": "ComprasMX",
        "url_procedimiento": url,
    }


def main():
    parser = argparse.ArgumentParser(description="Descarga CSV ComprasMX e importa expedientes nuevos")
    parser.add_argument("--dias", type=int, default=2)
    parser.add_argument("--limite", type=int, default=1000)
    parser.add_argument("--importar", action="store_true")
    args = parser.parse_args()
    if args.dias < 0 or not 1 <= args.limite <= 1000:
        parser.error("--dias debe ser >= 0 y --limite debe estar entre 1 y 1000")

    with tempfile.TemporaryDirectory() as folder:
        ruta = Path(folder) / "Expedientes_ComprasMX_2026.csv"
        print("Descargando CSV oficial de ComprasMX...")
        request = urllib.request.Request(CSV_URL, headers={"User-Agent": "TAPPAD-Radar/1.0"})
        with urllib.request.urlopen(request, timeout=180) as response, ruta.open("wb") as out:
            shutil.copyfileobj(response, out)
        if ruta.stat().st_size < 1000:
            raise RuntimeError("Descarga demasiado pequeña para ser el CSV esperado")

        items = {}
        total = sin_uuid = 0
        max_fecha = None
        with ruta.open("r", encoding="latin1", newline="") as archivo:
            lector = csv.DictReader(archivo)
            requeridas = {"Dirección del anuncio", "Fecha publicación", "Número de procedimiento/proyecto"}
            if not requeridas.issubset(set(lector.fieldnames or [])):
                raise RuntimeError("El CSV no contiene los encabezados esperados")
            for fila in lector:
                total += 1
                item = registro(fila)
                if item is None:
                    sin_uuid += 1
                    continue
                pub = fecha(item["fecha_publicacion"])
                if pub and (max_fecha is None or pub > max_fecha):
                    max_fecha = pub
                items[item["uuid_procedimiento"]] = item

        if max_fecha is None:
            raise RuntimeError("El CSV no contiene fechas válidas")
        if datetime.now() - max_fecha > timedelta(days=7):
            raise RuntimeError(f"CSV desactualizado: última publicación {max_fecha}")
        desde = max_fecha - timedelta(days=args.dias)
        seleccion = [item for item in items.values()
                     if (fecha(item["fecha_publicacion"]) or datetime.min) >= desde]
        seleccion.sort(key=lambda item: item["fecha_publicacion"], reverse=True)
        seleccion = seleccion[:args.limite]
        print(f"Filas: {total:,} | UUID únicos: {len(items):,} | Sin UUID: {sin_uuid:,}")
        print(f"Última publicación: {max_fecha} | Desde: {desde} | Seleccionados: {len(seleccion)}")
        print("Estatus:", dict(Counter(item["estatus"] or "(sin estatus)" for item in seleccion)))
        for item in seleccion[:3]:
            print("Ejemplo:", item["numero_procedimiento"])
        if not args.importar:
            print("MODO PRUEBA: no se escribió nada en Supabase.")
            return

        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_ADMIN_KEY")
        if not url or not key:
            raise RuntimeError("Faltan SUPABASE_URL o SUPABASE_ADMIN_KEY")
        from supabase import create_client
        db = create_client(url, key)
        nuevos = existentes = 0
        for item in seleccion:
            uuid = item["uuid_procedimiento"]
            consulta = db.table("licitaciones").select("id").eq("uuid_procedimiento", uuid).limit(1).execute()
            if consulta.data:
                existentes += 1
                continue
            db.table("licitaciones").insert(item, returning="minimal").execute()
            nuevos += 1
        print(f"Importación completada: {nuevos} nuevos, {existentes} existentes omitidos")


if __name__ == "__main__":
    main()
