"""Compuertas de liberacion: sin red, sin cobros y sin escrituras."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class GateComercial(unittest.TestCase):
    def test_borrador_no_usa_security_definer(self):
        sql = (ROOT/"docs/sql_conciliacion_reversion_mercadopago_borrador.sql").read_text().lower()
        self.assertIn("security invoker", sql)
        self.assertNotIn("security definer", sql)
        self.assertIn("revoke all on function", sql)

    def test_orden_de_bloqueos_alineado(self):
        sql = (ROOT/"docs/sql_conciliacion_reversion_mercadopago_borrador.sql").read_text().lower()
        self.assertLess(sql.index("from public.suscripciones_tappad\n    where"), sql.index("from public.acceso_comercial_tappad a\n    where"))
        self.assertLess(sql.index("from public.acceso_comercial_tappad a\n    where"), sql.index("from public.pagos_tappad\n    where"))
        worker = (ROOT/"conciliar_reversion_privada_postgres.py").read_text().lower()
        self.assertLess(worker.index("from public.suscripciones_tappad"), worker.index("from public.acceso_comercial_tappad"))
        self.assertLess(worker.index("from public.acceso_comercial_tappad"), worker.index("from public.pagos_tappad where id=%s and"))

    def test_estado_contracargo_requiere_migracion(self):
        sql = (ROOT/"docs/sql_preparacion_reversion_privada_NO_APLICAR.sql").read_text().lower()
        self.assertIn("'contracargo'", sql)
        self.assertIn("pagos_tappad_estado_check", sql)
        self.assertIn("nobypassrls", sql)
        self.assertIn("nologin", sql)
        self.assertIn("enable row level security", sql)

    def test_worker_cerrado_por_defecto(self):
        py = (ROOT/"conciliar_reversion_privada_postgres.py").read_text()
        self.assertIn('os.getenv("TAPPAD_HABILITAR_REVERSION_PRODUCCION") != "SI"', py)
        self.assertIn("permitir=False", py)

if __name__ == "__main__":
    unittest.main()
