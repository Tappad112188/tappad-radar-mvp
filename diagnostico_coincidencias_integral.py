"""Diagnostico de coincidencias TAPPAD (solo lectura, sin correos).

Ejecutar con SUPABASE_URL y SUPABASE_ADMIN_KEY:
  python diagnostico_coincidencias_integral.py
No sustituye el motor de alertas existente. Sirve para verificar datos
y localizar bloqueos antes de conectar los flujos automaticos.
"""
import json
import os
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timedelta, timezone

TABLAS = {
    "clientes": "id,empresa,activo,estado,ciudad,palabras_clave",
    "preferencias": "cliente_id,origen,descripcion,activo",
    "licitaciones": "id,fuente,numero_procedimiento,descripcion,nombre_procedimiento,entidad_federativa,fecha_publicacion,fecha_junta_aclaraciones,fecha_apertura,fecha_fallo,fecha_registro",
}

def consultar(tabla, select, extra=None):
    base = os.environ["SUPABASE_URL"].rstrip("/")
    clave = os.environ["SUPABASE_ADMIN_KEY"]
    cab = {"apikey": clave, "Accept": "application/json"}
    if not clave.startswith("sb_secret_"):
        cab["Authorization"] = "Bearer " + clave
    resultados = []
    for offset in range(0, 100000, 1000):
        params = {"select": select, "limit": "1000", "offset": str(offset)}
        if extra:
            params.update(extra)
        url = base + "/rest/v1/" + tabla + "?" + urllib.parse.urlencode(params)
        with urllib.request.urlopen(urllib.request.Request(url, headers=cab), timeout=30) as respuesta:
            lote = json.load(respuesta)
        resultados.extend(lote)
        if len(lote) < 1000:
            return resultados
    raise RuntimeError("Se alcanzo el limite de paginacion; no se emite un reporte parcial")

def diagnosticar():
    clientes = consultar("clientes", TABLAS["clientes"])
    preferencias = consultar("clientes_giros_preferencias_tappad", TABLAS["preferencias"])
    desde = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    licitaciones = consultar("licitaciones", TABLAS["licitaciones"],
                            {"fecha_registro": "gte." + desde})
    activas = [c for c in clientes if c.get("activo") is True]
    prefs = Counter(p["cliente_id"] for p in preferencias if p.get("activo") is True)
    fuentes = Counter(l["fuente"] for l in licitaciones)
    resumen = {
        "modo": "SOLO_LECTURA",
        "clientes_totales": len(clientes),
        "clientes_activos": len(activas),
        "clientes_activos_sin_ubicacion": sum(not (c.get("estado") or c.get("ciudad")) for c in activas),
        "clientes_activos_sin_giro_ni_palabras": sum(
            not prefs[c["id"]] and not (c.get("palabras_clave") or "").strip() for c in activas),
        "preferencias_activas": sum(prefs.values()),
        "licitaciones_ultimos_7_dias": len(licitaciones),
        "fuentes_ultimos_7_dias": dict(fuentes),
        "calendarios_incompletos": {
            campo: sum(not l.get(campo) for l in licitaciones)
            for campo in ("fecha_publicacion", "fecha_junta_aclaraciones", "fecha_apertura", "fecha_fallo")
        },
        "nota": "Fechas ausentes NO bloquean alertas; no se enviaron correos.",
    }
    return resumen

if __name__ == "__main__":
    print(json.dumps(diagnosticar(), ensure_ascii=False, indent=2))
