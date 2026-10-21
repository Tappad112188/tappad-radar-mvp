import unittest
from datetime import datetime
from zoneinfo import ZoneInfo
from validador_plazo_oficial import validar_envio_oportunidad

AHORA = datetime(2026, 10, 21, 16, 0, tzinfo=ZoneInfo("America/Monterrey"))

def oportunidad(fecha="2026-10-23T11:00:00", estatus="VIGENTE", categoria="candidata_revision"):
    return {"categoria_alerta": categoria, "fecha_apertura": fecha, "estatus": estatus}

class TestValidadorPlazoOficial(unittest.TestCase):
    def test_apertura_futura(self):
        self.assertTrue(validar_envio_oportunidad(oportunidad(), ahora=AHORA)["autorizada"])
    def test_fecha_vencida(self):
        self.assertFalse(validar_envio_oportunidad(oportunidad("2026-10-20T11:00:00"), ahora=AHORA)["autorizada"])
    def test_fecha_exacta(self):
        self.assertFalse(validar_envio_oportunidad(oportunidad("2026-10-21T16:00:00"), ahora=AHORA)["autorizada"])
    def test_sin_fecha(self):
        self.assertFalse(validar_envio_oportunidad(oportunidad(None), ahora=AHORA)["autorizada"])
    def test_fecha_invalida(self):
        self.assertFalse(validar_envio_oportunidad(oportunidad("fecha"), ahora=AHORA)["autorizada"])
    def test_cancelada(self):
        self.assertFalse(validar_envio_oportunidad(oportunidad(estatus="CANCELADO"), ahora=AHORA)["autorizada"])
    def test_no_candidata(self):
        self.assertFalse(validar_envio_oportunidad(oportunidad(categoria="requiere_revision"), ahora=AHORA)["autorizada"])
    def test_sin_estatus_activo(self):
        self.assertFalse(validar_envio_oportunidad(oportunidad(estatus=""), ahora=AHORA)["autorizada"])

if __name__ == "__main__":
    unittest.main()
