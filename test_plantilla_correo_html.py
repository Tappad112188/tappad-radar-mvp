"""Pruebas locales: no conectan a Gmail ni envían mensajes."""
import unittest
from unittest.mock import patch
from email.message import EmailMessage
from plantilla_correo_html import construir_correo_html
from envio_gmail_pruebas import enviar_prueba_gmail

OP = [{"numero_procedimiento":"IA-TEST","nombre_procedimiento":"Servicio <prueba>",
       "terminos":["mantenimiento"],"fecha_apertura":"2026-10-23T11:00:00",
       "url_procedimiento":"https://example.org/procedimiento"}]

class SMTPFalso:
    mensajes = []
    def __init__(self,*args,**kwargs): pass
    def __enter__(self): return self
    def __exit__(self,*args): pass
    def login(self,*args): pass
    def send_message(self,m): self.mensajes.append(m)

class PruebaCorreoHTML(unittest.TestCase):
    def test_escapa_datos_y_enlace(self):
        html = construir_correo_html("<Empresa>", OP)
        self.assertIn("&lt;Empresa&gt;", html)
        self.assertIn("Servicio &lt;prueba&gt;", html)
        self.assertIn("cid:tappad-logo", html)
        self.assertIn("https://example.org/procedimiento", html)
    def test_rechaza_url_no_segura(self):
        op = dict(OP[0],url_procedimiento="javascript:alert(1)")
        html = construir_correo_html("Empresa",[op])
        self.assertIn("Enlace oficial no disponible",html)
        self.assertNotIn("href=\"javascript:",html)
    def test_mime_png_inline_y_texto(self):
        SMTPFalso.mensajes.clear()
        with patch("smtplib.SMTP_SSL",SMTPFalso):
            enviar_prueba_gmail(1,"gerardotapia112188@gmail.com","Prueba",
                                "Texto alternativo","tappadcons@gmail.com","clave",
                                empresa="Empresa",oportunidades=OP)
        msg = SMTPFalso.mensajes[0]
        self.assertEqual(msg.get_content_type(),"multipart/alternative")
        self.assertIn("Texto alternativo",msg.get_body(preferencelist=("plain",)).get_content())
        html = msg.get_body(preferencelist=("html",))
        self.assertIn("cid:tappad-logo",html.get_content())
        imagenes=[p for p in msg.walk() if p.get_content_type()=="image/png"]
        self.assertEqual(len(imagenes),1)
        self.assertEqual(imagenes[0]["Content-ID"],"<tappad-logo>")
        self.assertGreater(len(imagenes[0].get_payload(decode=True)),100)
    def test_destinatario_no_autorizado(self):
        with self.assertRaises(ValueError):
            enviar_prueba_gmail(2,"tercero@example.org","Prueba","Texto",
                                "tappadcons@gmail.com","clave")

if __name__=="__main__":
    unittest.main()
