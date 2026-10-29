"""Regresiones de vigencia ComprasMX sin fecha oficial de apertura."""
import unittest
from datetime import datetime
from compuerta_alertas_v3 import evaluar

AHORA = datetime(2026, 10, 29, 12, 0)
BASE = {"id": 99, "fuente": "ComprasMX", "estatus": "Vigente"}

class FechasComprasMX(unittest.TestCase):
    def test_sin_fecha_publicada_se_admite(self):
        self.assertEqual(evaluar({**BASE, "fecha_apertura": None}, 1, set(), AHORA),
                         (True, "comprasmx_sin_fecha_apertura_publicada"))

    def test_fecha_vencida_se_bloquea(self):
        self.assertEqual(evaluar({**BASE, "fecha_apertura": "2026-10-28T10:00:00"}, 1, set(), AHORA),
                         (False, "plazo_presentacion_vencido"))

    def test_fecha_invalida_no_se_confunde_con_ausente(self):
        self.assertEqual(evaluar({**BASE, "fecha_apertura": "fecha ilegible"}, 1, set(), AHORA),
                         (False, "sin_fecha_apertura_valida"))

    def test_secop_sin_fecha_sigue_bloqueado(self):
        self.assertEqual(evaluar({**BASE, "fuente": "SECOP Coahuila", "fecha_apertura": None}, 1, set(), AHORA),
                         (False, "sin_fecha_apertura_valida"))

    def test_cancelada_y_duplicada_siempre_bloqueadas(self):
        self.assertEqual(evaluar({**BASE, "estatus": "cancelada", "fecha_apertura": None}, 1, set(), AHORA)[0], False)
        self.assertEqual(evaluar({**BASE, "fecha_apertura": None}, 1, {(1, 99)}, AHORA)[0], False)

if __name__ == "__main__":
    unittest.main()
