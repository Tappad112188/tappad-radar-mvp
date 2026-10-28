"""Envio controlado de prueba integral TAPPAD Radar por Gmail.
Solo permite dos correos de prueba. Sin cambios a Supabase.
Requiere SMTP_USER y SMTP_APP_PASSWORD en el entorno.
Uso: py enviar_prueba_integral_gmail.py --enviar
"""
import argparse, os, smtplib
from email.message import EmailMessage
from pathlib import Path

ROOT=Path(__file__).resolve().parent
HTML=ROOT/"documentos_secop_lote"/"vista_previa_integral_tappad.html"
PERMITIDOS=("tappadcons@gmail.com","gerardotapia112188@gmail.com")

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--enviar",action="store_true",help="Confirma envío solo a cuentas de prueba")
    args=p.parse_args()
    if not HTML.exists():raise SystemExit("Primero genera la vista previa integral")
    contenido=HTML.read_text(encoding="utf-8")
    if "TAPPAD Radar" not in contenido or "ComprasMX" not in contenido or "SECOP Coahuila" not in contenido:
        raise SystemExit("La vista previa no contiene ambas plataformas")
    msg=EmailMessage()
    msg["Subject"]="PRUEBA | TAPPAD Radar | ComprasMX y SECOP Coahuila"
    msg["From"]=os.environ.get("SMTP_USER","tappadcons@gmail.com")
    msg["To"]=", ".join(PERMITIDOS)
    msg.set_content("Prueba interna de TAPPAD Radar. Consulta la versión HTML del correo. No es una alerta comercial definitiva.")
    msg.add_alternative(contenido,subtype="html")
    print("DESTINATARIOS DE PRUEBA:",", ".join(PERMITIDOS))
    print("ORIGEN:",msg["From"])
    print("HTML:",HTML)
    if not args.enviar:
        print("SIMULACION: sin envio. Para enviar usar --enviar")
        return
    usuario=os.environ.get("SMTP_USER")
    clave=os.environ.get("SMTP_APP_PASSWORD")
    if not usuario or not clave:
        raise SystemExit("No hay SMTP_USER y SMTP_APP_PASSWORD configurados en esta ventana de CMD. No se envio nada.")
    if usuario.lower().strip() not in PERMITIDOS:
        raise SystemExit("Remitente fuera de las cuentas de prueba. No se envio nada.")
    msg.replace_header("From",usuario)
    with smtplib.SMTP("smtp.gmail.com",587,timeout=35) as smtp:
        smtp.ehlo();smtp.starttls();smtp.ehlo()
        smtp.login(usuario,clave)
        smtp.send_message(msg)
    print("Gmail acepto el mensaje para los dos destinatarios de prueba.")
    print("Sin escrituras Supabase; no implica confirmacion de entrega ni lectura.")

if __name__=="__main__":main()
