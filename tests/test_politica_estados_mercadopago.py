import unittest
from politica_estados_mercadopago import clasificar_estado_remoto


class EstadosRemotosTests(unittest.TestCase):
    def evaluar(self, pago="approved", suscripcion="authorized", vinculo=True, vendedor=True):
        return clasificar_estado_remoto(
            estado_pago=pago, estado_suscripcion=suscripcion,
            vinculo_verificado=vinculo, vendedor_verificado=vendedor)

    def test_aprobado_no_activa_directamente(self):
        self.assertEqual(self.evaluar(), "pago_aprobado_sujeto_a_conciliacion")

    def test_reembolso(self):
        self.assertEqual(self.evaluar(pago="refunded"), "revision_revocacion_pago")

    def test_contracargo(self):
        self.assertEqual(self.evaluar(pago="charged_back"), "revision_revocacion_pago")

    def test_rechazado(self):
        self.assertEqual(self.evaluar(pago="rejected"), "revision_pago_no_aprobado")

    def test_cancelado(self):
        self.assertEqual(self.evaluar(pago="cancelled"), "revision_pago_no_aprobado")

    def test_suscripcion_cancelada_con_pago_aprobado(self):
        self.assertEqual(self.evaluar(suscripcion="cancelled"),
                         "revision_suscripcion_no_renovable")

    def test_suscripcion_pausada(self):
        self.assertEqual(self.evaluar(suscripcion="paused"),
                         "revision_suscripcion_no_renovable")

    def test_vendedor_ajeno(self):
        self.assertEqual(self.evaluar(vendedor=False), "bloquear_evidencia_insuficiente")

    def test_vinculo_ajeno(self):
        self.assertEqual(self.evaluar(vinculo=False), "bloquear_evidencia_insuficiente")

    def test_estado_desconocido(self):
        self.assertEqual(self.evaluar(pago="unknown"), "revision_estado_pago_desconocido")


if __name__ == "__main__":
    unittest.main()
