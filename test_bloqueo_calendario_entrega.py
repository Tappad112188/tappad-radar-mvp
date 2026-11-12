"""Pruebas funcionales sin red de reglas de apertura por fuente."""
import unittest
from datetime import datetime
from compuerta_alertas_v3 import evaluar

class CalendarioPorFuente(unittest.TestCase):
    def setUp(self):
        self.ahora=datetime(2026,11,7,10,0)
        self.base={"id":42,"estatus":"Vigente","fecha_apertura":"2026-11-08T12:00:00",
                   "validacion_calendario":"pendiente"}
    def test_comprasmx_no_exige_validacion_documental(self):
        l={**self.base,"fuente":"ComprasMX"}
        self.assertTrue(evaluar(l,1,set(),self.ahora)[0])
    def test_secop_sin_apertura_se_bloquea(self):
        l={**self.base,"fuente":"SECOP Coahuila","fecha_apertura":None}
        self.assertFalse(evaluar(l,1,set(),self.ahora)[0])
    def test_secop_con_apertura_vigente_se_evalua(self):
        l={**self.base,"fuente":"SECOP Coahuila"}
        self.assertTrue(evaluar(l,1,set(),self.ahora)[0])

if __name__=="__main__": unittest.main()
