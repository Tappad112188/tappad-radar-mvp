"""Prueba aislada de Gmail para ComprasMX. No escribe en Supabase ni cambia workflows."""
import argparse
import html
import json
import os
import smtplib
from datetime import datetime
from email.message import EmailMessage
from email.utils import make_msgid
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
SALIDA = ROOT / "documentos_secop_lote" / "vista_previa_correo_comprasmx.html"
DESTINATARIOS = ("tappadcons@gmail.com", "gerardotapia112188@gmail.com")

def consulta():
    base = os.environ.get("SUPABASE_URL", "").rstrip("/")
    key = os.environ.get("SUPABASE_ADMIN_KEY") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not base or not key:
        raise SystemExit("Faltan SUPABASE_URL o SUPABASE_ADMIN_KEY")
    params = urlencode({
        "select": "numero_procedimiento,nombre_procedimiento,fecha_publicacion,fecha_junta_aclaraciones,fecha_apertura,fecha_fallo_programado,url_procedimiento,fuente,estatus",
        "fuente": "eq.ComprasMX",
        "numero_procedimiento": "not.is.null",
        "url_procedimiento": "not.is.null",
        "order": "fecha_publicacion.desc.nullslast",
        "limit": 2
    })
    req = Request(base + "/rest/v1/licitaciones?" + params,
                  headers={"apikey": key, "Authorization": "Bearer " + key})
    with urlopen(req, timeout=40) as response:
        rows = json.load(response)
    if len(rows) != 2:
        raise SystemExit("Se esperaban dos expedientes ComprasMX para la prueba; encontrados: " + str(len(rows)))
    return rows

def esc(v):
    return html.escape(str(v or ""), quote=True)

def fecha(v, solo_dia=False):
    if not v:
        return "No identificada; consultar publicación oficial"
    try:
        dt = datetime.fromisoformat(str(v).replace("Z", "+00:00"))
        return dt.strftime("%d/%m/%Y") if solo_dia else dt.strftime("%d/%m/%Y a las %H:%M h")
    except ValueError:
        return esc(v)

def logo_local():
    for carpeta in (ROOT / "assets", ROOT):
        for nombre in ("logo_tappad.png", "logo_tappad.jpg", "logo_tappad.jpeg"):
            ruta = carpeta / nombre
            if ruta.is_file():
                return ruta
    return None

def ficha(r):
    if r.get("fuente") != "ComprasMX":
        raise SystemExit("Fuente incorrecta: " + str(r.get("fuente")))
    url = r.get("url_procedimiento") or ""
    if not url.startswith("https://"):
        raise SystemExit("URL oficial inválida")
    campos = (
        ("Publicación", r.get("fecha_publicacion")),
        ("Junta de aclaraciones", r.get("fecha_junta_aclaraciones")),
        ("Presentación y apertura / límite de propuestas", r.get("fecha_apertura")),
        ("Fallo programado", r.get("fecha_fallo_programado"))
    )
    filas = "".join(
        "<tr><th style='text-align:left;padding:8px;border-bottom:1px solid #ddd'>" + esc(k) +
        "</th><td style='padding:8px;border-bottom:1px solid #ddd'>" +
        fecha(v, solo_dia=(k == "Publicación")) + "</td></tr>"
        for k, v in campos
    )
    return (
        "<section style='padding:20px;background:#fff;border:1px solid #dce3ea;margin:16px 0;border-radius:8px'>"
        "<h2>" + esc(r.get("numero_procedimiento")) + "</h2><p>" +
        esc(r.get("nombre_procedimiento")) + "</p><table style='width:100%'>" + filas +
        "</table><p><a href='" + esc(url) +
        "' style='display:inline-block;padding:11px 15px;background:#163e69;color:white;text-decoration:none;border-radius:6px'>"
        "Consultar procedimiento oficial</a></p></section>"
    )

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--enviar", action="store_true")
    args = p.parse_args()
    rows = consulta()
    logo = logo_local()
    cid = make_msgid(domain="tappad.local") if logo else None
    imagen = ('<img src="cid:' + cid[1:-1] +
              '" alt="TAPPAD Consultoría" width="160" style="display:block;max-width:160px;height:auto;margin-bottom:12px">'
              if cid else "")
    cuerpo = (
        "<html><body style='font-family:Arial,sans-serif;color:#182b40;background:#f5f7fa;max-width:760px;margin:auto'>"
        "<header style='background:#163e69;color:white;padding:24px'>" + imagen +
        "<h1>TAPPAD Radar</h1><p>PRUEBA INTERNA | Oportunidades ComprasMX</p></header>"
        + "".join(ficha(r) for r in rows) +
        "<footer style='padding:22px'><h3>¿Necesitas apoyo para participar?</h3>"
        "<p>TAPPAD Consultoría te apoya en la revisión de bases, preparación documental y presentación de propuestas.</p>"
        "<p>Prueba interna. Verifica fechas y documentos oficiales antes de participar.</p></footer></body></html>"
    )
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    SALIDA.write_text(cuerpo, encoding="utf-8")
    print("ComprasMX:", len(rows), "| HTML:", SALIDA)
    print("Logo:", logo if logo else "No encontrado")
    print("Procedimientos:", ", ".join(str(r["numero_procedimiento"]) for r in rows))
    print("Destinatarios de prueba:", ", ".join(DESTINATARIOS))
    if not args.enviar:
        print("SIMULACION: sin envio. Para enviar usar --enviar")
        return
    usuario = os.environ.get("SMTP_USER", "").strip()
    clave = os.environ.get("SMTP_APP_PASSWORD", "")
    if usuario.lower() not in DESTINATARIOS or not clave:
        raise SystemExit("Remitente no autorizado o faltan credenciales SMTP. Sin envío.")
    msg = EmailMessage()
    msg["Subject"] = "PRUEBA INTERNA | TAPPAD Radar | 2 licitaciones ComprasMX"
    msg["From"] = usuario
    msg["To"] = ", ".join(DESTINATARIOS)
    msg.set_content("Prueba interna ComprasMX. Consulta el correo HTML.")
    msg.add_alternative(cuerpo, subtype="html")
    if logo:
        subtipo = "png" if logo.suffix.lower() == ".png" else "jpeg"
        msg.get_payload()[-1].add_related(
            logo.read_bytes(), maintype="image", subtype=subtipo, cid=cid, filename=logo.name
        )
    with smtplib.SMTP("smtp.gmail.com", 587, timeout=35) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.ehlo()
        smtp.login(usuario, clave)
        smtp.send_message(msg)
    print("Gmail acepto el mensaje para las dos cuentas de prueba; confirma recepción en ambas.")

if __name__ == "__main__":
    main()
