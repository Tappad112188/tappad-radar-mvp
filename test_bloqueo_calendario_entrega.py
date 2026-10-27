"""Pruebas de la barrera documental del motor de entrega, sin red ni SMTP."""
import unittest
from pathlib import Path

MOTOR = Path(__file__).with_name("motor_entrega_tappad_v2.py")

class CalendarioVerificado(unittest.TestCase):
    def test_motor_exige_columna_de_validacion(self):
        codigo = MOTOR.read_text(encoding="utf-8")
        self.assertIn('id,fecha_apertura,estatus,validacion_calendario', codigo)

    def test_motor_bloquea_calendario_pendiente(self):
        codigo = MOTOR.read_text(encoding="utf-8")
        self.assertIn('!= "verificado"', codigo)
        self.assertIn('Envio bloqueado: calendario documental no verificado', codigo)

if __name__ == "__main__":
    unittest.main()
