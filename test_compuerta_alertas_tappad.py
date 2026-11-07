"""Pruebas sin red, sin Supabase y sin correo para la compuerta TAPPAD."""
import unittest
from datetime import datetime
from compuerta_alertas_v3 import evaluar, fechas_correo

AHORA = datetime(2026, 11, 7, 10, 0)

class PruebasCompuerta(unittest.TestCase):
    def setUp(self):
        self.base = {"id": 42, "fuente": "SECOP Coahuila", "estatus": "Vigente",
                     "fecha_apertura": "2026-11-08T12:00:00",
                     "validacion_calendario": "pendiente"}

    def test_secop_sin_apertura_no_bloquea(self):
        self.assertTrue(evaluar({**self.base, "fecha_apertura": None}, 1, set(), AHORA)[0])

    def test_comprasmx_sin_apertura_no_bloquea(self):
        self.assertTrue(evaluar({**self.base, "fuente": "ComprasMX", "fecha_apertura": None}, 1, set(), AHORA)[0])

    def test_apertura_vencida_bloquea(self):
        self.assertFalse(evaluar({**self.base, "fecha_apertura": "2026-11-07T09:00:00"}, 1, set(), AHORA)[0])

    def test_cancelada_bloquea(self):
        self.assertFalse(evaluar({**self.base, "estatus": "cancelada"}, 1, set(), AHORA)[0])

    def test_duplicado_bloquea(self):
        self.assertFalse(evaluar(self.base, 1, {(1, 42)}, AHORA)[0])

    def test_fecha_invalida_bloquea(self):
        self.assertFalse(evaluar({**self.base, "fecha_apertura": "no-es-fecha"}, 1, set(), AHORA)[0])

    def test_texto_fecha_faltante(self):
        self.assertEqual(fechas_correo({})[0][1], "Fecha no disponible, verificar enlace")

if __name__ == "__main__":
    unittest.main(verbosity=2)
