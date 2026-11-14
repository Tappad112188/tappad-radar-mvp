import os
import unittest
from unittest.mock import patch
from worker_activacion_comercial import ejecutar
from verificar_pago_mercadopago_servidor import VerificacionRechazada

class WorkerTests(unittest.TestCase):
    def config(self,**kw):
        return dict(supabase_url="https://demo.supabase.co",supabase_key="secret",
                    mercadopago_token="token",**kw)
    def test_no_autorizado_no_consulta(self):
        with patch.dict(os.environ,{"TAPPAD_HABILITAR_ACTIVACION_PRODUCCION":"NO"}):
            with self.assertRaisesRegex(VerificacionRechazada,"activacion_no_autorizada"):
                ejecutar(**self.config(activar=True,confirmacion="ACTIVAR"),
                        listar=lambda **kw: self.fail("No debe consultar"))
    def test_solo_lectura_no_activa(self):
        with patch.dict(os.environ,{"TAPPAD_MERCADOPAGO_SELLER_ID":"42"}):
            r=ejecutar(**self.config(),
                listar=lambda **kw:[9],
                verificar=lambda *a,**kw:{"evidencia":{"seller_id":"42"}},
                aplicar=lambda *a,**kw:self.fail("No debe activar"))
        self.assertEqual(r["resultados"][0]["estado"],"verificado_sin_activar")
    def test_vendedor_incorrecto_bloquea(self):
        with patch.dict(os.environ,{"TAPPAD_MERCADOPAGO_SELLER_ID":"42"}):
            r=ejecutar(**self.config(),
                listar=lambda **kw:[9],
                verificar=lambda *a,**kw:{"evidencia":{"seller_id":"otro"}},
                aplicar=lambda *a,**kw:self.fail("No debe activar"))
        self.assertEqual(r["resultados"][0]["estado"],"bloqueado")
    def test_lote_duplicado_bloquea(self):
        with self.assertRaisesRegex(VerificacionRechazada,"lote_de_pagos_invalido"):
            ejecutar(**self.config(),listar=lambda **kw:[9,9])
    def test_activacion_controlada(self):
        with patch.dict(os.environ,{"TAPPAD_MERCADOPAGO_SELLER_ID":"42",
                                    "TAPPAD_HABILITAR_ACTIVACION_PRODUCCION":"SI"}):
            r=ejecutar(**self.config(activar=True,confirmacion="ACTIVAR",
                                     postgres_dsn="postgresql://private"),
                listar=lambda **kw:[9],
                verificar=lambda *a,**kw:{"evidencia":{"seller_id":"42"}},
                aplicar=lambda *a,**kw:{"aplicacion":"aplicada"})
        self.assertEqual(r["resultados"][0]["estado"],"aplicada")

if __name__=="__main__":unittest.main()
