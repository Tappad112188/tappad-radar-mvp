"""Auditoria conservadora de documentos posteriores SECOP. Solo lectura."""
import json
import re
import unicodedata
from pathlib import Path

BASE = Path(__file__).resolve().parent / "documentos_secop_lote"
ORIGEN = BASE / "reporte_descargas.json"
DESTINO = BASE / "revision_modificaciones_secop.json"
PATRON = re.compile(r"\b(?:acta|aclaracion(?:es)?|modificaci[oó]n(?:es)?|diferimiento|pr[oó]rroga|addenda|adenda|fe\s+de\s+erratas|cambio\s+de\s+fecha)\b", re.I)

def normalizar(texto):
    return "".join(c for c in unicodedata.normalize("NFD", str(texto or "").lower()) if unicodedata.category(c) != "Mn")

def auditar_procedimiento(item):
    hallazgos = []
    vistos = set()
    fuentes = [
        ("enlace", item.get("enlaces_documentos") or []),
        ("archivo_descargado", item.get("archivos") or []),
    ]
    for tipo, elementos in fuentes:
        for elemento in elementos:
            nombre = elemento.get("texto") or elemento.get("nombre") or ""
            referencia = elemento.get("url") if tipo == "enlace" else elemento.get("ruta")
            if not PATRON.search(normalizar(nombre)):
                continue
            clave = (tipo, nombre, referencia)
            if clave in vistos:
                continue
            vistos.add(clave)
            hallazgos.append({"tipo": tipo, "documento": nombre, "referencia": referencia,
                              "estado": "REQUIERE_COTEJO_DOCUMENTAL"})
    errores = item.get("errores") or []
    return {
        "codigo": item.get("codigo"),
        "documentos_potencialmente_modificatorios": hallazgos,
        "errores_descarga": errores,
        "estado": "POSIBLE_MODIFICACION_REVISAR" if hallazgos else
                  "COBERTURA_INCOMPLETA_REVISAR" if errores else
                  "SIN_INDICIOS_EN_DOCUMENTOS_CAPTURADOS",
        "fechas_oficialmente_validadas": False,
        "advertencia": "Ausencia de indicios no acredita ausencia de modificaciones posteriores",
    }

def generar(datos):
    procedimientos = [auditar_procedimiento(x) for x in datos.get("procedimientos", [])]
    return {
        "fecha_fuente": datos.get("fecha_fuente"),
        "total": len(procedimientos),
        "procedimientos": procedimientos,
        "notificaciones_habilitadas": False,
        "escrituras_supabase": False,
    }

def main():
    if not ORIGEN.exists():
        raise SystemExit("Falta reporte_descargas.json; no se puede auditar")
    datos = json.loads(ORIGEN.read_text(encoding="utf-8-sig"))
    salida = generar(datos)
    DESTINO.write_text(json.dumps(salida, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Procedimientos auditados:", salida["total"])
    for item in salida["procedimientos"]:
        print(item["codigo"], "|", item["estado"], "| indicios:", len(item["documentos_potencialmente_modificatorios"]))
    print("Reporte:", DESTINO)
    print("Sin escrituras Supabase ni notificaciones.")

if __name__ == "__main__":
    main()
