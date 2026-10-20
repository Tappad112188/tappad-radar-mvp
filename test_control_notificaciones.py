import unittest
from control_notificaciones import separar_notificaciones

class TestControlNotificaciones(unittest.TestCase):
    def test_nuevas(self):
        self.assertEqual(len(separar_notificaciones([{"cliente_id":1,"licitacion_id":2}],[])["nuevas"]),1)

    def test_enviado(self):
        c=[{"cliente_id":1,"licitacion_id":2}]
        h=[{"cliente_id":1,"licitacion_id":2,"estado":"enviado"}]
        self.assertEqual(len(separar_notificaciones(c,h)["retenidas"]),1)

    def test_error(self):
        c=[{"cliente_id":1,"licitacion_id":2}]
        h=[{"cliente_id":1,"licitacion_id":2,"estado":"error"}]
        self.assertEqual(len(separar_notificaciones(c,h)["reintentos"]),1)

    def test_dos_proveedores(self):
        c=[{"cliente_id":1,"licitacion_id":2},{"cliente_id":3,"licitacion_id":2}]
        h=[{"cliente_id":1,"licitacion_id":2,"estado":"enviado"}]
        self.assertEqual(len(separar_notificaciones(c,h)["nuevas"]),1)

    def test_entrada_duplicada(self):
        c={"cliente_id":1,"licitacion_id":2}
        self.assertEqual(len(separar_notificaciones([c,c],[])["nuevas"]),1)

if __name__ == "__main__":
    unittest.main()
