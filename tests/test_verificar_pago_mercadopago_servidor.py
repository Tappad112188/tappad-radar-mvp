"""Pruebas sin red, sin secretos y sin modificar Supabase."""
import json
import unittest
from datetime import datetime, timezone
from io import BytesIO
from urllib.error import HTTPError
from verificar_pago_mercadopago_servidor import (
    VerificacionRechazada, verificar_pago_servidor)


class Response:
    status = 200
    def __init__(self, data):
        self.data = json.dumps(data).encode()
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self, n): return self.data[:n]


class VerificadorTests(unittest.TestCase):
    def setUp(self):
        self.s = {"id": 7, "proveedor_cobro": "mercadopago_produccion",
                  "referencia_externa": "sub-1"}
        self.p = {"suscripcion_id": 7, "proveedor_cobro": "mercadopago_produccion",
                  "referencia_externa": "pay-1", "estado": "pagado",
                  "monto_mxn": "449", "fecha_pago": "2026-11-13T23:00:00Z"}
        self.responses = {
            "/users/me": {"id": 11, "site_id": "MLM", "tags": []},
            "/preapproval/sub-1": {"id": "sub-1", "status": "authorized",
                "auto_recurring": {"currency_id": "MXN", "frequency_type": "months",
                                   "frequency": 1, "transaction_amount": 449}},
            "/v1/payments/pay-1": {"id": "pay-1", "status": "approved",
                "currency_id": "MXN", "transaction_amount": 449,
                "date_approved": "2026-11-13T23:00:00Z",
                "preapproval_id": "sub-1"}
        }
        self.visits = []
    def opener(self, request, timeout):
        self.visits.append(request.full_url)
        path = request.full_url.removeprefix("https://api.mercadopago.com")
        return Response(self.responses[path])
    def verificar(self):
        return verificar_pago_servidor(self.s, self.p, importe_esperado="449",
            token="dummy-test-token", ahora=datetime(2026,11,14,tzinfo=timezone.utc),
            opener=self.opener)
    def test_evidencia_valida(self):
        self.assertEqual(self.verificar()["payment_id"], "pay-1")
        self.assertEqual(len(self.visits), 3)
    def test_vendedor_de_prueba(self):
        self.responses["/users/me"]["tags"] = ["test_user"]
        with self.assertRaises(VerificacionRechazada): self.verificar()
    def test_plan_anual_verificado(self):
        self.responses["/preapproval/sub-1"]["auto_recurring"].update(
            {"frequency": 12, "transaction_amount": 4490})
        self.responses["/v1/payments/pay-1"]["transaction_amount"] = 4490
        self.p["monto_mxn"] = "4490"
        result = verificar_pago_servidor(self.s, self.p,
            importe_esperado=4490, periodicidad="anual",
            token="dummy-test-token",
            ahora=datetime(2026,11,14,tzinfo=timezone.utc),
            opener=self.opener)
        self.assertEqual(result["entorno"], "produccion")

    def test_pago_de_otro_vendedor(self):
        self.responses["/v1/payments/pay-1"]["collector_id"] = 99
        with self.assertRaises(VerificacionRechazada): self.verificar()

    def test_suscripcion_cancelada(self):
        self.responses["/preapproval/sub-1"]["status"] = "cancelled"
        with self.assertRaises(VerificacionRechazada): self.verificar()
    def test_pago_sin_vinculo(self):
        self.responses["/v1/payments/pay-1"].pop("preapproval_id")
        self.responses["/authorized_payments/search?preapproval_id=sub-1&limit=100&offset=0"] = {"results": []}
        with self.assertRaises(VerificacionRechazada): self.verificar()
    def test_pago_recurrente_vinculado_en_authorized_payments(self):
        self.responses["/v1/payments/pay-1"].pop("preapproval_id")
        self.responses["/authorized_payments/search?preapproval_id=sub-1&limit=100&offset=0"] = {
            "results": [{"preapproval_id": "sub-1", "payment": {"id": "pay-1"}}]}
        self.assertEqual(self.verificar()["payment_id"], "pay-1")
        self.assertEqual(len(self.visits), 4)

    def test_pago_de_otra_suscripcion(self):
        self.responses["/v1/payments/pay-1"]["preapproval_id"] = "otra"
        with self.assertRaises(VerificacionRechazada): self.verificar()
    def test_monto_remoto_incorrecto(self):
        self.responses["/preapproval/sub-1"]["auto_recurring"]["transaction_amount"] = 448
        with self.assertRaises(VerificacionRechazada): self.verificar()
    def test_entorno_de_prueba_sin_consultas(self):
        self.s["proveedor_cobro"] = "mercadopago_prueba"
        with self.assertRaises(VerificacionRechazada): self.verificar()
        self.assertEqual(self.visits, [])
    def test_identificador_inyectado_sin_consultas(self):
        self.p["referencia_externa"] = "pay-1?foo=bar"
        with self.assertRaises(VerificacionRechazada): self.verificar()
        self.assertEqual(self.visits, [])

if __name__ == "__main__":
    unittest.main()
