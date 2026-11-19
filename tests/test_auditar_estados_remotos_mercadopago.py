import json
import unittest
from auditar_estados_remotos_mercadopago import auditar_estado_remoto
from verificar_pago_mercadopago_servidor import VerificacionRechazada


class Response:
    status = 200
    def __init__(self, value): self.value = value
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self, limit): return json.dumps(self.value).encode()


class AuditorRemotoTests(unittest.TestCase):
    def setUp(self):
        self.sub = {"id":7,"proveedor_cobro":"mercadopago_produccion",
                    "referencia_externa":"sub-1"}
        self.pago = {"id":9,"suscripcion_id":7,
                     "proveedor_cobro":"mercadopago_produccion",
                     "referencia_externa":"pay-1"}
        self.remotos = {
            "/users/me":{"id":11,"site_id":"MLM","tags":[]},
            "/preapproval/sub-1":{"id":"sub-1","status":"authorized"},
            "/v1/payments/pay-1":{"id":"pay-1","status":"approved",
                                   "collector_id":11,"preapproval_id":"sub-1"}}
        self.consultas=[]
    def opener(self, req, timeout):
        path=req.full_url.removeprefix("https://api.mercadopago.com")
        self.consultas.append(path)
        return Response(self.remotos[path])
    def auditar(self):
        return auditar_estado_remoto(self.sub,self.pago,token="token",
                                     seller_id_esperado="11",opener=self.opener)
    def test_aprobado_solo_lectura(self):
        self.assertEqual(self.auditar()["decision"],"pago_aprobado_sujeto_a_conciliacion")
        self.assertEqual(len(self.consultas),3)
    def test_reembolso_detectado(self):
        self.remotos["/v1/payments/pay-1"]["status"]="refunded"
        self.assertEqual(self.auditar()["decision"],"revision_revocacion_pago")
    def test_contracargo_detectado(self):
        self.remotos["/v1/payments/pay-1"]["status"]="charged_back"
        self.assertEqual(self.auditar()["decision"],"revision_revocacion_pago")
    def test_suscripcion_cancelada_detectada(self):
        self.remotos["/preapproval/sub-1"]["status"]="cancelled"
        self.assertEqual(self.auditar()["decision"],"revision_suscripcion_no_renovable")
    def test_vendedor_ajeno_rechazado(self):
        self.remotos["/users/me"]["id"]=12
        with self.assertRaises(VerificacionRechazada): self.auditar()
    def test_pago_ajeno_rechazado(self):
        self.remotos["/v1/payments/pay-1"]["collector_id"]=12
        with self.assertRaises(VerificacionRechazada): self.auditar()
    def test_vinculo_ausente_rechazado(self):
        self.remotos["/v1/payments/pay-1"].pop("preapproval_id")
        self.remotos["/authorized_payments/search?preapproval_id=sub-1&limit=100&offset=0"] = {"results":[]}
        with self.assertRaises(VerificacionRechazada): self.auditar()
    def test_vinculo_recurrente_verificado_por_autorizaciones(self):
        self.remotos["/v1/payments/pay-1"].pop("preapproval_id")
        self.remotos["/authorized_payments/search?preapproval_id=sub-1&limit=100&offset=0"] = {
            "results":[{"preapproval_id":"sub-1","payment":{"id":"pay-1"},"status":"processed"}]}
        self.assertEqual(self.auditar()["decision"],"pago_aprobado_sujeto_a_conciliacion")
        self.assertEqual(len(self.consultas),4)
    def test_vinculo_recurrente_duplicado_rechazado(self):
        self.remotos["/v1/payments/pay-1"].pop("preapproval_id")
        row={"preapproval_id":"sub-1","payment":{"id":"pay-1"},"status":"processed"}
        self.remotos["/authorized_payments/search?preapproval_id=sub-1&limit=100&offset=0"] = {"results":[row,row]}
        with self.assertRaises(VerificacionRechazada): self.auditar()
    def test_vinculo_directo_contradictorio_rechazado(self):
        self.remotos["/v1/payments/pay-1"]["preapproval_id"]="otra-sub"
        with self.assertRaises(VerificacionRechazada): self.auditar()
    def test_entorno_prueba_rechazado_antes_de_red(self):
        self.sub["proveedor_cobro"]="mercadopago_prueba"
        with self.assertRaises(VerificacionRechazada): self.auditar()
        self.assertEqual(self.consultas,[])
    def test_identificador_invalido_rechazado(self):
        self.pago["referencia_externa"]="pay-1?other=1"
        with self.assertRaises(VerificacionRechazada): self.auditar()
        self.assertEqual(self.consultas,[])


if __name__=="__main__":
    unittest.main()
