"""Pruebas del puente privado: sin red, pagos ni escrituras reales."""
import os
import unittest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch
from activacion_privada_postgres import activar_conexion_privada
from verificar_pago_mercadopago_servidor import VerificacionRechazada


class FakeCursor:
    def __init__(self, accepted, *, fecha_pago=None, vencimiento=None):
        self.accepted = accepted
        self.fecha_pago = fecha_pago
        self.vencimiento = vencimiento
        self.executions = []
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def execute(self, sql, args=None): self.executions.append((sql,args))
    def fetchone(self):
        if len(self.executions)==2: return ("tappad_activador_privado", "tappad_login_activacion", False, True)
        if len(self.executions)==3: return (False,)
        if len(self.executions) in (4,5): return (7,)
        if len(self.executions)==6: return (self.fecha_pago or datetime.now(timezone.utc)-timedelta(minutes=2),"mensual",self.vencimiento)
        if len(self.executions)==7: return (datetime.now(timezone.utc)+timedelta(days=30),)
        return (self.accepted,)


class FakeConnection:
    def __init__(self, accepted=True, *, fecha_pago=None, vencimiento=None):
        self.cursor_obj = FakeCursor(accepted, fecha_pago=fecha_pago, vencimiento=vencimiento)
        self.committed = False
        self.rolled_back = False
    def __enter__(self): return self
    def __exit__(self, exc_type, *_):
        self.rolled_back = exc_type is not None
        self.committed = exc_type is None
        return False
    def cursor(self): return self.cursor_obj


