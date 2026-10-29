"""Pruebas estáticas de validación documental por fuente, sin red ni SMTP."""
import unittest
from pathlib import Path

MOTOR = Path(__file__).with_name("motor_entrega_tappad_v2.py")

class CalendarioPorFuente(unittest.TestCase):
    def test_consulta_incluye_fuente(self):
        codigo = MOTOR.read_text(encoding="utf-8")
        self.assertIn("id,fuente,fecha_apertura,estatus,validacion_calendario", codigo)

    def test_comprasmx_no_exige_validacion_documental(self):
        codigo = MOTOR.read_text(encoding="utf-8")
        self.assertIn('str(l.get("fuente") or "").strip().casefold() != "comprasmx"', codigo)

    def test_otras_fuentes_conservan_control(self):
        codigo = MOTOR.read_text(encoding="utf-8")
        self.assertIn('str(l.get("validacion_calendario") or "").strip().casefold() != "verificado"', codigo)

if __name__ == "__main__":
    unittest.main()
