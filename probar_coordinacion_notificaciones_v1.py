"""Pruebas unitarias del protocolo de notificaciones; sin red ni credenciales.
Comprueba reserva completa, duplicados, aceptacion SMTP, entrega incierta.
"""
import unittest

def decidir(reservadas,solicitadas,resultado_smtp):
    if len(reservadas)!=len(solicitadas) or set(reservadas)!=set(solicitadas):
        return "NO_ENVIAR_REVISAR_RESERVAS"
    if resultado_smtp=="aceptado":
        return "REGISTRAR_ENVIADO"
    if resultado_smtp=="error":
        return "ENTREGA_INCIERTA_NO_REINTENTAR"
    return "NO_ENVIAR"

class CoordinacionTest(unittest.TestCase):
    def test_reserva_completa(self):
        self.assertEqual(decidir([101,102],[101,102],"aceptado"),"REGISTRAR_ENVIADO")
    def test_reserva_parcial(self):
        self.assertEqual(decidir([101],[101,102],"aceptado"),"NO_ENVIAR_REVISAR_RESERVAS")
    def test_duplicado(self):
        self.assertEqual(decidir([], [101],"aceptado"),"NO_ENVIAR_REVISAR_RESERVAS")
    def test_smtp_incierto(self):
        self.assertEqual(decidir([101],[101],"error"),"ENTREGA_INCIERTA_NO_REINTENTAR")
    def test_no_activar(self):
        self.assertEqual(decidir([101],[101],None),"NO_ENVIAR")

if __name__=="__main__": unittest.main(verbosity=2)
