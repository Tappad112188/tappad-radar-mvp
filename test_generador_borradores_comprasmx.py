"""Regresion de borradores ComprasMX con siete campos oficiales."""
import unittest
from generar_borradores_gmail_v3 import convertir_bloque

class BorradoresComprasMX(unittest.TestCase):
    def test_siete_campos_y_fechas_ausentes(self):
        bloque="""TAPPAD Radar | Vista previa para Empresa Prueba
Procedimiento: IA-123
Fuente: ComprasMX
Objeto: Compra de material
Descripcion resumida: Material de oficina
Enlace del procedimiento: https://comprasmx.buengobierno.gob.mx/test
Publicacion: 2026-10-29T09:00:00
Junta de aclaraciones: No especificada
Presentacion y apertura de propuestas: No especificada
Fallo programado: No especificada
"""
        nombre, oportunidades, html = convertir_bloque(bloque)
        self.assertEqual(nombre, "Empresa Prueba")
        self.assertEqual(len(oportunidades), 1)
        self.assertEqual(html.count("Fecha no disponible, verificar enlace"), 3)
        for etiqueta in ("Descripción del procedimiento:", "Número de procedimiento:",
                         "Fecha de publicación:", "Fecha de Junta de aclaraciones:",
                         "Fecha de apertura de proposiciones:", "Fecha de fallo:",
                         "Enlace a documentos del procedimiento:"):
            self.assertIn(etiqueta, html)
        self.assertIn("cid:tappad-logo", html)\n\n    def test_descripcion_larga_no_se_recorta(self):\n        descripcion = "Adquisición de equipos " + "tecnológicos especializados " * 25 + "FIN_DESCRIPCION_OFICIAL"\n        bloque = ("TAPPAD Radar | Vista previa para Empresa Prueba\\n"\n                  "Procedimiento: IA-456\\nFuente: ComprasMX\\n"\n                  "Descripcion resumida: " + descripcion + "\\n"\n                  "Enlace del procedimiento: https://ejemplo.gob.mx/procedimiento\\n")\n        _, oportunidades, html = convertir_bloque(bloque)\n        self.assertEqual(oportunidades[0]["descripcion"], descripcion)\n        self.assertIn("FIN_DESCRIPCION_OFICIAL", html)

if __name__ == "__main__":
    unittest.main()
