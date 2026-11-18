import unittest
from datetime import datetime, timezone
from evidencia_auditoria_mercadopago import preparar_evidencia_estado
from verificar_pago_mercadopago_servidor import VerificacionRechazada


class EvidenciaTests(unittest.TestCase):
    def setUp(self):
        self.base = {"pago_id_local":8,"suscripcion_id_local":3,
                     "decision":"revision_revocacion_pago","modo":"SOLO_LECTURA"}
        self.ahora=datetime(2026,11,17,tzinfo=timezone.utc)
    def test_evidencia_reembolso_no_revoca(self):
        result=preparar_evidencia_estado(self.base,ahora=self.ahora)
        self.assertEqual(result["pago_id"],8)
        self.assertFalse(result["aplica_cambios"])
        self.assertTrue(result["requiere_conciliacion_privada"])
    def test_sin_modo_confiable(self):
        with self.assertRaises(VerificacionRechazada):
            preparar_evidencia_estado({**self.base,"modo":"ESCRITURA"})
    def test_decision_desconocida(self):
        with self.assertRaises(VerificacionRechazada):
            preparar_evidencia_estado({**self.base,"decision":"activar"})
    def test_id_booleano_rechazado(self):
        with self.assertRaises(VerificacionRechazada):
            preparar_evidencia_estado({**self.base,"pago_id_local":True})
    def test_fecha_sin_zona(self):
        with self.assertRaises(VerificacionRechazada):
            preparar_evidencia_estado(self.base,ahora=self.ahora.replace(tzinfo=None))


if __name__=="__main__":
    unittest.main()
