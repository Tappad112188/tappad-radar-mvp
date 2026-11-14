"""Pruebas aisladas: sin API, credenciales, cargos ni escrituras."""
import unittest
from datetime import datetime, timezone
from conciliacion_comercial_mercadopago import evaluar_pago_comercial


class ConciliacionMercadoPago(unittest.TestCase):
    def setUp(self):
        self.ahora = datetime(2026, 11, 14, tzinfo=timezone.utc)
        self.s = {"id": 7, "proveedor_cobro": "mercadopago_produccion",
                  "referencia_externa": "preapproval-123"}
        self.local = {"suscripcion_id": 7, "proveedor_cobro": "mercadopago_produccion",
                      "estado": "pagado", "referencia_externa": "pay-456",
                      "monto_mxn": "449.00", "fecha_pago": "2026-11-14T01:00:00Z"}
        self.remoto = {"id": "pay-456", "status": "approved",
                       "currency_id": "MXN", "transaction_amount": 449,
                       "date_approved": "2026-11-14T01:00:00Z",
                       "preapproval_id": "preapproval-123"}

    def evaluar(self):
        return evaluar_pago_comercial(self.s, self.local, self.remoto,
                                      ahora=self.ahora, importe_esperado="449.00")[0]

    def test_pago_comercial_coincidente(self):
        self.assertTrue(self.evaluar())

    def test_proveedor_prueba(self):
        self.s["proveedor_cobro"] = "mercadopago_prueba"
        self.assertFalse(self.evaluar())

    def test_pago_rechazado(self):
        self.remoto["status"] = "rejected"
        self.assertFalse(self.evaluar())

    def test_importe_distinto(self):
        self.remoto["transaction_amount"] = "448.99"
        self.assertFalse(self.evaluar())

    def test_importe_local_distinto(self):
        self.local["monto_mxn"] = "448.00"
        self.assertFalse(self.evaluar())

    def test_fecha_local_ausente(self):
        self.local["fecha_pago"] = None
        self.assertFalse(self.evaluar())

    def test_fecha_local_futura(self):
        self.local["fecha_pago"] = "2026-12-14T01:00:00Z"
        self.assertFalse(self.evaluar())

    def test_suscripcion_sin_referencia(self):
        self.s["referencia_externa"] = None
        self.assertFalse(self.evaluar())

    def test_referencia_ajena(self):
        self.remoto["id"] = "pay-otro"
        self.assertFalse(self.evaluar())

    def test_suscripcion_ajena(self):
        self.remoto["preapproval_id"] = "preapproval-otro"
        self.assertFalse(self.evaluar())

    def test_pago_local_pendiente(self):
        self.local["estado"] = "pendiente"
        self.assertFalse(self.evaluar())

    def test_moneda_distinta(self):
        self.remoto["currency_id"] = "USD"
        self.assertFalse(self.evaluar())

    def test_fecha_futura(self):
        self.remoto["date_approved"] = "2026-12-14T01:00:00Z"
        self.assertFalse(self.evaluar())

    def test_importe_no_finito(self):
        self.remoto["transaction_amount"] = "NaN"
        self.assertFalse(self.evaluar())


if __name__ == "__main__":
    unittest.main()
