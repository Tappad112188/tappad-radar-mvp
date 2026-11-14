"""Contrato del aplicador: no escribe sin dos habilitaciones."""
import json
import os
import unittest
from unittest.mock import patch
from aplicar_activacion_comercial_controlada import ejecutar_activacion_controlada
from verificar_pago_mercadopago_servidor import VerificacionRechazada


EVIDENCIA = {"cliente_id": 4, "suscripcion_id": 7, "pago_id": 2,
 "evidencia": {"payment_id": "pay-1", "preapproval_id": "sub-1",
              "verificacion_remota": "confirmada", "entorno": "produccion",
              "seller_id": "11"}}


class Response:
    status = 200
    def __init__(self, value): self.value = json.dumps(value).encode()
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self, n): return self.value


class AplicacionTests(unittest.TestCase):
    def setUp(self):
        self.requests = []
    def rpc(self, request, timeout):
        self.requests.append(request)
        return Response(True)
    def ejecutar(self, habilitar=False):
        return ejecutar_activacion_controlada(2,
            supabase_url="https://example.supabase.co", supabase_key="dummy",
            mercadopago_token="dummy", inicio="2026-11-14T00:00:00Z",
            fin="2026-12-14T00:00:00Z", habilitar=habilitar,
            rpc_opener=self.rpc)
    @patch("aplicar_activacion_comercial_controlada.verificar_pago_desde_supabase",
           return_value=EVIDENCIA)
    def test_sin_flag_no_escribe(self, _):
        with patch.dict(os.environ, {"TAPPAD_HABILITAR_ACTIVACION_PRODUCCION": "SI"}):
            self.assertEqual(self.ejecutar()["aplicacion"], "simulada_sin_escrituras")
        self.assertEqual(self.requests, [])
    @patch("aplicar_activacion_comercial_controlada.verificar_pago_desde_supabase",
           return_value=EVIDENCIA)
    def test_sin_entorno_no_escribe(self, _):
        with patch.dict(os.environ, {"TAPPAD_HABILITAR_ACTIVACION_PRODUCCION": "NO"}):
            self.assertEqual(self.ejecutar(True)["aplicacion"], "simulada_sin_escrituras")
        self.assertEqual(self.requests, [])
    @patch("aplicar_activacion_comercial_controlada.verificar_pago_desde_supabase",
           return_value=EVIDENCIA)
    def test_ambos_flags_rpc_una_vez(self, _):
        with patch.dict(os.environ, {"TAPPAD_HABILITAR_ACTIVACION_PRODUCCION": "SI"}):
            self.assertEqual(self.ejecutar(True)["aplicacion"], "aplicada")
        self.assertEqual(len(self.requests), 1)
        self.assertEqual(self.requests[0].get_method(), "POST")
        self.assertEqual(json.loads(self.requests[0].data)["p_pago"], 2)
    @patch("aplicar_activacion_comercial_controlada.verificar_pago_desde_supabase",
           return_value=EVIDENCIA)
    def test_rpc_rechaza_pago_repetido(self, _):
        self.rpc = lambda request, timeout: Response(False)
        with patch.dict(os.environ, {"TAPPAD_HABILITAR_ACTIVACION_PRODUCCION": "SI"}):
            with self.assertRaisesRegex(VerificacionRechazada, "activacion_rechazada"):
                self.ejecutar(True)
    @patch("aplicar_activacion_comercial_controlada.verificar_pago_desde_supabase",
           side_effect=VerificacionRechazada("pago_no_productivo"))
    def test_pago_invalido_no_llama_rpc(self, _):
        with patch.dict(os.environ, {"TAPPAD_HABILITAR_ACTIVACION_PRODUCCION": "SI"}):
            with self.assertRaises(VerificacionRechazada): self.ejecutar(True)
        self.assertEqual(self.requests, [])


if __name__ == "__main__":
    unittest.main()
