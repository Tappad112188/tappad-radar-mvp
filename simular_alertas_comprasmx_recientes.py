"""Simulacion integral de alertas ComprasMX: SOLO LECTURA, SIN SMTP.
Usa licitaciones ya importadas a Supabase y ventana de publicacion local.
"""
import argparse
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from diagnosticar_vigencia_v4 import (
    consulta, norm, contiene, RUBROS, GENERICAS,
    estado_equivalente, objeto_principal,
)
from compuerta_alertas_v3 import evaluar, fecha_local

ZONA = ZoneInfo("America/Monterrey")

def simular(dias):
    hoy = datetime.now(ZONA).date()
    desde = hoy - timedelta(days=dias)
    clientes = consulta("clientes", "id,empresa,correo,activo,palabras_clave", {"activo": "eq.true"})
    giros = consulta("clientes_giros", "cliente_id,giro_id")
    ubicaciones = consulta("clientes_ubicaciones", "cliente_id,estado,municipio")
    licitaciones = consulta("licitaciones", "id,numero_procedimiento,nombre_procedimiento,descripcion,fuente,entidad_federativa,estatus,fecha_publicacion,fecha_apertura")
    historial = consulta("notificaciones_enviadas", "cliente_id,licitacion_id,estado")
    ocupados = {(r["cliente_id"], r["licitacion_id"]) for r in historial}
    gs, us = defaultdict(set), defaultdict(list)
    for g in giros:
        gs[g["cliente_id"]].add(g["giro_id"])
    for u in ubicaciones:
        us[u["cliente_id"]].append(u)
    candidatos = []
    motivos = Counter()
    for l in licitaciones:
        if norm(l.get("fuente")).strip() != "comprasmx":
            continue
        pub = fecha_local(l.get("fecha_publicacion"))
        if not pub or not desde <= pub.date() <= hoy:
            continue
        if norm(l.get("estatus")).strip() != "vigente":
            motivos["no_vigente"] += 1
            continue
        candidatos.append(l)
    ahora = datetime.now(ZONA).replace(tzinfo=None)
    print("SIMULACION TAPPAD RADAR | SIN CORREOS NI ESCRITURAS")
    print("Ventana de publicacion:", desde, "a", hoy)
    print("ComprasMX vigentes en Supabase:", len(candidatos))
    print("Proveedores activos:", len(clientes))
    print("Notificaciones historicas:", len(ocupados))
    total = 0
    for c in clientes:
        cid = c["id"]
        fuertes = [norm(x.strip()) for x in re.split(r"[,;\\n]", c.get("palabras_clave") or "") if len(x.strip()) >= 4]
        fuertes = [x for x in fuertes if x not in GENERICAS]
        coincidencias = []
        for l in candidatos:
            if (cid, l["id"]) in ocupados:
                motivos["ya_notificada"] += 1
                continue
            ok, razon = evaluar(l, cid, ocupados, ahora)
            if not ok:
                motivos[razon] += 1
                continue
            ubic = us[cid]
            entidad = norm(l.get("entidad_federativa"))
            if ubic and (not entidad or not any(estado_equivalente(x.get("estado"), entidad) for x in ubic)):
                motivos["fuera_de_ubicacion"] += 1
                continue
            texto = norm((l.get("nombre_procedimiento") or "") + " " + (l.get("descripcion") or ""))
            rubros = [g for g in gs[cid] if any(contiene(texto, k) for k in RUBROS.get(g, ()))]
            objeto = objeto_principal(l)
            if objeto is not None:
                if gs[cid] and objeto not in gs[cid]:
                    motivos["objeto_incompatible"] += 1
                    continue
                rubros = [g for g in rubros if g == objeto]
            palabras = [k for k in fuertes if contiene(texto, k)]
            if gs[cid] and not rubros:
                motivos["giro_sin_coincidencia"] += 1
                continue
            if not rubros and not palabras:
                motivos["sin_coincidencia"] += 1
                continue
            coincidencias.append(l)
        print("Proveedor", cid, "|", c.get("empresa"), "| oportunidades nuevas:", len(coincidencias))
        for l in coincidencias[:20]:
            print("  ", l.get("numero_procedimiento"), "|", l.get("fecha_publicacion"), "| id", l["id"])
        if len(coincidencias) > 20:
            print("  ... otras", len(coincidencias) - 20)
        total += len(coincidencias)
    print("TOTAL COINCIDENCIAS NUEVAS:", total)
    print("Descartes:", dict(motivos))
    print("SIMULACION FINALIZADA: sin SMTP, sin escrituras Supabase.")

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--ventana-dias", type=int, default=2)
    a = p.parse_args()
    if not 0 <= a.ventana_dias <= 7:
        p.error("--ventana-dias debe estar entre 0 y 7")
    simular(a.ventana_dias)
