"""Regresion estructural del borrador SQL privado, sin conexion ni escrituras."""
import unittest
from pathlib import Path

SQL = (Path(__file__).resolve().parents[1] /
       "docs/sql_conciliacion_reversion_mercadopago_borrador.sql").read_text()


class BorradorReversionTests(unittest.TestCase):
    def test_no_funcion_publica(self):
        self.assertIn("tappad_internal.conciliar_reversion_pago", SQL)
        self.assertNotIn("create or replace function public.", SQL.lower())
    def test_invoker_y_revocacion(self):
        self.assertIn("security invoker", SQL.lower())
        self.assertIn("revoke all on function", SQL.lower())
    def test_evidencia_remota_obligatoria(self):
        self.assertIn("consulta_directa_mercadopago", SQL)
        self.assertIn("payment_id", SQL)
        self.assertIn("preapproval_id", SQL)
    def test_solo_reversiones(self):
        self.assertIn("('refunded','charged_back')", SQL)
        self.assertIn("transicion_conflictiva", SQL)
    def test_acceso_bloqueado_y_periodo_unico(self):
        self.assertIn("for update", SQL.lower())
        self.assertIn("v_activaciones_actuales=1", SQL)
        self.assertIn("x.periodo_inicio<=transaction_timestamp()", SQL)

    def test_registro_y_bloqueo_atomicos(self):
        self.assertIn("insert into tappad_internal.auditoria_estados_mercadopago", SQL.lower())
        self.assertIn("update public.pagos_tappad", SQL.lower())
        self.assertIn("update public.acceso_comercial_tappad", SQL.lower())
        self.assertIn("x.periodo_fin=v_acceso.vigente_hasta", SQL)


if __name__=="__main__":
    unittest.main()
