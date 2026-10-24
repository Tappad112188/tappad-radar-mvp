"""Pruebas sin red de fichas SECOP; no modifica datos ni envia correos."""
import unittest
from html.parser import HTMLParser
from generar_fichas_secop_web import ficha, PORTAL

class Links(HTMLParser):
    def __init__(self):
        super().__init__(); self.links=[]
    def handle_starttag(self, tag, attrs):
        if tag=="a": self.links.append(dict(attrs).get("href"))

class FichasSECOP(unittest.TestCase):
    def setUp(self):
        self.base={"numero_procedimiento":"UTC-LPN-CA-E001-2026",
                   "cod_expediente":"UTC01-2026",
                   "nombre_procedimiento":"Servicio de limpieza y jardineria",
                   "fecha_publicacion":"2026-10-23",
                   "fecha_apertura":"2026-11-06T10:00:00"}
    def test_identificacion(self):
        html=ficha(self.base)
        self.assertIn("UTC-LPN-CA-E001-2026",html)
        self.assertIn("UTC01-2026",html)
    def test_enlace_oficial_no_descarga(self):
        links=Links();links.feed(ficha(self.base))
        self.assertEqual(links.links,[PORTAL])
        self.assertNotIn("GetFile/",ficha(self.base))
    def test_datos_no_verificados(self):
        html=ficha(self.base)
        self.assertIn("Pendiente de verificar",html)
        self.assertIn("verifica vigencia",html)
    def test_html_escapado(self):
        r={**self.base,"nombre_procedimiento":'<script>alert("x")</script>'}
        html=ficha(r)
        self.assertNotIn("<script>",html)
        self.assertIn("&lt;script&gt;",html)
    def test_sin_expediente_individual_falso(self):
        html=ficha(self.base)
        self.assertIn("no directamente al expediente",html)

if __name__=="__main__":
    unittest.main(verbosity=2)
