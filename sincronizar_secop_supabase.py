"""Sincroniza fichas SECOP previamente revisadas. Predeterminado: simulación.
Uso: py sincronizar_secop_supabase.py
     py sincronizar_secop_supabase.py --importar
Requiere SUPABASE_URL y SUPABASE_ADMIN_KEY solo al importar.
"""
import argparse
import json
import os
import re
from pathlib import Path
from urllib.parse import urlparse

ARCHIVO = Path(__file__).resolve().parent / "documentos_secop_lote" / "secop_importacion_pendiente_revision.json"
CAMPOS = ("uuid_procedimiento", "fuente", "numero_procedimiento", "cod_expediente",
          "nombre_procedimiento", "descripcion", "entidad_federativa", "estatus",
          "fecha_publicacion", "fecha_junta_aclaraciones", "fecha_apertura",
          "fecha_fallo_programado", "url_procedimiento", "documentos_disponibles",
          "url_bases", "url_convocatoria", "documentos_bases_verificados",
          "documentos_convocatorias_verificados", "validacion_calendario")

def enlace_oficial(url):
    p = urlparse(str(url or ""))
    return (p.scheme == "https" and p.hostname == "www.sefincoahuila.gob.mx"
            and bool(re.fullmatch(r"/sistemas/Secop/Procedimiento/GetFile/\d+", p.path, re.I))
            and not p.query and not p.fragment and not p.username and not p.password)

def preparar(registro):
    if registro.get("fuente") != "SECOP Coahuila":
        raise ValueError("Fuente no permitida")
    uuid = str(registro.get("uuid_procedimiento") or "")
    if not re.fullmatch(r"secop-coahuila:[a-z0-9][a-z0-9/._-]{1,150}", uuid):
        raise ValueError("Identificador SECOP inválido")
    if not registro.get("cod_expediente") or not registro.get("nombre_procedimiento"):
        raise ValueError("Faltan código u objeto")
    item = {k: registro[k] for k in CAMPOS if k in registro}
    bases = registro.get("documentos_bases_verificados") or []
    convocatorias = registro.get("documentos_convocatorias_verificados") or []
    for documento in bases + convocatorias:
        if not isinstance(documento, dict) or not enlace_oficial(documento.get("url")):
            raise ValueError("Documento con URL no oficial")
    if registro.get("url_bases") and (not enlace_oficial(registro["url_bases"]) or
                                     registro["url_bases"] not in [d["url"] for d in bases]):
        raise ValueError("Bases no coinciden con evidencia")
    if registro.get("url_convocatoria") and (not enlace_oficial(registro["url_convocatoria"]) or
                                            registro["url_convocatoria"] not in [d["url"] for d in convocatorias]):
        raise ValueError("Convocatoria no coincide con evidencia")
    item["documentos_bases_verificados"] = bases
    item["documentos_convocatorias_verificados"] = convocatorias
    item["documentos_disponibles"] = [
        {"tipo": tipo, "texto": d.get("texto") or tipo, "url": d["url"]}
        for tipo, docs in (("bases", bases), ("convocatoria", convocatorias)) for d in docs
    ]
    # Nunca promover automáticamente una fecha extraída a calendario confirmado.
    item["validacion_calendario"] = "pendiente"
    return item

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--importar", action="store_true")
    args = parser.parse_args()
    datos = json.loads(ARCHIVO.read_text(encoding="utf-8-sig"))
    registros = [preparar(r) for r in datos.get("registros", [])]
    ids = [r["uuid_procedimiento"] for r in registros]
    if len(ids) != len(set(ids)):
        raise ValueError("Lote con identificadores duplicados")
    print("SECOP registros revisados estructuralmente:", len(registros))
    print("Enlaces bases:", sum(bool(r.get("url_bases")) for r in registros))
    print("Enlaces convocatorias:", sum(bool(r.get("url_convocatoria")) for r in registros))
    if not args.importar:
        print("SIMULACIÓN: no se escribió en Supabase.")
        return
    if datos.get("estado") != "VALIDACION_OFICIAL_CONFIRMADA":
        raise SystemExit("Importación bloqueada: falta confirmación documental explícita del lote.")
    if not registros:
        raise SystemExit("Sin registros para importar.")
    url, key = os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_ADMIN_KEY")
    if not url or not key:
        raise SystemExit("Faltan SUPABASE_URL o SUPABASE_ADMIN_KEY.")
    from supabase import create_client
    db = create_client(url, key)
    for r in registros:
        db.table("licitaciones").upsert(r, on_conflict="uuid_procedimiento").execute()
    print("Importados o actualizados:", len(registros))
    print("Alertas SECOP bloqueadas hasta confirmar calendario y enlace individual.")

if __name__ == "__main__":
    main()
