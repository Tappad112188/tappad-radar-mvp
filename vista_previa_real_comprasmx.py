"""Vista previa real de 10 expedientes ComprasMX desde Supabase, sin enviar correos."""
import json, os, urllib.parse, urllib.request
from pathlib import Path
from plantilla_correo_html import construir_correo_html
from prueba_10_expedientes_comprasmx import IDS

CAMPOS = [
    "Descripción del procedimiento:",
    "Número de procedimiento:",
    "Fecha de publicación:",
    "Fecha de Junta de aclaraciones:",
    "Fecha de apertura de proposiciones:",
    "Fecha de fallo:",
    "Enlace a documentos del procedimiento:",
]
AVISO = "Fecha no disponible, verificar enlace"

def main():
    base = os.environ["SUPABASE_URL"].rstrip("/")
    key = os.environ["SUPABASE_ADMIN_KEY"]
    qs = urllib.parse.urlencode({
        "select": "id,fuente,descripcion,numero_procedimiento,fecha_publicacion,fecha_junta_aclaraciones,fecha_apertura,fecha_fallo_programado,url_procedimiento",
        "id": "in.(" + ",".join(map(str, IDS)) + ")",
        "fuente": "eq.ComprasMX",
        "order": "id.asc",
    })
    req = urllib.request.Request(base + "/rest/v1/licitaciones?" + qs,
        headers={"apikey": key, "Authorization": "Bearer " + key})
    with urllib.request.urlopen(req, timeout=60) as response:
        oportunidades = json.load(response)
    if len(oportunidades) != len(IDS):
        raise RuntimeError("Se esperaban 10 registros reales; obtenidos: " + str(len(oportunidades)))
    html = construir_correo_html("Empresa de prueba TAPPAD", oportunidades)
    posiciones = [html.find(c) for c in CAMPOS]
    if any(p < 0 for p in posiciones) or posiciones != sorted(posiciones):
        raise AssertionError("Los siete campos no aparecen en el orden establecido")
    fechas_vacias = sum(not x.get(k) for x in oportunidades for k in
        ("fecha_publicacion","fecha_junta_aclaraciones","fecha_apertura","fecha_fallo_programado"))
    if html.count(AVISO) != fechas_vacias:
        raise AssertionError(f"Mensajes esperados {fechas_vacias}, encontrados {html.count(AVISO)}")
    for op in oportunidades:
        if op["numero_procedimiento"] not in html:
            raise AssertionError("Procedimiento faltante: " + op["numero_procedimiento"])
        if op.get("url_procedimiento") and op["url_procedimiento"] not in html:
            raise AssertionError("Enlace faltante: " + op["numero_procedimiento"])
    Path("vista_previa_comprasmx_real.html").write_text(html, encoding="utf-8")
    print(json.dumps({"expedientes":len(oportunidades),"campos_por_expediente":7,
        "fechas_vacias":fechas_vacias,"avisos_mostrados":html.count(AVISO),
        "enlaces_verificados_en_html":len(oportunidades),
        "archivo":"vista_previa_comprasmx_real.html","correos_enviados":0},ensure_ascii=False))
if __name__ == "__main__": main()
