import unittest
from datetime import datetime, timezone, timedelta
from validador_plazo_oficial import validar_envio_oportunidad

AHORA = datetime(2026, 10, 20, 18, tzinfo=timezone.utc)
CANDIDATA = {"categoria_alerta": "candidata_revision"}
def verificacion(estado="confirmado_abierto", limite=None, revisado=None):
    return {"estado": estado, "fuente_url": "https://comprasmx.buengobierno.gob.mx/",
            "fecha_limite": (limite or (AHORA + timedelta(days=1))).isoformat(),
            "verificado_en": (revisado or AHORA).isoformat()}

class TestValidadorPlazoOficial(unittest.TestCase):
    def test_sin_verificacion(self):
        self.assertFalse(validar_envio_oportunidad(CANDIDATA, ahora=AHORA)["autorizada"])
    def test_confirmada(self):
        self.assertTrue(validar_envio_oportunidad(CANDIDATA, verificacion(), AHORA)["autorizada"])
    def test_plazo_vencido(self):
        self.assertFalse(validar_envio_oportunidad(CANDIDATA, verificacion(limite=AHORA-timedelta(minutes=1)), AHORA)["autorizada"])
    def test_verificacion_antigua(self):
        self.assertFalse(validar_envio_oportunidad(CANDIDATA, verificacion(revisado=AHORA-timedelta(hours=7)), AHORA)["autorizada"])
    def test_no_candidata(self):
        self.assertFalse(validar_envio_oportunidad({"categoria_alerta":"requiere_revision"},verificacion(),AHORA)["autorizada"])
    def test_cerrado(self):
        self.assertFalse(validar_envio_oportunidad(CANDIDATA,verificacion(estado="cerrado"),AHORA)["autorizada"])
    def test_sin_zona(self):
        v=verificacion()
        v["fecha_limite"]="2026-10-21T12:00:00"
        self.assertFalse(validar_envio_oportunidad(CANDIDATA,v,AHORA)["autorizada"])

if __name__ == "__main__":
    unittest.main()
