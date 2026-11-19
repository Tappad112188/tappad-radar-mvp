"""Pruebas aisladas del ejecutor: sin red, base real ni cobros."""
import os
import unittest
from unittest.mock import patch
from conciliar_reversion_privada_postgres import conciliar_reversion_privada
from verificar_pago_mercadopago_servidor import VerificacionRechazada


class Cursor:
    def __init__(self, *, applied=True, missing=False):
        self.calls = []
        self.applied = applied
        self.missing = missing
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def execute(self, sql, params): self.calls.append((sql, params))
    def fetchone(self):
        n = len(self.calls)
        if n == 1: return None if self.missing else (7,)
        if n == 2: return (7, "mercadopago_produccion", "sub-1")
        if n == 3: return (9, 7, "mercadopago_produccion", "pay-1")
        return (self.applied,)


class Conn:
    def __init__(self, **kwargs):
        self.c = Cursor(**kwargs)
        self.committed = False
        self.rolled_back = False
    def __enter__(self): return self
    def __exit__(self, kind, *args):
        self.rolled_back = kind is not None
        self.committed = kind is None
        return False
    def cursor(self): return self.c


class WorkerTests(unittest.TestCase):
    def setUp(self):
        self.conn = Conn()
        self.audit_calls = []
    def connect(self, dsn):
        self.assertEqual(dsn, "local-test")
        return self.conn
    def auditar(self, sub, pay, **kwargs):
        self.audit_calls.append((sub, pay, kwargs))
        return {"decision": "revision_revocacion_pago",
                "estado_pago_remoto": "refunded",
                "evidencia": {"origen": "consulta_directa_mercadopago",
                             "seller_id": "11", "payment_id": "pay-1",
                             "preapproval_id": "sub-1"}}
    def run_worker(self, **kwargs):
        return conciliar_reversion_privada(
            9, postgres_dsn="local-test", token="fake", seller_id="11",
            connect=self.connect, auditar=self.auditar, **kwargs)
    def test_bloqueado_por_defecto(self):
        with patch.dict(os.environ, {"TAPPAD_HABILITAR_REVERSION_PRODUCCION": "NO"}):
            self.assertEqual(self.run_worker(permitir=True)["escrituras"], 0)
        self.assertEqual(self.conn.c.calls, [])
    def test_reembolso_aplicado(self):
        with patch.dict(os.environ, {"TAPPAD_HABILITAR_REVERSION_PRODUCCION": "SI"}):
            result = self.run_worker(permitir=True)
        self.assertEqual(result["estado"], "aplicada")
        self.assertTrue(self.conn.committed)
        self.assertEqual(len(self.conn.c.calls), 4)
    def test_idempotente(self):
        self.conn = Conn(applied=False)
        with patch.dict(os.environ, {"TAPPAD_HABILITAR_REVERSION_PRODUCCION": "SI"}):
            self.assertEqual(self.run_worker(permitir=True)["estado"], "ya_conciliada")
    def test_evidencia_invalida_revierte(self):
        def bad(*args, **kwargs):
            return {"decision": "revision_revocacion_pago",
                    "estado_pago_remoto": "refunded",
                    "evidencia": {"seller_id": "otro"}}
        with patch.dict(os.environ, {"TAPPAD_HABILITAR_REVERSION_PRODUCCION": "SI"}):
            with self.assertRaises(VerificacionRechazada):
                conciliar_reversion_privada(9, postgres_dsn="local-test",
                    token="fake", seller_id="11", permitir=True,
                    connect=self.connect, auditar=bad)
        self.assertTrue(self.conn.rolled_back)
        self.assertEqual(len(self.conn.c.calls), 3)
    def test_sin_reversion_no_escribe(self):
        def approved(*args, **kwargs):
            return {"decision": "pago_aprobado_sujeto_a_conciliacion"}
        with patch.dict(os.environ, {"TAPPAD_HABILITAR_REVERSION_PRODUCCION": "SI"}):
            result = conciliar_reversion_privada(9, postgres_dsn="local-test",
                token="fake", seller_id="11", permitir=True,
                connect=self.connect, auditar=approved)
        self.assertEqual(result["escrituras"], 0)
        self.assertEqual(len(self.conn.c.calls), 3)
    def test_pago_inexistente_revierte(self):
        self.conn = Conn(missing=True)
        with patch.dict(os.environ, {"TAPPAD_HABILITAR_REVERSION_PRODUCCION": "SI"}):
            with self.assertRaisesRegex(VerificacionRechazada, "pago_no_encontrado"):
                self.run_worker(permitir=True)
        self.assertTrue(self.conn.rolled_back)


if __name__ == "__main__":
    unittest.main()
