"""Pruebas sin red de la compuerta final de entrega ComprasMX."""
import unittest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from preparador_alertas import filtrar_lote_para_envio_real
from control_notificaciones import separar_notificaciones

ZONA=ZoneInfo("America/Monterrey")

class EntregaSegura(unittest.TestCase):
    def setUp(self):
        self.ahora=datetime.now(ZONA)
        self.licitacion={"id":990001,"fuente":"ComprasMX","estatus":"Vigente",
            "fecha_apertura":(self.ahora+timedelta(days=5)).isoformat()}
        self.resultado={"por_proveedor":{9001:[{"cliente_id":9001,"licitacion_id":990001}]}}
    def filtrar(self,habilitado="true",historial=None,licitacion=None):
        return filtrar_lote_para_envio_real(self.resultado,[licitacion or self.licitacion],
            historial or [],{"alertas_automaticas_habilitadas":habilitado},ahora=self.ahora)
    def test_interruptor_desactivado(self):
        self.assertFalse(self.filtrar("false")["por_proveedor"])
    def test_nueva_y_vigente_apta_con_interruptor(self):
        self.assertEqual(len(self.filtrar()["por_proveedor"][9001]),1)
    def test_duplicado_enviado_bloqueado(self):
        r=self.filtrar(historial=[{"cliente_id":9001,"licitacion_id":990001,"estado":"enviado"}])
        self.assertFalse(r["por_proveedor"])
    def test_pendiente_bloqueado(self):
        r=self.filtrar(historial=[{"cliente_id":9001,"licitacion_id":990001,"estado":"pendiente"}])
        self.assertFalse(r["por_proveedor"])
    def test_error_no_se_reintenta(self):
        r=self.filtrar(historial=[{"cliente_id":9001,"licitacion_id":990001,"estado":"error"}])
        self.assertFalse(r["por_proveedor"])
    def test_plazo_vencido(self):
        l={**self.licitacion,"fecha_apertura":(self.ahora-timedelta(days=1)).isoformat()}
        self.assertFalse(self.filtrar(licitacion=l)["por_proveedor"])
    def test_estatus_no_vigente(self):
        self.assertFalse(self.filtrar(licitacion={**self.licitacion,"estatus":"Cancelada"})["por_proveedor"])
    def test_deduplicacion(self):
        x={"cliente_id":9001,"licitacion_id":990001}
        r=separar_notificaciones([x,x],[])
        self.assertEqual(len(r["nuevas"]),1)
    def test_sin_apertura(self):
        self.assertFalse(self.filtrar(licitacion={**self.licitacion,"fecha_apertura":None})["por_proveedor"])

if __name__=="__main__": unittest.main()
