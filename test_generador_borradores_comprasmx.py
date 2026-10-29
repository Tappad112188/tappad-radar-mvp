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
Publicacion: 29/10/2026
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
        self.assertIn("cid:tappad-logo", html)

if __name__ == "__main__":
    unittest.main()
