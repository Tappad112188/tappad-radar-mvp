"""TAPPAD Radar: extrae texto y fechas candidatas de un expediente SECOP local.
No navega internet, no modifica bases de datos ni envía correos.
Requiere: py -m pip install pymupdf
"""
import argparse
import json
import re
import unicodedata
import zipfile
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree as ET

PATRON_FECHA = re.compile(r"(?<!\d)(\d{1,2})[/-](\d{1,2})[/-](20\d{2})(?!\d)")
ETAPAS = {
    "visita_obra": ["visita al lugar", "visita de obra", "visita a la obra"],
    "junta_aclaraciones": ["junta de aclaraciones"],
    "presentacion_apertura": ["presentación y apertura", "presentacion y apertura", "apertura de proposiciones", "apertura de propuestas"],
    "fallo_programado": ["fallo"],
    "inicio_obra": ["inicio de los trabajos", "inicio de obra"],
    "terminacion_obra": ["terminación de los trabajos", "terminacion de obra"],
}

def leer_docx(datos):
    import io
    with zipfile.ZipFile(io.BytesIO(datos)) as z:
        xml = z.read("word/document.xml")
    raiz = ET.fromstring(xml)
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    lineas = []
    for p in raiz.findall(".//w:p", ns):
        s = "".join(t.text or "" for t in p.findall(".//w:t", ns))
        if s.strip():
            lineas.append(s)
    return "\n".join(lineas)

def leer_pdf(datos):
    try:
        import pymupdf as fitz
    except ImportError:
        return [], "Falta PyMuPDF. Instala con: py -m pip install pymupdf"
    try:
        doc = fitz.open(stream=datos, filetype="pdf")
        paginas = [p.get_text("text") for p in doc]
        doc.close()
        if not any(p.strip() for p in paginas):
            return paginas, "PDF sin texto seleccionable: requiere OCR o revisión visual"
        return paginas, None
    except Exception as e:
        return [], f"No se pudo leer PDF: {e}"

def analizar_texto(texto, documento, pagina=None):
    lineas = [s.strip() for s in texto.splitlines() if s.strip()]
    hallazgos = []
    for i, linea in enumerate(lineas):
        contexto = " ".join(lineas[max(0,i-3):min(len(lineas),i+5)])
        for etapa, terminos in ETAPAS.items():
            if not any(normalizar(t) in normalizar(linea) for t in terminos):
                continue
            for m in PATRON_FECHA.finditer(contexto):
                try:
                    if m.group(1):
                        dia,mes,anio = map(int,m.group(1,2,3))
                    else:
                        dia=int(m.group(4));mes=MESES[normalizar(m.group(5))];anio=int(m.group(6))
                    fecha=datetime(anio,mes,dia).date().isoformat()
                except (ValueError,KeyError):
                    continue
                hallazgos.append({"campo_candidato":etapa,"fecha":fecha,"documento":documento,"pagina":pagina,"evidencia":contexto[:650],"validacion":"pendiente_revision"})
    return hallazgos

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("zip_expediente", help="Ruta al ZIP de bases y anexos")
    parser.add_argument("--convocatoria", help="PDF adicional de convocatoria (opcional)")
    args = parser.parse_args()
    origen = Path(args.zip_expediente).expanduser().resolve()
    if not origen.is_file():
        parser.error(f"No existe el archivo: {origen}")
    resultado = {
        "expediente": origen.name, "documentos": [],
        "fechas_candidatas": [], "advertencias": [],
        "estado": "extraccion_preliminar_sin_validacion"
    }
    def procesar(nombre, datos):
        sufijo = Path(nombre).suffix.lower()
        if sufijo not in (".pdf", ".docx"):
            return
        registro = {"nombre": nombre, "tipo": sufijo, "paginas": 0, "texto_extraido": False}
        if sufijo == ".pdf":
            paginas, error = leer_pdf(datos)
        else:
            try:
                paginas, error = [leer_docx(datos)], None
            except Exception as e:
                paginas, error = [], str(e)
        registro["paginas"] = len(paginas)
        registro["texto_extraido"] = any(p.strip() for p in paginas)
        if error:
            registro["advertencia"] = error
            resultado["advertencias"].append({"documento": nombre, "motivo": error})
        for numero, texto in enumerate(paginas, 1):
            resultado["fechas_candidatas"].extend(analizar_texto(texto, nombre, numero))
        resultado["documentos"].append(registro)
    with zipfile.ZipFile(origen) as z:
        for item in z.infolist():
            if item.is_dir():
                continue
            if item.file_size > 40 * 1024 * 1024:
                resultado["advertencias"].append({"documento": item.filename, "motivo": "Archivo mayor a 40 MB, omitido"})
                continue
            procesar(item.filename, z.read(item))
    if args.convocatoria:
        convocatoria = Path(args.convocatoria).expanduser().resolve()
        if convocatoria.is_file():
            procesar(convocatoria.name, convocatoria.read_bytes())
        else:
            resultado["advertencias"].append({"documento": str(convocatoria), "motivo": "No encontrado"})
    resultado["fechas_candidatas"] = list({(x["campo_candidato"],x["fecha"],x["documento"],x["pagina"]):x for x in resultado["fechas_candidatas"]}.values())
    salida = origen.parent / "extraccion_expediente_secop.json"
    salida.write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Documentos analizados: {len(resultado['documentos'])}")
    print(f"Fechas candidatas: {len(resultado['fechas_candidatas'])}")
    print(f"Advertencias: {len(resultado['advertencias'])}")
    print(f"Reporte: {salida}")
    print("IMPORTANTE: las fechas son candidatas; no se usarán como oficiales sin validación.")

if __name__ == "__main__":
    main()
