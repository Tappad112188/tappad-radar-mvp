"""Pruebas del enlace Supabase-Mercado Pago sin red ni escrituras."""
import json
import unittest
from datetime import datetime, timezone
from conexion_segura_mercadopago_supabase import verificar_pago_desde_supabase
from verificar_pago_mercadopago_servidor import VerificacionRechazada


class Response:
    status = 200
    def __init__(self, payload): self.payload = json.dumps(payload).encode()
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self, n): return self.payload[:n]


class ConexionTests(unittest.TestCase):
    def setUp(self):
        self.db = {
            "pagos_tappad": [{"id": 2, "suscripcion_id": 7, "monto_mxn": 449,
                "estado": "pagado", "proveedor_cobro": "mercadopago_produccion",
                "referencia_externa": "pay-1", "fecha_pago": "2026-11-13T23:00:00Z"}],
            "suscripciones_tappad": [{"id": 7, "cliente_id": 4, "plan_id": 1,
                "estado": "pendiente", "proveedor_cobro": "mercadopago_produccion",
                "referencia_externa": "sub-1"}],
            "planes_tappad": [{"id": 1, "precio_mxn": 449, "activo": True,
                               "periodicidad": "mensual"}]}
        self.mp = {
            "/users/me": {"id": 5, "site_id": "MLM", "tags": []},
            "/preapproval/sub-1": {"id": "sub-1", "status": "authorized",
                "auto_recurring": {"transaction_amount": 449, "currency_id": "MXN",
                                   "frequency": 1, "frequency_type": "months"}},
            "/v1/payments/pay-1": {"id": "pay-1", "status": "approved",
                "currency_id": "MXN", "transaction_amount": 449,
                "date_approved": "2026-11-13T23:00:00Z",
                "preapproval_id": "sub-1"}}
        self.requests = []
    def db_open(self, req, timeout):
        self.requests.append((req.method, req.full_url))
        tabla = req.full_url.split("/rest/v1/")[1].split("?")[0]
        return Response(self.db[tabla])
    def mp_open(self, req, timeout):
        self.requests.append((req.method, req.full_url))
        path = req.full_url.removeprefix("https://api.mercadopago.com")
        return Response(self.mp[path])
    def run_check(self):
        return verificar_pago_desde_supabase(2,
            supabase_url="https://example.supabase.co", supabase_key="dummy",
            mercadopago_token="dummy", db_opener=self.db_open,
            mp_opener=self.mp_open,
            ahora=datetime(2026, 11, 14, tzinfo=timezone.utc))
    def test_enlace_valido_no_activa(self):
        result = self.run_check()
        self.assertEqual(result["aplicacion"], "bloqueada_hasta_rpc_autorizada")
        self.assertEqual(result["cliente_id"], 4)
        self.assertEqual(len(self.requests), 6)
        self.assertTrue(all(method == "GET" for method, _ in self.requests))
    def test_plan_inactivo_falla_antes_de_mercadopago(self):
        self.db["planes_tappad"][0]["activo"] = False
        with self.assertRaises(VerificacionRechazada): self.run_check()
        self.assertEqual(len(self.requests), 3)
    def test_pago_prueba_rechazado(self):
        self.db["pagos_tappad"][0]["proveedor_cobro"] = "mercadopago_prueba"
        with self.assertRaises(VerificacionRechazada): self.run_check()
        self.assertEqual(len(self.requests), 1)
    def test_suscripcion_duplicada_rechazada(self):
        self.db["suscripciones_tappad"].append(self.db["suscripciones_tappad"][0])
        with self.assertRaises(VerificacionRechazada): self.run_check()
        self.assertEqual(len(self.requests), 2)
    def test_id_invalido(self):
        with self.assertRaises(VerificacionRechazada):
            verificar_pago_desde_supabase(True,
                supabase_url="https://example.supabase.co",supabase_key="dummy",
                mercadopago_token="dummy",db_opener=self.db_open,
                mp_opener=self.mp_open)
        self.assertEqual(self.requests, [])

if __name__ == "__main__":
    unittest.main()
