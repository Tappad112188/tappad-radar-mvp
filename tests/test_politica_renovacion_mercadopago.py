"""Casos de politica de renovacion: ninguna llamada externa ni escritura."""
import unittest
from datetime import datetime, timezone, timedelta
from politica_renovacion_mercadopago import evaluar_inicio_ciclo


class PoliticaRenovacionTests(unittest.TestCase):
    def setUp(self):
        self.ahora = datetime(2026, 11, 17, 23, 0, tzinfo=timezone.utc)

    def evaluar(self, pago, vencimiento=None):
        return evaluar_inicio_ciclo(fecha_pago=pago,
                                   vencimiento=vencimiento, ahora=self.ahora)

    def test_primera_activacion(self):
        pago = self.ahora - timedelta(hours=1)
        self.assertEqual(self.evaluar(pago), ("aplicar", pago))

    def test_renovacion_vencida_conserva_continuidad(self):
        pago = self.ahora - timedelta(hours=1)
        anterior = self.ahora - timedelta(days=2)
        self.assertEqual(self.evaluar(pago, anterior), ("aplicar", anterior))

    def test_anticipada_no_concede_acceso(self):
        pago = self.ahora - timedelta(hours=1)
        self.assertEqual(self.evaluar(pago, self.ahora + timedelta(days=10)),
                         ("pendiente_anticipada", None))

    def test_pago_tardio_se_reserva_para_revision(self):
        self.assertEqual(self.evaluar(self.ahora - timedelta(days=8)),
                         ("revision_tardia", None))

    def test_pago_en_limite_siete_dias(self):
        pago = self.ahora - timedelta(days=7)
        self.assertEqual(self.evaluar(pago), ("aplicar", pago))

    def test_fecha_futura(self):
        self.assertEqual(self.evaluar(self.ahora + timedelta(seconds=1)),
                         ("fecha_futura", None))

    def test_fechas_sin_zona(self):
        self.assertEqual(self.evaluar(self.ahora.replace(tzinfo=None)),
                         ("fecha_invalida", None))
        self.assertEqual(self.evaluar(self.ahora, self.ahora.replace(tzinfo=None)),
                         ("fecha_invalida", None))


if __name__ == "__main__":
    unittest.main()
