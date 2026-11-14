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

    def evaluar(self):
        def fake_api(metodo, tabla, params=None, datos=None):
            self.assertEqual(metodo, "GET")
            if tabla == "acceso_comercial_tappad":
                return [self.acceso]
            if tabla == "suscripciones_tappad":
                return [self.suscripcion]
            raise AssertionError(tabla)
        with patch.object(mod, "api", fake_api), patch.dict(
            os.environ, {"TAPPAD_PROVEEDORES_COMERCIALES": "mercadopago_produccion"}):
            return mod.acceso_comercial_vigente(4, self.ahora)

    def test_vigencia_confirmada(self):
        self.assertTrue(self.evaluar())

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

    def test_fecha_ausente(self):
        self.acceso["vigente_hasta"] = None
        self.assertFalse(self.evaluar())

    def test_no_habilitar_sin_proveedor_configurado(self):
        with patch.object(mod, "api", lambda *a, **k:
                          [self.acceso] if a[1] == "acceso_comercial_tappad"
                          else [self.suscripcion]), patch.dict(
            os.environ, {"TAPPAD_PROVEEDORES_COMERCIALES": ""}):
            self.assertFalse(mod.acceso_comercial_vigente(4, self.ahora))


if __name__ == "__main__":
    unittest.main()
