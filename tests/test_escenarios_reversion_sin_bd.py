"""Pruebas gratuitas de la politica de suspension, sin base ni red.

Modelo de decisiones para detectar regresiones en los casos de multiples
pagos. No sustituye la prueba SQL real con PostgreSQL.
"""
import unittest


def suspender(*, acceso, periodo_vigente, activaciones, pago_revertido, ahora):
    if acceso != "habilitado":
        return False
    actuales = [a for a in activaciones
                if a["estado"] == "aplicada"
                and a["periodo_fin"] == periodo_vigente]
    return (len(actuales) == 1
            and actuales[0]["pago_id"] == pago_revertido
            and actuales[0]["periodo_inicio"] <= ahora < actuales[0]["periodo_fin"])


class EscenariosReversionTests(unittest.TestCase):
    def setUp(self):
        self.actual = dict(pago_id=10, estado="aplicada",
                           periodo_inicio=100, periodo_fin=200)
    def evaluar(self, activaciones, pago=10, acceso="habilitado"):
        return suspender(acceso=acceso, periodo_vigente=200,
                         activaciones=activaciones, pago_revertido=pago,
                         ahora=150)
    def test_reembolso_del_unico_pago_vigente_suspende(self):
        self.assertTrue(self.evaluar([self.actual]))
    def test_contracargo_del_unico_pago_vigente_suspende(self):
        self.assertTrue(self.evaluar([self.actual]))
    def test_reversion_de_periodo_anterior_no_suspende(self):
        anterior=dict(pago_id=9,estado="aplicada",periodo_inicio=0,periodo_fin=100)
        self.assertFalse(self.evaluar([anterior,self.actual],pago=9))
    def test_pago_nuevo_respalda_periodo_actual(self):
        anterior=dict(pago_id=9,estado="aplicada",periodo_inicio=0,periodo_fin=100)
        self.assertFalse(self.evaluar([anterior,self.actual],pago=9))
    def test_dos_activaciones_mismo_periodo_no_suspende(self):
        segunda=dict(self.actual,pago_id=11)
        self.assertFalse(self.evaluar([self.actual,segunda]))
    def test_acceso_no_habilitado_no_cambia(self):
        self.assertFalse(self.evaluar([self.actual],acceso="suspendido"))
    def test_sin_activaciones_no_suspende(self):
        self.assertFalse(self.evaluar([]))
    def test_periodo_expirado_no_suspende(self):
        vencida=dict(self.actual,periodo_inicio=0,periodo_fin=200)
        self.assertFalse(suspender(acceso="habilitado",periodo_vigente=200,
                         activaciones=[vencida],pago_revertido=10,ahora=201))


if __name__=="__main__":
    unittest.main()
