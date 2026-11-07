"""Prepara lote ACTUAL de ComprasMX para clientes de prueba. Nunca envia ni escribe Supabase.

Reutiliza el emparejamiento existente; invalida el manifiesto anterior antes
de consultar para impedir que un fallo habilite un lote obsoleto.
SECOP queda fuera hasta integrar su seleccion y validacion documental.
"""
import hashlib
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from diagnosticar_vigencia_v4 import consulta
from compuerta_alertas_v3 import evaluar
from plantilla_correo_html import construir_correo_html
from preparar_plan_controlado_comprasmx import preparar, CLIENTES_PRUEBA

BASE = Path(__file__).resolve().parent
PLAN = BASE / "plan_envios_seco_tappad.json"
MANIFIESTO = BASE / "manifiesto_notificaciones_tappad.json"
CARPETA = BASE / "borradores_gmail_tappad_v3"
CAMPOS = ("id,fuente,numero_procedimiento,nombre_procedimiento,descripcion,"
          "fecha_publicacion,fecha_junta_aclaraciones,fecha_apertura,"
          "fecha_fallo_programado,url_procedimiento,estatus,validacion_calendario")


def invalidar_manifiesto():
    # El motor de entrega solo acepta SOLO_PREPARACION.
    MANIFIESTO.write_text(
        json.dumps({"modo": "INVALIDADO_REGENERAR", "proveedores": []}),
        encoding="utf-8",
    )


def main():
    invalidar_manifiesto()
    # El generador solo acepta los dos buzones autorizados y omite pares notificados.
    preparar()
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    if plan.get("modo") != "SIMULACION_SIN_ENVIO":
        raise SystemExit("Plan no autorizado")
    lotes = plan.get("proveedores") or []
    if not lotes:
        raise SystemExit("No hay coincidencias nuevas")
    ids = [lid for lote in lotes for lid in lote["licitacion_ids"]]
    if len(ids) != len(set(ids)):
        # Una misma licitacion SI puede corresponder a clientes distintos.
        if any(len(x["licitacion_ids"]) != len(set(x["licitacion_ids"])) for x in lotes):
            raise SystemExit("Duplicados dentro de un cliente")
    clientes = {c["id"]: c for c in consulta(
        "clientes", "id,empresa,correo,activo", {"activo": "eq.true"}
    )}
    oportunidades = {l["id"]: l for l in consulta(
        "licitaciones", CAMPOS,
        {"id": "in.(" + ",".join(map(str, sorted(set(ids)))) + ")"}
    )}
    ocupados = {(r["cliente_id"], r["licitacion_id"]) for r in consulta(
        "notificaciones_enviadas", "cliente_id,licitacion_id,estado"
    )}
    ahora = datetime.now(ZoneInfo("America/Monterrey")).replace(tzinfo=None)
    CARPETA.mkdir(exist_ok=True)
    manifiesto = []
    for lote in lotes:
        cid = lote["cliente_id"]
        cliente = clientes.get(cid)
        if not cliente or cid not in CLIENTES_PRUEBA:
            raise SystemExit("Cliente fuera de lista de pruebas: " + str(cid))
        if str(cliente.get("correo") or "").strip().casefold() != CLIENTES_PRUEBA[cid]:
            raise SystemExit("Correo no autorizado: " + str(cid))
        licitaciones = []
        for lid in lote["licitacion_ids"]:
            lic = oportunidades.get(lid)
            if not lic or str(lic.get("fuente") or "").casefold().strip() != "comprasmx":
                raise SystemExit("Licitacion ausente o fuente no autorizada: " + str(lid))
            ok, motivo = evaluar(lic, cid, ocupados, ahora)
            if not ok:
                raise SystemExit("Preflight rechazado " + str(cid) + "/" + str(lid) + ": " + motivo)
            licitaciones.append(lic)
        html = construir_correo_html(cliente["empresa"], licitaciones)
        if "cid:tappad-logo" not in html:
            raise SystemExit("Falta logo CID")
        archivo = CARPETA / ("correo_actual_comprasmx_cliente_" + str(cid) + ".html")
        archivo.write_text(html, encoding="utf-8")
        manifiesto.append({
            "cliente_id": cid, "licitacion_ids": lote["licitacion_ids"],
            "html": archivo.name,
            "sha256_html": hashlib.sha256(html.encode("utf-8")).hexdigest(),
            "destinatario_configurado": True,
        })
    salida = {
        "modo": "SOLO_PREPARACION",
        "generado_en": datetime.now(ZoneInfo("America/Monterrey")).isoformat(),
        "fuentes": ["ComprasMX"],
        "proveedores": manifiesto,
        "cantidad_correos": len(manifiesto),
        "cantidad_oportunidades": sum(len(x["licitacion_ids"]) for x in manifiesto),
    }
    # Publicar solo tras completar TODAS las validaciones.
    MANIFIESTO.write_text(json.dumps(salida, ensure_ascii=False, indent=2), encoding="utf-8")
    print("MANIFIESTO ACTUAL:", salida["generado_en"])
    print("CORREOS:", salida["cantidad_correos"],
          "| OPORTUNIDADES:", salida["cantidad_oportunidades"])
    print("SOLO COMPRASMX. SIN SMTP NI ESCRITURAS SUPABASE.")


if __name__ == "__main__":
    main()
