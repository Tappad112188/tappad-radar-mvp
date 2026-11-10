"""Auditoria conservadora de documentos posteriores SECOP. Solo lectura."""
import json
import hashlib
import zipfile
import posixpath
import re
import unicodedata
from pathlib import Path

BASE = Path(__file__).resolve().parent / "documentos_secop_lote"
ORIGEN = BASE / "reporte_descargas.json"
DESTINO = BASE / "revision_modificaciones_secop.json"
PATRON = re.compile(r"\b(?:acta|aclaracion(?:es)?|modificaci[oó]n(?:es)?|diferimiento|pr[oó]rroga|addenda|adenda|fe\s+de\s+erratas|cambio\s+de\s+fecha)\b", re.I)

def normalizar(texto):
    return "".join(c for c in unicodedata.normalize("NFD", str(texto or "").lower()) if unicodedata.category(c) != "Mn")

def cotejar_bases_pdf_zip(item):
    """Compara por SHA-256 un PDF descargado y su copia exacta en un ZIP local."""
    archivos = item.get("archivos") or []
    pdfs = [a for a in archivos if str(a.get("nombre", "")).lower().endswith(".pdf")]
    zips = [a for a in archivos if str(a.get("nombre", "")).lower().endswith(".zip")]
    resultados = []
    diagnosticos = []
    for pdf in pdfs:
        ruta_pdf = Path(pdf.get("ruta") or "")
        if not ruta_pdf.is_file():
            diagnosticos.append({"documento": pdf.get("nombre"), "motivo": "PDF_NO_ENCONTRADO", "ruta": str(ruta_pdf)})
            continue
        hash_pdf = hashlib.sha256(ruta_pdf.read_bytes()).hexdigest()
        for paquete in zips:
            ruta_zip = Path(paquete.get("ruta") or "")
            if not ruta_zip.is_file():
                diagnosticos.append({"documento": paquete.get("nombre"), "motivo": "ZIP_NO_ENCONTRADO", "ruta": str(ruta_zip)})
                continue
            try:
                with zipfile.ZipFile(ruta_zip) as z:
                    coincidencias = 0
                    for entrada in z.infolist():
                        if entrada.is_dir() or posixpath.basename(entrada.filename).casefold() != ruta_pdf.name.casefold():
                            continue
                        coincidencias += 1
                        with z.open(entrada) as flujo:
                            sha_interno = hashlib.sha256()
                            for bloque in iter(lambda: flujo.read(1024 * 1024), b""):
                                sha_interno.update(bloque)
                            hash_interno = sha_interno.hexdigest()
                        resultados.append({
                            "pdf": pdf.get("nombre"), "paquete": paquete.get("nombre"),
                            "miembro": entrada.filename, "sha256_pdf": hash_pdf,
                            "sha256_interno": hash_interno,
                            "identicos": hash_pdf == hash_interno,
                        })
                    if coincidencias == 0:
                        diagnosticos.append({"documento": paquete.get("nombre"), "motivo": "PDF_NO_COINCIDE_POR_NOMBRE", "pdf": pdf.get("nombre")})
            except (OSError, ValueError, zipfile.BadZipFile, RuntimeError) as exc:
                diagnosticos.append({"documento": paquete.get("nombre"), "motivo": "ERROR_LECTURA_ZIP", "detalle": str(exc)})
    return resultados, diagnosticos


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
    cotejos, diagnosticos = cotejar_bases_pdf_zip(item)
    duplicado_confirmado = any(c["identicos"] for c in cotejos)
    # La igualdad de PDFs no resuelve la verificacion de los enlaces oficiales.
    errores_pendientes = list(errores)
    return {
        "codigo": item.get("codigo"),
        "documentos_potencialmente_modificatorios": hallazgos,
        "errores_descarga": errores,
        "errores_pendientes": errores_pendientes,
        "cotejos_pdf_zip": cotejos,
        "diagnosticos_cotejo": diagnosticos,
        "bases_duplicadas_confirmadas": duplicado_confirmado,
        "estado": "POSIBLE_MODIFICACION_REVISAR" if hallazgos else
                  "COBERTURA_INCOMPLETA_REVISAR" if errores_pendientes else
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
