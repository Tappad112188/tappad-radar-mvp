"""Envio de prueba historica de alertas consolidadas TAPPAD Radar.
Solo dos cuentas autorizadas, con confirmacion --enviar y --historico-prueba.
No modifica Supabase. Requiere SMTP_USER y SMTP_APP_PASSWORD en entorno local.
"""
import argparse
import json
import os
import smtplib
from datetime import date
from email.message import EmailMessage
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIR = ROOT / "documentos_secop_lote"
REPORTE = DIR / "cruce_giros_prueba_integral.json"
PERMITIDOS = {
    "tappadcons@gmail.com": "vista_previa_destino_tappadcons.html",
    "gerardotapia112188@gmail.com": "vista_previa_destino_gerardotapia.html",
}

def main():
    parser = argparse.ArgumentParser(description="Prueba historica Gmail, solo dos destinatarios")
    parser.add_argument("--historico-prueba", action="store_true", help="Autoriza contenido historico marcado como simulacion")
    parser.add_argument("--enviar", action="store_true", help="Autoriza enviar exclusivamente a las dos cuentas de prueba")
    args = parser.parse_args()
    if not REPORTE.exists():
        raise SystemExit("Falta reporte de cruce. Primero ejecutar cruce_giros_con_logo.py --historico-prueba")
    reporte = json.loads(REPORTE.read_text(encoding="utf-8-sig"))
    if reporte.get("fecha_prueba") != date.today().isoformat():
        raise SystemExit("Reporte de otra fecha. Regenerar el cruce antes del envio.")
    if not args.historico_prueba:
        raise SystemExit("Envio bloqueado: especificar --historico-prueba para autorizar simulacion historica.")
    if not reporte.get("modo_historico"):
        raise SystemExit("Este envio solo admite la simulacion historica previamente revisada.")
    if reporte.get("correos_enviados") != 0:
        raise SystemExit("El reporte no indica cero envios; revisar manualmente.")
    destinos = {x["correo_prueba"]: x for x in reporte.get("destinatarios_consolidados", [])}
    if not destinos or set(destinos) - set(PERMITIDOS):
        raise SystemExit("Destinatarios no autorizados o reporte sin destinatarios.")
    mensajes = []
    for correo, datos in sorted(destinos.items()):
        ruta = DIR / PERMITIDOS[correo]
        if not ruta.exists():
            raise SystemExit("No existe vista previa: " + str(ruta))
        contenido = ruta.read_text(encoding="utf-8")
        if ('SIMULACIÓN INTERNA' not in contenido or
            'NO ES UNA ALERTA DE LICITACIONES VIGENTES' not in contenido or
            'logo_tappad.png' not in contenido or
            'TAPPAD Radar' not in contenido):
            raise SystemExit("Vista previa sin advertencias o logo esperado: " + str(ruta))
        msg = EmailMessage()
        msg["To"] = correo
        msg["Subject"] = "[SIMULACIÓN HISTÓRICA - PRUEBA] TAPPAD Radar | " + str(datos.get("procedimientos_unicos", 0)) + " procedimientos"
        msg.set_content("SIMULACIÓN HISTÓRICA - PRUEBA INTERNA. No son alertas de licitaciones vigentes. Revisa el contenido HTML y verifica siempre las bases oficiales. TAPPAD Radar.")
        msg.add_alternative(contenido, subtype="html")
        mensajes.append((correo, msg))
    print("SIMULACIÓN HISTÓRICA: contenido de prueba, NO licitaciones vigentes")
    for correo, msg in mensajes:
        print("Destinatario:", correo, "| Asunto:", msg["Subject"])
    if not args.enviar:
        print("VISTA PREVIA: no se enviaron correos. Para enviar usar --historico-prueba --enviar")
        return
    usuario = os.environ.get("SMTP_USER", "").strip().lower()
    clave = os.environ.get("SMTP_APP_PASSWORD", "")
    if usuario not in PERMITIDOS or not clave:
        raise SystemExit("No hay remitente permitido y contraseña de aplicacion SMTP en este CMD. No se envio nada.")
    with smtplib.SMTP("smtp.gmail.com", 587, timeout=40) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.ehlo()
        smtp.login(usuario, clave)
        for correo, msg in mensajes:
            msg["From"] = usuario
            smtp.send_message(msg, from_addr=usuario, to_addrs=[correo])
            print("Gmail acepto el mensaje dirigido a:", correo)
    print("Fin. Sin modificaciones a Supabase. La aceptacion SMTP no confirma lectura ni entrega final.")

if __name__ == "__main__":
    main()
