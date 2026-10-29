"""Importa oportunidades SECOP vigentes del día desde un reporte validado.
No envía correos. Conserva fecha de primera detección y registros existentes.
"""
import argparse
import json
import os
import re
from datetime import date
from pathlib import Path
from zoneinfo import ZoneInfo
from datetime import datetime

ROOT = Path(__file__).resolve().parent

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--archivo", default=str(ROOT / "secop_vigentes_hoy.json"))
    p.add_argument("--importar", action="store_true")
    args = p.parse_args()
    reporte = json.loads(Path(args.archivo).read_text(encoding="utf-8-sig"))
    hoy = datetime.now(ZoneInfo("America/Monterrey")).date().isoformat()
    if reporte.get("fecha_consulta") != hoy:
        raise SystemExit("Reporte SECOP no corresponde a la fecha local de hoy")
    if not reporte.get("filtros_servidor_confirmados"):
        raise SystemExit("Filtro SECOP no validado; importación cancelada")
    if reporte.get("total_validado_fecha_y_estatus") != len(reporte.get("registros", [])):
        raise SystemExit("Conteo SECOP inconsistente")
    archivo_calendarios = ROOT / "secop_calendarios_automaticos.json"
    if not archivo_calendarios.exists():
        raise SystemExit("Falta reporte documental SECOP")
    documental = json.loads(archivo_calendarios.read_text(encoding="utf-8"))
    if documental.get("fecha_consulta") != hoy:
        raise SystemExit("Reporte documental SECOP no corresponde a hoy")
    calendarios = {r["codigo"]: r for r in documental.get("resultados", [])}
    registros = []
    vistos = set()
    for r in reporte["registros"]:
        if r.get("estatus", "").casefold() != "vigente" or r.get("fecha_publicacion_original") != datetime.fromisoformat(hoy).strftime("%d/%m/%Y"):
            raise SystemExit("Registro fuera de filtro: " + str(r.get("codigo")))
        codigo = (r.get("codigo") or "").strip()
        if not codigo:
            raise SystemExit("SECOP devolvió registro sin código")
        uid = "secop-coahuila:" + re.sub(r"[^a-z0-9-]", "", codigo.casefold())
        if uid in vistos:
            raise SystemExit("Código SECOP repetido en extracción: " + codigo)
        vistos.add(uid)
        detalle = calendarios.get(codigo, {})
        fechas = detalle.get("calendario", {})
        registros.append({
            "uuid_procedimiento": uid,
            "numero_procedimiento": codigo,
            "nombre_procedimiento": r.get("descripcion") or codigo,
            "descripcion": r.get("descripcion") or None,
            "fuente": "SECOP Coahuila",
            "estatus": "Vigente",
            "entidad_federativa": "Coahuila",
            "fecha_publicacion": hoy,
            **{k: v for k, v in fechas.items() if k in ("fecha_junta_aclaraciones", "fecha_apertura", "fecha_fallo_programado")},
            "url_convocatoria": "https://www.sefincoahuila.gob.mx/sistemas/Secop/Convocatoria"
        })
    print("SECOP: candidatos vigentes publicados hoy:", len(registros))
    if not args.importar:
        print("SIMULACIÓN: sin escrituras ni envíos")
        return
    if not registros:
        print("No hay oportunidades nuevas para importar")
        return
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_ADMIN_KEY")
    if not url or not key:
        raise SystemExit("Faltan secretos Supabase")
    from supabase import create_client
    db = create_client(url, key)
    nuevos = existentes = 0
    for r in registros:
        consulta = db.table("licitaciones").select("id,fecha_junta_aclaraciones,fecha_apertura,fecha_fallo_programado").eq("uuid_procedimiento", r["uuid_procedimiento"]).limit(1).execute()
        if consulta.data:
            existentes += 1
            anterior = consulta.data[0]
            completar = {k: r[k] for k in ("fecha_junta_aclaraciones", "fecha_apertura", "fecha_fallo_programado") if r.get(k) and not anterior.get(k)}
            if completar:
                db.table("licitaciones").update(completar).eq("id", anterior["id"]).execute()
            continue
        db.table("licitaciones").upsert(
            r, on_conflict="uuid_procedimiento", ignore_duplicates=True, returning="minimal"
        ).execute()
        nuevos += 1
    print("SECOP importado | nuevos candidatos:", nuevos, "| ya existentes:", existentes)
    print("Fechas no identificadas se conservan vacías para indicar revisión de bases en las alertas.")

if __name__ == "__main__":
    main()
