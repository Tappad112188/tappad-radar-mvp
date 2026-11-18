"""Pruebas sin red de la auditoria comercial (sin cobros ni activaciones)."""
import io
import json
import unittest
from unittest.mock import patch
from conciliador_pagos_pendientes_lectura import pendientes, auditar
from verificar_pago_mercadopago_servidor import VerificacionRechazada


class Respuesta:
    status = 200
    def __init__(self, data): self.data = data
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self, n=-1): return json.dumps(self.data).encode()


class AuditoriaTests(unittest.TestCase):
    def test_no_acepta_clave_ausente(self):
        with self.assertRaisesRegex(VerificacionRechazada, "supabase_clave_ausente"):
            pendientes(supabase_url="https://demo.supabase.co",supabase_key="")
    def test_no_acepta_url_ajena(self):
        with self.assertRaisesRegex(VerificacionRechazada, "supabase_url_invalida"):
            pendientes(supabase_url="http://localhost",supabase_key="key")
    def test_filtra_solo_productivos_pagados(self):
        urls=[]
        def opener(req,timeout):
            urls.append(req.full_url)
            if "activaciones_comerciales_tappad" in req.full_url:
                return Respuesta([])
            return Respuesta([{"id":8,"estado":"pagado","proveedor_cobro":"mercadopago_produccion"}])
        ids=pendientes(supabase_url="https://demo.supabase.co",supabase_key="key",opener=opener)
        self.assertEqual(ids,[8])
        self.assertIn("mercadopago_produccion",urls[0])
        self.assertIn("eq.pagado",urls[0])
    def test_pago_ya_activado_no_se_reprocesa(self):
        def opener(req,timeout):
            if "activaciones_comerciales_tappad" in req.full_url:
                return Respuesta([{"pago_id":8}])
            return Respuesta([{"id":8},{"id":9}])
        ids=pendientes(supabase_url="https://demo.supabase.co",
                       supabase_key="key",opener=opener)
        self.assertEqual(ids,[9])

    def test_activaciones_incompletas_falla_cerrada(self):
        def opener(req,timeout):
            if "activaciones_comerciales_tappad" in req.full_url:
                return Respuesta([{"pago_id":i} for i in range(1000)])
            return Respuesta([{"id":8}])
        with self.assertRaisesRegex(VerificacionRechazada,"activaciones_incompletas"):
            pendientes(supabase_url="https://demo.supabase.co",
                       supabase_key="key",opener=opener)

    def test_pago_duplicado_falla_cerrada(self):
        def opener(req,timeout):
            return Respuesta([{"id":8},{"id":8}])
        with self.assertRaisesRegex(VerificacionRechazada,"pagos_duplicados"):
            pendientes(supabase_url="https://demo.supabase.co",
                       supabase_key="key",opener=opener)

    @patch("conciliador_pagos_pendientes_lectura.verificar_pago_desde_supabase")
    @patch("conciliador_pagos_pendientes_lectura.pendientes",return_value=[3,4])
    def test_rechazo_no_activa_y_continua(self, obtener, verificar):
        verificar.side_effect=[VerificacionRechazada("pago_no_productivo"),{"cliente_id":4}]
        resultado=auditar(supabase_url="https://demo.supabase.co",
                         supabase_key="key",mercadopago_token="token")
        self.assertEqual(resultado["modo"],"SOLO_LECTURA")
        self.assertEqual(resultado["pagos_revisados"],2)
        self.assertEqual(resultado["resultados"][0]["resultado"],"bloqueado")
        self.assertEqual(resultado["resultados"][1]["resultado"],"verificado_sin_activar")
        self.assertEqual(verificar.call_count,2)
    def test_paginacion_falla_cerrada(self):
        def opener(req,timeout):
            return Respuesta([{"id":i} for i in range(1000)])
        with self.assertRaisesRegex(VerificacionRechazada,"paginacion_pendiente"):
            pendientes(supabase_url="https://demo.supabase.co",supabase_key="key",opener=opener)


if __name__=="__main__":
    unittest.main()
