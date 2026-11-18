"""Pruebas sin red ni correo para el filtro de acceso comercial SECOP.

Ejecutar desde la raiz: python -m unittest tests/test_acceso_comercial_secop.py
"""
import importlib.util
import os
import sys
import types
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

sys.modules.setdefault("motor_alertas_secop", types.SimpleNamespace(
    consultar=lambda *a, **k: [], coincide=lambda *a, **k: False, PERMITIDOS=set()))
spec = importlib.util.spec_from_file_location(
    "entregar_alertas_secop", Path(__file__).resolve().parents[1] / "entregar_alertas_secop.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class AccesoComercialSecop(unittest.TestCase):
    def setUp(self):
        self.ahora = datetime(2026, 11, 14, tzinfo=timezone.utc)
        self.acceso = {"cliente_id": 4, "suscripcion_id": 9, "estado": "habilitado",
                       "vigente_hasta": (self.ahora + timedelta(days=5)).isoformat()}
        self.suscripcion = {"id": 9, "cliente_id": 4, "estado": "activa",
                            "proveedor_cobro": "mercadopago_produccion",
                            "fin_periodo": (self.ahora + timedelta(days=5)).isoformat()}

    def activacion(self):
        return {"cliente_id": 4, "suscripcion_id": 9, "pago_id": 20,
                "estado": "aplicada",
                "periodo_inicio": (self.ahora - timedelta(days=1)).isoformat(),
                "periodo_fin": (self.ahora + timedelta(days=5)).isoformat()}

    def pago(self):
        return {"id": 20, "suscripcion_id": 9, "estado": "pagado",
                "proveedor_cobro": "mercadopago_produccion",
                "referencia_externa": "referencia-confirmada"}

    def evaluar(self):
        def fake_api(metodo, tabla, params=None, datos=None):
            self.assertEqual(metodo, "GET")
            if tabla == "acceso_comercial_tappad":
                return [self.acceso]
            if tabla == "suscripciones_tappad":
                return [self.suscripcion]
            if tabla == "activaciones_comerciales_tappad":
                return [self.activacion()]
            if tabla == "pagos_tappad":
                return [self.pago()]
            raise AssertionError(tabla)
        with patch.object(mod, "api", fake_api), patch.dict(
            os.environ, {"TAPPAD_PROVEEDORES_COMERCIALES": "mercadopago_produccion"}):
            return mod.acceso_comercial_vigente(4, self.ahora)

    def test_vigencia_confirmada(self):
        self.assertTrue(self.evaluar())

    def test_suscripcion_cancelada_bloquea_acceso(self):
        self.suscripcion["estado"] = "cancelada"
        self.assertFalse(self.evaluar())

    def test_suscripcion_suspendida_bloquea_acceso(self):
        self.suscripcion["estado"] = "suspendida"
        self.assertFalse(self.evaluar())

    def test_pago_reembolsado_bloquea_acceso(self):
        self.pago = lambda: {**AccesoComercialSecop.pago(self), "estado": "reembolsado"}
        self.assertFalse(self.evaluar())

    def test_pago_contracargo_bloquea_acceso(self):
        self.pago = lambda: {**AccesoComercialSecop.pago(self), "estado": "contracargo"}
        self.assertFalse(self.evaluar())

    def test_pago_rechazado_bloquea_acceso(self):
        self.pago = lambda: {**AccesoComercialSecop.pago(self), "estado": "rechazado"}
        self.assertFalse(self.evaluar())

    def test_activacion_revocada_bloquea_acceso(self):
        self.activacion = lambda: {**AccesoComercialSecop.activacion(self), "estado": "revocada"}
        self.assertFalse(self.evaluar())

    def test_acceso_prueba_bloqueado(self):
        self.acceso["estado"] = "prueba"
        self.assertFalse(self.evaluar())

    def test_acceso_vencido_bloqueado(self):
        self.acceso["vigente_hasta"] = (self.ahora - timedelta(seconds=1)).isoformat()
        self.assertFalse(self.evaluar())

    def test_suscripcion_prueba_bloqueada(self):
        self.suscripcion["estado"] = "prueba"
        self.assertFalse(self.evaluar())

    def test_proveedor_prueba_bloqueado(self):
        self.suscripcion["proveedor_cobro"] = "mercadopago_prueba"
        self.assertFalse(self.evaluar())

    def test_periodo_suscripcion_vencido(self):
        self.suscripcion["fin_periodo"] = self.ahora.isoformat()
        self.assertFalse(self.evaluar())

    def test_suscripcion_sin_identificador(self):
        self.acceso["suscripcion_id"] = None
        self.assertFalse(self.evaluar())

    def test_acceso_mas_largo_que_suscripcion(self):
        self.acceso["vigente_hasta"] = (self.ahora + timedelta(days=6)).isoformat()
        self.assertFalse(self.evaluar())

    def test_fecha_ausente(self):
        self.acceso["vigente_hasta"] = None
        self.assertFalse(self.evaluar())

    def test_no_habilitar_sin_proveedor_configurado(self):
        with patch.dict(os.environ, {"TAPPAD_PROVEEDORES_COMERCIALES": ""}):
            with patch.object(mod, "api", lambda metodo, tabla, *args:
                              [self.acceso] if tabla == "acceso_comercial_tappad"
                              else [self.suscripcion]):
                self.assertFalse(mod.acceso_comercial_vigente(4, self.ahora))

    def test_sin_activacion_aplicada(self):
        original = self.activacion
        self.activacion = lambda: {**original(), "estado": "pendiente_revision"}
        # Consulta REST filtra aplicada: no devolver registros pendientes.
        def fake_api(metodo, tabla, *args):
            if tabla == "acceso_comercial_tappad": return [self.acceso]
            if tabla == "suscripciones_tappad": return [self.suscripcion]
            if tabla == "activaciones_comerciales_tappad": return []
            raise AssertionError(tabla)
        with patch.object(mod, "api", fake_api), patch.dict(
            os.environ, {"TAPPAD_PROVEEDORES_COMERCIALES": "mercadopago_produccion"}):
            self.assertFalse(mod.acceso_comercial_vigente(4, self.ahora))

    def test_pago_de_prueba_no_habilita(self):
        self.suscripcion["proveedor_cobro"] = "mercadopago_prueba"
        self.assertFalse(self.evaluar())

    def test_activacion_de_otro_cliente(self):
        self.activacion = lambda: {**AccesoComercialSecop.activacion(self), "cliente_id": 99}
        self.assertFalse(self.evaluar())

    def test_activacion_pendiente_no_autoriza(self):
        self.activacion = lambda: {**AccesoComercialSecop.activacion(self),
                                   "estado": "pendiente_revision"}
        self.assertFalse(self.evaluar())

    def test_pago_de_otra_suscripcion(self):
        self.pago = lambda: {**AccesoComercialSecop.pago(self), "suscripcion_id": 88}
        self.assertFalse(self.evaluar())

    def test_pago_sin_referencia(self):
        self.pago = lambda: {**AccesoComercialSecop.pago(self), "referencia_externa": None}
        self.assertFalse(self.evaluar())

    def test_activacion_expirada(self):
        self.activacion = lambda: {**AccesoComercialSecop.activacion(self),
            "periodo_fin": (self.ahora - timedelta(seconds=1)).isoformat()}
        self.assertFalse(self.evaluar())



if __name__ == "__main__":
    unittest.main()
