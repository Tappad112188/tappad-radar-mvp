import unittest
from formato_alertas import fecha_legible, frase_oportunidades
from plantilla_correo_html import construir_correo_html

class TestFormatoAlertas(unittest.TestCase):
    def test_fecha(self):
        self.assertEqual(fecha_legible("2026-10-23T11:00:00"), "23 de octubre de 2026, 11:00 a. m.")
    def test_tarde(self):
        self.assertEqual(fecha_legible("2026-10-23T18:30:00"), "23 de octubre de 2026, 6:30 p. m.")
    def test_sin_fecha(self):
        self.assertEqual(fecha_legible(None), "No disponible")
    def test_singular(self):
        self.assertIn("una oportunidad", frase_oportunidades(1))
    def test_plural(self):
        self.assertIn("2 oportunidades", frase_oportunidades(2))
    def test_html_seguro(self):
        html = construir_correo_html("<script>", [{
            "numero_procedimiento": "IA-123", "nombre_procedimiento": "<b>Prueba</b>",
            "terminos": ["limpieza"], "fecha_apertura": "2026-10-23T11:00:00",
            "url_procedimiento": "https://comprasmx.buengobierno.gob.mx/",
        }])
        self.assertIn("&lt;script&gt;", html)
        self.assertNotIn("<script>", html)
        self.assertIn("23 de octubre de 2026, 11:00 a. m.", html)
        self.assertIn("una oportunidad", html)

if __name__ == "__main__":
    unittest.main()