class PuenteTests(unittest.TestCase):
    def setUp(self):
        self.con = FakeConnection()
        self.calls = []
        self.evidence = {"cliente_id":4,"suscripcion_id":7,"pago_id":2,
                         "evidencia":{"verificacion_remota":"confirmada",
                                     "entorno":"produccion","payment_id":"pay-1",
                                     "preapproval_id":"sub-1","seller_id":"11"}}
    def connect(self, dsn):
        self.calls.append(dsn)
        return self.con
    def run_bridge(self, permitir=True):
        return activar_conexion_privada(
            2, supabase_url="https://example.supabase.co",
            supabase_key="dummy", mercadopago_token="dummy",
            postgres_dsn="postgresql://private", permitir=permitir,
            connect=self.connect)
    @patch("activacion_privada_postgres.verificar_pago_desde_supabase")
    def test_apagado_no_verifica_ni_escribe(self, verifier):
        with patch.dict(os.environ, {"TAPPAD_HABILITAR_ACTIVACION_PRODUCCION":"SI","TAPPAD_MERCADOPAGO_SELLER_ID":"11"}):
            self.assertEqual(self.run_bridge(False)["aplicacion"],"bloqueada")
        verifier.assert_not_called()
        self.assertEqual(self.calls,[])
    @patch("activacion_privada_postgres.verificar_pago_desde_supabase")
    def test_entorno_no_autorizado(self, verifier):
        with patch.dict(os.environ, {"TAPPAD_HABILITAR_ACTIVACION_PRODUCCION":"NO","TAPPAD_MERCADOPAGO_SELLER_ID":"11"}):
            self.assertEqual(self.run_bridge()["aplicacion"],"bloqueada")
        verifier.assert_not_called()
        self.assertEqual(self.calls,[])
    @patch("activacion_privada_postgres.verificar_pago_desde_supabase")
    def test_verificacion_invalida_no_abre_db(self, verifier):
        verifier.side_effect = VerificacionRechazada("pago_invalido")
        with patch.dict(os.environ, {"TAPPAD_HABILITAR_ACTIVACION_PRODUCCION":"SI"}):
            with self.assertRaises(VerificacionRechazada): self.run_bridge()
        self.assertEqual(self.calls,[])
    @patch("activacion_privada_postgres.verificar_pago_desde_supabase")
    def test_rechazo_sql_revierte_transaccion(self, verifier):
        verifier.return_value=self.evidence
        self.con = FakeConnection(False)
        with patch.dict(os.environ, {"TAPPAD_HABILITAR_ACTIVACION_PRODUCCION":"SI","TAPPAD_MERCADOPAGO_SELLER_ID":"11"}):
            with self.assertRaisesRegex(VerificacionRechazada,"activacion_rechazada"):
                self.run_bridge()
        self.assertTrue(self.con.rolled_back)
        self.assertFalse(self.con.committed)
    @patch("activacion_privada_postgres.verificar_pago_desde_supabase")
    def test_vendedor_ajeno_rechazado_antes_de_db(self, verifier):
        verifier.return_value=dict(self.evidence, evidencia=dict(self.evidence["evidencia"], seller_id="999"))
        with patch.dict(os.environ, {"TAPPAD_HABILITAR_ACTIVACION_PRODUCCION":"SI","TAPPAD_MERCADOPAGO_SELLER_ID":"11"}):
            with self.assertRaisesRegex(VerificacionRechazada,"vendedor_inesperado"):
                self.run_bridge()
        self.assertEqual(self.calls, [])

    @patch("activacion_privada_postgres.verificar_pago_desde_supabase")
    def test_fechas_del_llamador_rechazadas(self, verifier):
        with patch.dict(os.environ, {"TAPPAD_HABILITAR_ACTIVACION_PRODUCCION":"SI","TAPPAD_MERCADOPAGO_SELLER_ID":"11"}):
            with self.assertRaisesRegex(VerificacionRechazada,"periodo_no_puede_ser_proporcionado"):
                activar_conexion_privada(
                    2,supabase_url="https://example.supabase.co",supabase_key="dummy",
                    mercadopago_token="dummy",postgres_dsn="postgresql://private",
                    inicio=datetime.now(timezone.utc),permitir=True,connect=self.connect)
        verifier.assert_not_called()

    @patch("activacion_privada_postgres.verificar_pago_desde_supabase")
    def test_renovacion_anticipada_no_extiende_acceso(self, verifier):
        verifier.return_value=self.evidence
        self.con = FakeConnection(vencimiento=datetime.now(timezone.utc)+timedelta(days=12))
        with patch.dict(os.environ, {"TAPPAD_HABILITAR_ACTIVACION_PRODUCCION":"SI",
                                     "TAPPAD_MERCADOPAGO_SELLER_ID":"11"}):
            with self.assertRaisesRegex(VerificacionRechazada,"renovacion_anticipada_pendiente"):
                self.run_bridge()
        self.assertTrue(self.con.rolled_back)
        self.assertEqual(len(self.con.cursor_obj.executions),6)

    @patch("activacion_privada_postgres.verificar_pago_desde_supabase")
    def test_pago_tardio_no_activa_sin_politica(self, verifier):
        verifier.return_value=self.evidence
        self.con = FakeConnection(fecha_pago=datetime.now(timezone.utc)-timedelta(days=8))
        with patch.dict(os.environ, {"TAPPAD_HABILITAR_ACTIVACION_PRODUCCION":"SI",
                                     "TAPPAD_MERCADOPAGO_SELLER_ID":"11"}):
            with self.assertRaisesRegex(VerificacionRechazada,"pago_fuera_de_ventana"):
                self.run_bridge()
        self.assertTrue(self.con.rolled_back)
        self.assertEqual(len(self.con.cursor_obj.executions),6)

    @patch("activacion_privada_postgres.verificar_pago_desde_supabase")
    def test_fecha_de_pago_futura_no_activa(self, verifier):
        verifier.return_value=self.evidence
        self.con = FakeConnection(fecha_pago=datetime.now(timezone.utc)+timedelta(days=1))
        with patch.dict(os.environ, {"TAPPAD_HABILITAR_ACTIVACION_PRODUCCION":"SI",
                                     "TAPPAD_MERCADOPAGO_SELLER_ID":"11"}):
            with self.assertRaisesRegex(VerificacionRechazada,"pago_fuera_de_ventana"):
                self.run_bridge()
        self.assertTrue(self.con.rolled_back)
        self.assertEqual(len(self.con.cursor_obj.executions),6)

    @patch("activacion_privada_postgres.verificar_pago_desde_supabase")
    def test_rol_administrativo_bloqueado(self, verifier):
        verifier.return_value=self.evidence
        self.con.cursor_obj.fetchone=lambda: ("postgres","postgres",True,True)
        with patch.dict(os.environ, {"TAPPAD_HABILITAR_ACTIVACION_PRODUCCION":"SI",
                                     "TAPPAD_MERCADOPAGO_SELLER_ID":"11"}):
            with self.assertRaisesRegex(VerificacionRechazada,"identidad_activacion_no_autorizada"):
                self.run_bridge()
        self.assertTrue(self.con.rolled_back)
        self.assertEqual(len(self.con.cursor_obj.executions),2)

    @patch("activacion_privada_postgres.verificar_pago_desde_supabase")
    def test_funcion_security_definer_rechazada(self, verifier):
        verifier.return_value=self.evidence
        original=self.con.cursor_obj.fetchone
        def responder():
            if len(self.con.cursor_obj.executions)==3: return (True,)
            return original()
        self.con.cursor_obj.fetchone=responder
        with patch.dict(os.environ, {"TAPPAD_HABILITAR_ACTIVACION_PRODUCCION":"SI",
                                     "TAPPAD_MERCADOPAGO_SELLER_ID":"11"}):
            with self.assertRaisesRegex(VerificacionRechazada,"funcion_activacion_no_invoker"):
                self.run_bridge()
        self.assertTrue(self.con.rolled_back)
        self.assertEqual(len(self.con.cursor_obj.executions),3)

    @patch("activacion_privada_postgres.verificar_pago_desde_supabase")
    def test_pago_valido_aplica_una_vez(self, verifier):
        verifier.return_value=self.evidence
        with patch.dict(os.environ, {"TAPPAD_HABILITAR_ACTIVACION_PRODUCCION":"SI","TAPPAD_MERCADOPAGO_SELLER_ID":"11"}):
            self.assertEqual(self.run_bridge()["aplicacion"],"aplicada")
        self.assertTrue(self.con.committed)
        self.assertEqual(len(self.con.cursor_obj.executions),8)
        self.assertIn("tappad_internal.tappad_aplicar_activacion_comercial",
                      self.con.cursor_obj.executions[7][0])


if __name__=="__main__":
    unittest.main()
