"""Genera vista previa de alertas TAPPAD Radar desde fichas SECOP.
Solo archivos locales; NO envia correos ni escribe en Supabase.
Uso: py preparar_alertas_secop.py
"""
import html, json
from pathlib import Path
from datetime import datetime

BASE = Path(__file__).resolve().parent / "documentos_secop_lote"
ORIGEN = BASE / "fichas_comerciales_secop.json"
DESTINO = BASE / "alertas_clientes_vista_previa.html"

def escapar(valor):
    return html.escape(str(valor or "No disponible"))

def mostrar_fecha(item):
    if not isinstance(item, dict) or not item.get("fecha"):
        return "No identificada"
    fecha = item["fecha"]
    try:
        fecha = datetime.strptime(fecha, "%Y-%m-%d").strftime("%d/%m/%Y")
    except ValueError:
        pass
    return fecha + (" a las " + str(item["hora"]) if item.get("hora") else "")

def tarjeta(f):
    cal = f.get("calendario") or {}
    filas = [
        ("Publicación", f.get("publicacion") or "No identificada"),
        ("Junta de aclaraciones", mostrar_fecha(cal.get("junta_aclaraciones"))),
        ("Presentación de propuestas (fecha límite)", mostrar_fecha(cal.get("limite_presentacion_propuestas"))),
        ("Fallo programado", mostrar_fecha(cal.get("fallo_programado"))),
    ]
    cuerpo = "".join("<tr><th>" + escapar(k) + "</th><td>" + escapar(v) + "</td></tr>" for k,v in filas)
    return (
        '<section class="card"><h2>' + escapar(f.get("referencia") or f.get("codigo")) + '</h2>'
        '<p><strong>Objeto:</strong> ' + escapar(f.get("objeto")) + '</p>'
        '<p><strong>Fuente:</strong> SECOP Coahuila</p>'
        '<table>' + cuerpo + '</table>'
        '<p class="nota">Fechas programadas conforme a la información detectada. '
        'Consulta la publicación oficial para conocer posibles modificaciones.</p></section>'
    )

def main():
    if not ORIGEN.exists():
        raise SystemExit("No se encontró fichas_comerciales_secop.json")
    datos = json.loads(ORIGEN.read_text(encoding="utf-8-sig"))
    fichas = datos.get("fichas", [])
    if not fichas:
        raise SystemExit("Sin oportunidades: no se genera alerta")
    codigos = [f.get("codigo") for f in fichas]
    if len(set(codigos)) != len(codigos):
        raise SystemExit("Hay procedimientos duplicados: revisar antes de preparar alertas")
    pagina = """<!doctype html><html lang="es"><head><meta charset="utf-8">
<title>TAPPAD Radar | Vista previa de oportunidades</title>
<style>body{font-family:Arial,sans-serif;background:#f4f6f9;color:#182638;max-width:760px;margin:32px auto;padding:0 18px}
header{background:#132b48;color:white;padding:24px;border-radius:12px}header h1{margin:0}
.card{background:white;border:1px solid #dce2ea;border-radius:12px;padding:22px;margin:18px 0}
table{width:100%;border-collapse:collapse}th,td{text-align:left;padding:11px;border-bottom:1px solid #e5e9ef}
th{width:48%}.nota{font-size:13px;color:#586777}.cta{background:#e9f1f9;padding:20px;border-radius:12px}
</style></head><body><header><h1>TAPPAD Radar</h1><p>Nuevas oportunidades de contratación pública</p></header>"""
    pagina += "".join(tarjeta(f) for f in fichas)
    pagina += """<section class="cta"><h2>¿Te interesa participar?</h2>
<p>TAPPAD Consultoría puede asesorarte en el análisis de la convocatoria,
la preparación de tu propuesta y el seguimiento del procedimiento.</p>
<p>Responde a la alerta para solicitar información sobre nuestros servicios.</p></section>
<p class="nota">VISTA PREVIA INTERNA: este archivo no se envió a ningún cliente.</p>
</body></html>"""
    DESTINO.write_text(pagina, encoding="utf-8")
    print("Alertas preparadas:", len(fichas))
    for f in fichas:
        print(" -", f.get("codigo"), "|", f.get("referencia"))
    print("Vista previa:", DESTINO)
    print("SIN correos, SIN escrituras en Supabase, SIN destinatarios reales.")

if __name__ == "__main__":
    main()
