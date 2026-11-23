"""Prueba integral de flujo comercial aislado, sin red, cobros ni BD real.

Verifica lectura Supabase -> Mercado Pago -> decision de aplicacion -> RPC
simulado. NO equivale a una transaccion real en Supabase.
"""
import json
import os
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from aplicar_activacion_comercial_controlada import ejecutar_activacion_controlada
from verificar_pago_mercadopago_servidor import VerificacionRechazada


class Response:
    status = 200
    def __init__(self, data): self.payload = json.dumps(data).encode()
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self, n): return self.payload[:n]


class FlujoIntegralTests(unittest.TestCase):
    def setUp(self):
        self.db = {
            "pagos_tappad": [{"id": 2, "suscripcion_id": 7, "monto_mxn": 449,
                "estado": "pagado", "proveedor_cobro": "mercadopago_produccion",
                "referencia_externa": "pay-1", "fecha_pago": "2026-11-13T23:00:00Z"}],
            "suscripciones_tappad": [{"id": 7, "cliente_id": 4, "plan_id": 1,
                "estado": "pendiente", "proveedor_cobro": "mercadopago_produccion",
                "referencia_externa": "sub-1"}],
            "planes_tappad": [{"id": 1, "precio_mxn": 449, "activo": True,
                               "periodicidad": "mensual"}]
        }
        self.mp = {
            "/users/me": {"id": 5, "site_id": "MLM", "tags": []},
            "/preapproval/sub-1": {"id": "sub-1", "status": "authorized",
                "auto_recurring": {"transaction_amount": 449, "currency_id": "MXN",
                                   "frequency": 1, "frequency_type": "months"}},
            "/v1/payments/pay-1": {"id": "pay-1", "status": "approved", "live_mode": True,
                "currency_id": "MXN", "transaction_amount": 449,
                "collector_id": 5, "date_approved": "2026-11-13T23:00:00Z",
                "preapproval_id": "sub-1"}
        }
        self.calls = []
        self.applied = set()
    def db_open(self, req, timeout):
        self.calls.append(("db", req.get_method()))
        name = req.full_url.split("/rest/v1/")[1].split("?")[0]
        return Response(self.db[name])
    def mp_open(self, req, timeout):
        self.calls.append(("mp", req.get_method()))
        return Response(self.mp[req.full_url.removeprefix("https://api.mercadopago.com")])
    def rpc_open(self, req, timeout):
        self.calls.append(("rpc", req.get_method()))
        args = json.loads(req.data)
        if args["p_pago"] in self.applied:
            return Response(False)
        self.applied.add(args["p_pago"])
        return Response(True)
    def ejecutar(self, habilitar):
        with patch.dict(os.environ, {"TAPPAD_HABILITAR_ACTIVACION_PRODUCCION": "SI"}):
            return ejecutar_activacion_controlada(
                2, supabase_url="https://example.supabase.co",
                supabase_key="dummy", mercadopago_token="dummy",
                inicio="2026-11-14T00:00:00Z", fin="2026-12-14T00:00:00Z",
                habilitar=habilitar, db_opener=self.db_open,
                mp_opener=self.mp_open, rpc_opener=self.rpc_open)
    def test_simulacion_integral_sin_escritura(self):
        self.assertEqual(self.ejecutar(False)["aplicacion"], "simulada_sin_escrituras")
        self.assertEqual([c for c in self.calls if c[0] == "rpc"], [])
    def test_pago_valido_se_aplica_una_vez_y_repetido_se_rechaza(self):
        self.assertEqual(self.ejecutar(True)["aplicacion"], "aplicada")
        with self.assertRaisesRegex(VerificacionRechazada, "activacion_rechazada"):
            self.ejecutar(True)
        self.assertEqual(self.applied, {2})
        self.assertEqual(len([c for c in self.calls if c[0] == "rpc"]), 2)
    def test_pago_rechazado_no_llega_a_rpc(self):
        self.mp["/v1/payments/pay-1"]["status"] = "rejected"
        with self.assertRaises(VerificacionRechazada): self.ejecutar(True)
        self.assertFalse(self.applied)
        self.assertFalse(any(c[0] == "rpc" for c in self.calls))
    def test_pago_prueba_no_llega_a_mercadopago(self):
        self.db["pagos_tappad"][0]["proveedor_cobro"] = "mercadopago_prueba"
        with self.assertRaises(VerificacionRechazada): self.ejecutar(True)
        self.assertEqual(self.calls, [("db", "GET")])
    def test_monto_incorrecto_no_llega_a_rpc(self):
        self.mp["/v1/payments/pay-1"]["transaction_amount"] = 448
        with self.assertRaises(VerificacionRechazada): self.ejecutar(True)
        self.assertFalse(any(c[0] == "rpc" for c in self.calls))


if __name__ == "__main__":
    unittest.main()
