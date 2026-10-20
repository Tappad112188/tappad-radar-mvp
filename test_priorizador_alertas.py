import unittest
from datetime import datetime
from priorizador_alertas import priorizar_oportunidad

AHORA = datetime(2026, 10, 20, 12)
def lic(estatus="VIGENTE", fecha="2026-11-02T12:00:00"):
    return {"estatus": estatus, "fecha_apertura": fecha}
def coinc(geo="dentro_de_cobertura", tema=True):
    return {"categoria": geo, "coincidencia_tematica": tema}

class PriorizadorTests(unittest.TestCase):
    def test_candidata(self):
        self.assertEqual(priorizar_oportunidad(coinc(), lic(), AHORA)["categoria_alerta"], "candidata_revision")
    def test_concluida(self):
        self.assertEqual(priorizar_oportunidad(coinc(), lic("ADJUDICADO"), AHORA)["categoria_alerta"], "excluida_concluida")
    def test_fuera_de_cobertura(self):
        self.assertEqual(priorizar_oportunidad(coinc("fuera_de_cobertura"), lic(), AHORA)["categoria_alerta"], "exploratoria_fuera_cobertura")
    def test_sin_cobertura(self):
        self.assertEqual(priorizar_oportunidad(coinc("cobertura_sin_definir"), lic(), AHORA)["categoria_alerta"], "requiere_revision")
    def test_apertura_vencida(self):
        self.assertEqual(priorizar_oportunidad(coinc(), lic(fecha="2026-10-19"), AHORA)["categoria_alerta"], "requiere_revision")
    def test_sin_coincidencia_tematica(self):
        self.assertEqual(priorizar_oportunidad(coinc(tema=False), lic(), AHORA)["categoria_alerta"], "sin_coincidencia")

if __name__ == "__main__":
    unittest.main()
