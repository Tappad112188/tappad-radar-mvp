"""Genera una bandeja de revision documental SECOP, sin escrituras ni correos.

No convierte candidatos documentales en fechas oficialmente validadas.
Uso: py revisar_calendarios_secop.py
"""
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

BASE = Path(__file__).resolve().parent / "documentos_secop_lote"
ORIGEN = BASE / "fichas_comerciales_secop.json"
DESTINO = BASE / "revision_calendarios_secop.json"
ETAPAS = ("junta_aclaraciones", "limite_presentacion_propuestas", "fallo_programado")


def revisar_ficha(ficha):
    calendario = ficha.get("calendario") or {}
    eventos = {}
    for etapa in ETAPAS:
        dato = calendario.get(etapa) or {}
        fecha = dato.get("fecha")
        hora = dato.get("hora")
        evidencia = dato.get("evidencia")
        fuente = dato.get("fuente")
        estado_extraccion = dato.get("estado", "no_identificado")
        completo = bool(fecha and hora and evidencia and fuente)
        alternativas = dato.get("alternativas") or []
        conflicto = bool(alternativas) or estado_extraccion == "requiere_revision"
        estado_validacion = ("CONFLICTO_REVISAR_FECHAS" if conflicto else
                             "PENDIENTE_REVISION_HUMANA" if completo else
                             "INCOMPLETO_REVISAR_BASES")
        eventos[etapa] = {
            "fecha_candidata": fecha,
            "hora_candidata": hora,
            "estado_extraccion": estado_extraccion,
            "fuente_documental": fuente,
            "evidencia": evidencia,
            "alternativas": alternativas,
            "estado_validacion": estado_validacion,
        }
    return {
        "codigo": ficha.get("codigo"),
        "objeto": ficha.get("objeto"),
        "publicacion": ficha.get("publicacion"),
        "eventos": eventos,
        "apto_para_notificacion_con_fechas": False,
        "motivo": "Fechas candidatas; requieren cotejo con bases oficiales y modificaciones posteriores",
    }


def generar(datos):
    fichas = [revisar_ficha(f) for f in datos.get("fichas", [])]
    return {
        "fecha_consulta": datos.get("fecha_consulta"),
        "generado": datetime.now(ZoneInfo("America/Monterrey")).isoformat(timespec="seconds"),
        "estado": "SOLO_REVISION_SIN_PUBLICACION",
        "total": len(fichas),
        "fichas": fichas,
        "notificaciones_habilitadas": False,
        "escrituras_supabase": False,
    }


def main():
    if not ORIGEN.exists():
        raise SystemExit("Faltan fichas comerciales SECOP; no se genera revision")
    datos = json.loads(ORIGEN.read_text(encoding="utf-8-sig"))
    salida = generar(datos)
    DESTINO.write_text(json.dumps(salida, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Calendarios para revision:", salida["total"])
    print("Reporte:", DESTINO)
    print("Sin escrituras Supabase ni notificaciones.")


if __name__ == "__main__":
    main()
