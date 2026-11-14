"""Pruebas del puente privado: sin red, pagos ni escrituras reales."""
import os
import unittest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch
from activacion_privada_postgres import activar_conexion_privada
from verificar_pago_mercadopago_servidor import VerificacionRechazada


class FakeCursor:
    def __init__(self, accepted): self.accepted = accepted; self.executions = []
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def execute(self, sql, args): self.executions.append((sql,args))
    def fetchone(self): return (self.accepted,)


class FakeConnection:
    def __init__(self, accepted=True):
        self.cursor_obj = FakeCursor(accepted)
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
            inicio=datetime.now(timezone.utc)-timedelta(minutes=2),
            fin=datetime.now(timezone.utc)+timedelta(days=30),
            connect=self.connect)
    @patch("activacion_privada_postgres.verificar_pago_desde_supabase")
    def test_apagado_no_verifica_ni_escribe(self, verifier):
        with patch.dict(os.environ, {"TAPPAD_HABILITAR_ACTIVACION_PRODUCCION":"SI"}):
            self.assertEqual(self.run_bridge(False)["aplicacion"],"bloqueada")
        verifier.assert_not_called()
        self.assertEqual(self.calls,[])
    @patch("activacion_privada_postgres.verificar_pago_desde_supabase")
    def test_entorno_no_autorizado(self, verifier):
        with patch.dict(os.environ, {"TAPPAD_HABILITAR_ACTIVACION_PRODUCCION":"NO"}):
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
        with patch.dict(os.environ, {"TAPPAD_HABILITAR_ACTIVACION_PRODUCCION":"SI"}):
            with self.assertRaisesRegex(VerificacionRechazada,"activacion_rechazada"):
                self.run_bridge()
        self.assertTrue(self.con.rolled_back)
        self.assertFalse(self.con.committed)
    @patch("activacion_privada_postgres.verificar_pago_desde_supabase")
    def test_pago_valido_aplica_una_vez(self, verifier):
        verifier.return_value=self.evidence
        with patch.dict(os.environ, {"TAPPAD_HABILITAR_ACTIVACION_PRODUCCION":"SI"}):
            self.assertEqual(self.run_bridge()["aplicacion"],"aplicada")
        self.assertTrue(self.con.committed)
        self.assertEqual(len(self.con.cursor_obj.executions),1)
        self.assertIn("tappad_internal.tappad_aplicar_activacion_comercial",
                      self.con.cursor_obj.executions[0][0])


if __name__=="__main__":
    unittest.main()
