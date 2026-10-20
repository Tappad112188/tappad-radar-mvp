"""Pruebas de clasificación temporal de licitaciones."""
import unittest
from datetime import datetime
from clasificador_licitaciones import clasificar_licitacion

AHORA = datetime(2026, 10, 20, 12, 0)

class ClasificadorLicitacionesTests(unittest.TestCase):
    def test_vigente_con_apertura_futura(self):
        r = clasificar_licitacion({"estatus": "VIGENTE", "fecha_apertura": "2026-11-01T12:00:00"}, AHORA)
        self.assertEqual(r["categoria"], "potencialmente_abierta")

    def test_aclaraciones_con_apertura_futura(self):
        r = clasificar_licitacion({"estatus": "EN ACLARACIONES", "fecha_apertura": "2026-11-01T12:00:00"}, AHORA)
        self.assertEqual(r["categoria"], "potencialmente_abierta")

    def test_vigente_con_apertura_pasada(self):
        r = clasificar_licitacion({"estatus": "VIGENTE", "fecha_apertura": "2026-10-19T12:00:00"}, AHORA)
        self.assertEqual(r["categoria"], "requiere_revision")

    def test_adjudicado_tiene_prioridad(self):
        r = clasificar_licitacion({"estatus": "ADJUDICADO", "fecha_apertura": "2026-11-01T12:00:00"}, AHORA)
        self.assertEqual(r["categoria"], "concluida")

    def test_cancelado(self):
        r = clasificar_licitacion({"estatus": "CANCELADO", "fecha_apertura": None}, AHORA)
        self.assertEqual(r["categoria"], "concluida")

    def test_sin_fecha(self):
        r = clasificar_licitacion({"estatus": "VIGENTE", "fecha_apertura": None}, AHORA)
        self.assertEqual(r["categoria"], "requiere_revision")

    def test_estatus_desconocido(self):
        r = clasificar_licitacion({"estatus": "OTRO", "fecha_apertura": "2026-11-01T12:00:00"}, AHORA)
        self.assertEqual(r["categoria"], "requiere_revision")

if __name__ == "__main__":
    unittest.main()
