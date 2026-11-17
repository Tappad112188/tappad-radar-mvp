import unittest
from datetime import date
from generar_manifiesto_comprasmx_automatico import seleccionar_recientes

HOY=date(2026,11,17)
def lic(pub,detect,fuente="ComprasMX"):
    return {"id":1,"fuente":fuente,"fecha_publicacion":pub,"fecha_registro":detect}

class SeleccionRecientesTests(unittest.TestCase):
    def test_publicacion_anterior_detectada_hoy(self):
        self.assertEqual(len(seleccionar_recientes([lic("2026-11-14 10:00:00","2026-11-17T02:23:32+00:00")],HOY)),1)
    def test_no_reenvia_historicos(self):
        self.assertEqual(seleccionar_recientes([lic("2026-11-01","2026-11-17")],HOY),[])
    def test_no_reprocesa_detectados_antes(self):
        self.assertEqual(seleccionar_recientes([lic("2026-11-15","2026-11-13")],HOY),[])
    def test_otra_fuente_no_se_incluye(self):
        self.assertEqual(seleccionar_recientes([lic("2026-11-17","2026-11-17","SECOP Coahuila")],HOY),[])
    def test_fechas_futuras_o_faltantes_no_se_incluyen(self):
        self.assertEqual(seleccionar_recientes([lic("2026-11-18","2026-11-17"),lic(None,"2026-11-17")],HOY),[])

if __name__=="__main__":unittest.main()
