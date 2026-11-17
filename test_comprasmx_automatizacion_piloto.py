"""Regresion local sin red: ventana de deteccion y compuerta de entrega ComprasMX."""
import unittest
from datetime import date, datetime
from zoneinfo import ZoneInfo
from generar_manifiesto_comprasmx_automatico import seleccionar_recientes
from control_notificaciones import autorizar_envio_real

class ComprasMXEntregaSegura(unittest.TestCase):
    def test_reciente_valida(self):
        lic={"id":1,"fuente":"ComprasMX","fecha_publicacion":"2026-11-16 09:00:00",
             "fecha_registro":"2026-11-17T12:00:00+00:00"}
        self.assertEqual(len(seleccionar_recientes([lic],date(2026,11,17))),1)
    def test_antigua_o_otra_fuente_no_entran(self):
        base={"id":1,"fuente":"ComprasMX","fecha_publicacion":"2026-11-01 09:00:00",
              "fecha_registro":"2026-11-17T12:00:00+00:00"}
        self.assertEqual(seleccionar_recientes([base],date(2026,11,17)),[])
        self.assertEqual(seleccionar_recientes([{**base,"fuente":"SECOP Coahuila","fecha_publicacion":"2026-11-17"}],date(2026,11,17)),[])
    def test_sin_interruptor_no_envia(self):
        lic={"estatus":"VIGENTE","fecha_apertura":"2026-11-27T11:00:00"}
        ahora=datetime(2026,11,17,12,0,tzinfo=ZoneInfo("America/Monterrey"))
        self.assertFalse(autorizar_envio_real({},lic,ahora=ahora)[0])
    def test_bloqueo_duplicados_y_vencidos(self):
        lic={"estatus":"VIGENTE","fecha_apertura":"2026-11-27T11:00:00"}
        ahora=datetime(2026,11,17,12,0,tzinfo=ZoneInfo("America/Monterrey"))
        cfg={"alertas_automaticas_habilitadas":"true"}
        self.assertFalse(autorizar_envio_real(cfg,lic,"enviado",ahora=ahora)[0])
        self.assertFalse(autorizar_envio_real(cfg,{**lic,"fecha_apertura":"2026-11-01T11:00:00"},ahora=ahora)[0])
        self.assertTrue(autorizar_envio_real(cfg,lic,ahora=ahora)[0])

if __name__=="__main__":
    unittest.main()
