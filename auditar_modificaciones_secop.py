"""Auditoria conservadora de documentos posteriores SECOP. Solo lectura."""
import json
import hashlib
import zipfile
import re
import unicodedata
import subprocess
import shutil
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
                    pdfs_internos = 0
                    for entrada in z.infolist():
                        if entrada.is_dir() or not entrada.filename.casefold().endswith(".pdf"):
                            continue
                        pdfs_internos += 1
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
                    if pdfs_internos == 0:
                        diagnosticos.append({"documento": paquete.get("nombre"), "motivo": "ZIP_SIN_PDF", "pdf": pdf.get("nombre")})
            except (OSError, ValueError, zipfile.BadZipFile, RuntimeError) as exc:
                diagnosticos.append({"documento": paquete.get("nombre"), "motivo": "ERROR_LECTURA_ZIP", "detalle": str(exc)})
    return resultados, diagnosticos


def docx_local_integro(item):
    archivos = item.get("archivos") or []
    if len(archivos) != 1 or not str(archivos[0].get("nombre") or "").lower().endswith(".docx"):
        return False
    ruta = Path(archivos[0].get("ruta") or "")
    try:
        if not ruta.is_file() or ruta.stat().st_size <= 0:
            return False
        with zipfile.ZipFile(ruta) as z:
            return "word/document.xml" in z.namelist() and z.testzip() is None
    except (OSError, ValueError, zipfile.BadZipFile, RuntimeError):
        return False


def rar_bases_integras(item):
    """Verifica un RAR descargado del procedimiento y sus miembros con 7-Zip."""
    siete = shutil.which("7z") or shutil.which("7z.exe")
    if not siete:
        candidato = Path("C:/Program Files/7-Zip/7z.exe")
        siete = str(candidato) if candidato.is_file() else None
    if not siete:
        return False, "7-ZIP_NO_DISPONIBLE"
    codigo = str(item.get("codigo") or "")
    partes = re.search(r"(?:^|-)(IE|LPN|LP|AD|IR|INV|OP)(?:[-_]OP)?[-_](\d{2,4})[-_](20\d{2})$", codigo, re.I)
    abreviado = "-".join(partes.groups()) if partes else None
    archivos = [a for a in item.get("archivos") or [] if str(a.get("nombre") or "").lower().endswith(".rar")]
    if not archivos:
        return False, "RAR_NO_DESCARGADO"
    for archivo in archivos:
        ruta = Path(archivo.get("ruta") or "")
        if not ruta.is_file() or ruta.stat().st_size < 8:
            continue
        if ruta.open("rb").read(8) != bytes.fromhex("526172211a070100"):
            continue
        try:
            prueba = subprocess.run([siete, "t", str(ruta)], capture_output=True, timeout=120, check=False)
            if prueba.returncode != 0:
                continue
            listado = subprocess.run([siete, "l", "-slt", str(ruta)], capture_output=True,
                                    text=True, encoding="utf-8", errors="replace", timeout=90, check=True).stdout
            miembros = [x[7:].replace("\\\\", "/").rsplit("/", 1)[-1] for x in listado.splitlines() if x.startswith("Path = ")]
            bases = [x for x in miembros if re.match(r"^BASES\s+", x, re.I) and x.lower().endswith(".pdf")]
            validas = [x for x in bases if codigo.casefold() in x.casefold() or
                       (abreviado and re.search(r"(?<![A-Za-z0-9])"+re.escape(abreviado)+r"(?![A-Za-z0-9])", x, re.I))]
            if len(validas) == 1:
                return True, "RAR5_INTEGRO_BASES_UNICAS"
        except (OSError, subprocess.SubprocessError):
            continue
    return False, "RAR_SIN_BASES_UNICAS_O_INTEGRO"

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
    # Multiples enlaces de bases son habituales cuando SECOP ofrece un ZIP
    # de anexos y el PDF principal. No son por si mismos un error.
    multiples = "Multiples enlaces de bases: requieren revision"
    if multiples in errores_pendientes:
        archivos = item.get("archivos") or []
        nombres = [str(a.get("nombre") or "").lower() for a in archivos]
        hay_zip = any(n.endswith(".zip") for n in nombres)
        hay_pdf = any(n.endswith(".pdf") for n in nombres)
        rutas_validas = all(
            Path(a.get("ruta") or "").is_file()
            and Path(a.get("ruta") or "").stat().st_size > 0
            for a in archivos if str(a.get("nombre") or "").lower().endswith((".zip", ".pdf"))
        )
        # Exigir que se haya capturado al menos un ZIP y un PDF del mismo
        # procedimiento; no considerar la sola presencia de URLs como prueba.
        if hay_zip and hay_pdf and rutas_validas and not diagnosticos:
            errores_pendientes = [e for e in errores_pendientes if e != multiples]
    aviso = "Enlace de bases no confirmado sin sesion"
    docx_verificado = docx_local_integro(item)
    rar_integro, diagnostico_rar = rar_bases_integras(item)
    hay_rar = any(str(a.get("nombre") or "").lower().endswith(".rar")
                  for a in item.get("archivos") or [])
    # Nunca aprobar la auditoria si existen bases RAR cuya integridad no se comprobo.
    if hay_rar and not rar_integro:
        errores_pendientes.append("Integridad de bases RAR no confirmada: " + diagnostico_rar)
    # El enlace debe verificarse sin sesion y el RAR local debe pasar 7z t,
    # contener exactamente unas bases identificables y no tener otros errores.
    bases_verificadas = item.get("bases_verificadas") or []
    enlace_rar_verificado = (len(bases_verificadas) == 1
        and bases_verificadas[0].get("estado") == "verificado_sin_sesion"
        and item.get("estado_enlace") == "verificado_sin_sesion")
    if aviso in errores_pendientes and docx_verificado and not hallazgos and not diagnosticos:
        errores_pendientes = [e for e in errores_pendientes if e != aviso]
    if aviso in errores_pendientes and enlace_rar_verificado and rar_integro and not hallazgos and not diagnosticos:
        errores_pendientes = [e for e in errores_pendientes if e != aviso]
    return {
        "docx_local_integro": docx_verificado,
        "rar_bases_integro": rar_integro,
        "hay_rar": hay_rar,
        "diagnostico_rar": diagnostico_rar,
        "enlace_rar_verificado": enlace_rar_verificado,
        "enlace_anonimo_no_verificado": aviso in errores,
        "advertencias_no_bloqueantes": [aviso] if aviso in errores and docx_verificado else [],
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
