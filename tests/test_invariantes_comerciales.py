"""Pruebas locales de invariantes comerciales, sin red ni escrituras.

Ejecutar: python -m unittest tests/test_invariantes_comerciales.py
"""
import unittest
from datetime import datetime, timedelta, timezone


def renovacion_admisible(checkpoint_anterior, proximo_cobro, fecha_pago,
                         pago_aprobado, referencia_unica, proveedor_confirmado,
                         entorno_prueba):
    """La fecha de cobro por si sola nunca acredita una renovacion."""
    if entorno_prueba or not (proveedor_confirmado and pago_aprobado and referencia_unica):
        return False
    if any(x is None for x in (checkpoint_anterior, proximo_cobro, fecha_pago)):
        return False
    try:
        return proximo_cobro > checkpoint_anterior and fecha_pago > checkpoint_anterior
    except (TypeError, ValueError):
        return False


class InvariantesComerciales(unittest.TestCase):
    def setUp(self):
        self.anterior = datetime(2026, 11, 13, tzinfo=timezone.utc)
        self.nuevo = self.anterior + timedelta(days=30)
        self.pago = self.anterior + timedelta(days=1)
        self.base = dict(checkpoint_anterior=self.anterior,
                         proximo_cobro=self.nuevo, fecha_pago=self.pago,
                         pago_aprobado=True, referencia_unica=True,
                         proveedor_confirmado=True, entorno_prueba=False)

    def test_renovacion_con_evidencia_completa(self):
        self.assertTrue(renovacion_admisible(**self.base))

    def test_entorno_prueba_no_habilita_acceso_real(self):
        self.assertFalse(renovacion_admisible(**(self.base | {"entorno_prueba": True})))

    def test_no_basta_con_fecha_futura(self):
        self.assertFalse(renovacion_admisible(**(self.base | {"pago_aprobado": False})))

    def test_pago_anterior_al_checkpoint(self):
        self.assertFalse(renovacion_admisible(**(self.base | {"fecha_pago": self.anterior})))

    def test_checkpoint_sin_avance(self):
        self.assertFalse(renovacion_admisible(**(self.base | {"proximo_cobro": self.anterior})))

    def test_referencia_duplicada(self):
        self.assertFalse(renovacion_admisible(**(self.base | {"referencia_unica": False})))

    def test_sin_verificacion_remota(self):
        self.assertFalse(renovacion_admisible(**(self.base | {"proveedor_confirmado": False})))

    def test_falta_fecha_pago(self):
        self.assertFalse(renovacion_admisible(**(self.base | {"fecha_pago": None})))

    def test_fecha_incompatible(self):
        self.assertFalse(renovacion_admisible(**(self.base | {"fecha_pago": "no_es_fecha"})))

    def test_falta_fecha(self):
        self.assertFalse(renovacion_admisible(**(self.base | {"proximo_cobro": None})))


if __name__ == "__main__":
    unittest.main()
