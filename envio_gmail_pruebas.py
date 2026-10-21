"""Envío SMTP exclusivo para pruebas manuales de TAPPAD Radar."""
import smtplib
import ssl
from email.message import EmailMessage

REMITENTE_PERMITIDO = "tappadcons@gmail.com"
DESTINATARIOS_PRUEBA = {
    1: "gerardotapia112188@gmail.com",
    4: "tappadcons@gmail.com",
}

def enviar_prueba_gmail(cliente_id, correo_registrado, asunto, cuerpo, usuario, clave, empresa=None, oportunidades=None):
    """Envía solo a los dos registros de prueba, nunca a terceros."""
    destino = DESTINATARIOS_PRUEBA.get(int(cliente_id))
    if not destino or str(correo_registrado or "").strip().lower() != destino:
        raise ValueError("Destinatario fuera de la lista autorizada de pruebas.")
    if str(usuario or "").strip().lower() != REMITENTE_PERMITIDO:
        raise ValueError("El remitente no corresponde a la cuenta autorizada.")
    if not clave or not str(clave).strip():
        raise ValueError("Falta configurar la contraseña de aplicación.")
    mensaje = EmailMessage()
    mensaje["From"] = REMITENTE_PERMITIDO
    mensaje["To"] = destino
    mensaje["Subject"] = asunto
    mensaje.set_content(cuerpo)
    if empresa is not None and oportunidades is not None:
        from plantilla_correo_html import construir_correo_html
        mensaje.add_alternative(construir_correo_html(empresa, oportunidades), subtype="html")
        import cairosvg
        from pathlib import Path
        logo = Path(__file__).resolve().parent / "assets" / "logo_tappad.svg"
        png = cairosvg.svg2png(url=str(logo), output_width=276, output_height=276)
        mensaje.get_body(preferencelist=("html",)).add_related(
            png, maintype="image", subtype="png", cid="<tappad-logo>",
            filename="tappad-logo.png", disposition="inline")
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ssl.create_default_context(), timeout=20) as smtp:
        smtp.login(REMITENTE_PERMITIDO, str(clave).replace(" ", ""))
        smtp.send_message(mensaje)
    return True
