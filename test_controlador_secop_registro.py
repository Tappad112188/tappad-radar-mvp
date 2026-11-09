"""Pruebas aisladas de autorizacion del controlador SECOP (sin red ni escrituras)."""
import unittest
from ejecutar_secop_windows import auditoria_autoriza_registro

class ControladorSecopTests(unittest.TestCase):
    def setUp(self):
        self.base={"fecha_consulta":"2026-11-09","consulta_supabase":"realizada",
                   "total":2,"estado":"SOLO_LECTURA",
                   "importacion_habilitada":False,"notificaciones_habilitadas":False,
                   "nuevos":["a","b"],"existentes":[]}
    def test_auditoria_valida(self):
        self.assertTrue(auditoria_autoriza_registro(self.base,"2026-11-09",2))
    def test_fecha_incorrecta(self):
        self.assertFalse(auditoria_autoriza_registro(self.base,"2026-11-10",2))
    def test_consulta_no_realizada(self):
        d={**self.base,"consulta_supabase":"no_realizada_faltan_variables"}
        self.assertFalse(auditoria_autoriza_registro(d,"2026-11-09",2))
    def test_total_inconsistente(self):
        d={**self.base,"nuevos":["a"]}
        self.assertFalse(auditoria_autoriza_registro(d,"2026-11-09",2))
    def test_alertas_habilitadas(self):
        d={**self.base,"notificaciones_habilitadas":True}
        self.assertFalse(auditoria_autoriza_registro(d,"2026-11-09",2))
if __name__=="__main__":unittest.main()
