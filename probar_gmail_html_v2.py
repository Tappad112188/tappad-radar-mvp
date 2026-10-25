"""Envio de prueba Gmail TAPPAD Radar: SOLO dos buzones autorizados.
No consulta ni modifica Supabase. No registra notificaciones de produccion.
Requiere --enviar-prueba para enviar; por defecto solo muestra el plan.
"""
import argparse
import os
import smtplib
from email.message import EmailMessage
from pathlib import Path

BASE=Path(__file__).resolve().parent
CARPETA=BASE/"borradores_gmail_tappad_v3"
DESTINATARIOS=("tappadcons@gmail.com","gerardotapia112188@gmail.com")\nLOGO=BASE/"assets"/"logo_tappad.png"

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--enviar-prueba",action="store_true")
    args=p.parse_args()
    archivos=sorted(CARPETA.glob("correo_proveedor_*.html"))
    if not archivos:
        raise SystemExit("No hay borradores. Ejecuta primero: py generar_borradores_gmail_v2.py")
    print("Borradores:",len(archivos),"| Destinatarios fijos:",", ".join(DESTINATARIOS))
    print("Envios previstos:",len(archivos)*len(DESTINATARIOS))
    if not args.enviar_prueba:
        print("SIMULACION: cero correos enviados. Para autorizar: --enviar-prueba")
        return
    usuario=os.environ.get("SMTP_USER")
    clave=os.environ.get("SMTP_APP_PASSWORD")
    if not usuario or not clave:
        raise SystemExit("Faltan SMTP_USER o SMTP_APP_PASSWORD en PowerShell. No pegues las claves en el chat.")
    if not LOGO.is_file():\n        raise SystemExit("Falta assets/logo_tappad.png. Descarga el logotipo original de GitHub.")\n    logo_bytes=LOGO.read_bytes()\n    enviados=0
    with smtplib.SMTP("smtp.gmail.com",587,timeout=30) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.ehlo()
        smtp.login(usuario,clave)
        for archivo in archivos:
            html=archivo.read_text(encoding="utf-8")
            for destino in DESTINATARIOS:
                msg=EmailMessage()
                msg["From"]=usuario
                msg["To"]=destino
                msg["Subject"]="[PRUEBA] TAPPAD Radar - "+archivo.stem.replace("_"," ")
                msg.set_content("Prueba TAPPAD Radar. Abre este mensaje en un cliente compatible con HTML.")
                msg.add_alternative(html,subtype="html")\n                msg.get_payload()[-1].add_related(logo_bytes,maintype="image",subtype="png",cid="<logo_tappad>",filename="logo_tappad.png",disposition="inline")
                smtp.send_message(msg)
                enviados+=1
                print("Enviado a",destino,"desde",archivo.name)
    print("PRUEBA COMPLETADA:",enviados,"correos. Sin escrituras en Supabase.")

if __name__=="__main__":
    main()
