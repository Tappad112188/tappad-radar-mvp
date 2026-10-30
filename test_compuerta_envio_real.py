import unittest
from datetime import datetime
from control_notificaciones import autorizar_envio_real
from preparador_alertas import filtrar_lote_para_envio_real


class PruebasSeguridadEnvios(unittest.TestCase):
    def setUp(self):
        self.ahora = datetime(2026, 10, 30, 9, 0)
        self.licitacion = {"id": 10, "estatus": "Vigente", "fecha_apertura": "2026-11-06T12:00:00"}
        self.config = {"alertas_automaticas_habilitadas": "true"}

    def test_apagado_por_defecto(self):
        self.assertFalse(autorizar_envio_real({}, self.licitacion, ahora=self.ahora)[0])
        self.assertFalse(autorizar_envio_real({"alertas_automaticas_habilitadas": "false"}, self.licitacion, ahora=self.ahora)[0])

    def test_vigencia_y_duplicados(self):
        self.assertTrue(autorizar_envio_real(self.config, self.licitacion, ahora=self.ahora)[0])
        for estado in ("pendiente", "procesando", "enviado", "error"):
            self.assertFalse(autorizar_envio_real(self.config, self.licitacion, estado, self.ahora)[0])
        self.assertFalse(autorizar_envio_real(self.config, {**self.licitacion, "fecha_apertura": None}, ahora=self.ahora)[0])
        self.assertFalse(autorizar_envio_real(self.config, {**self.licitacion, "fecha_apertura": "2026-10-29T12:00:00"}, ahora=self.ahora)[0])
        self.assertFalse(autorizar_envio_real(self.config, {**self.licitacion, "estatus": "Cancelado"}, ahora=self.ahora)[0])

    def test_integracion_lote(self):
        lote = {"por_proveedor": {3: [{"licitacion_id": 10}]}}
        self.assertEqual(filtrar_lote_para_envio_real(lote, [self.licitacion], [], {}, self.ahora)["por_proveedor"], {})
        self.assertEqual(len(filtrar_lote_para_envio_real(lote, [self.licitacion], [], self.config, self.ahora)["por_proveedor"][3]), 1)
        historial = [{"cliente_id": 3, "licitacion_id": 10, "estado": "enviado"}]
        self.assertEqual(filtrar_lote_para_envio_real(lote, [self.licitacion], historial, self.config, self.ahora)["por_proveedor"], {})


if __name__ == "__main__":
    unittest.main()
