"""Pruebas sin red ni Supabase del mapeo ComprasMX."""
import unittest
from tappad_importador_automatico import registro, fecha

class TestImportacionComprasMX(unittest.TestCase):
    def test_cuatro_fechas_oficiales(self):
        fila={
            "Dirección del anuncio":"https://comprasmx.buengobierno.gob.mx/detalle/0123456789abcdef0123456789abcdef/procedimiento",
            "Número de procedimiento/proyecto":"PRUEBA-2026",
            "Fecha publicación":"2026-10-28 08:00:00",
            "Fecha y hora junta de aclaraciones":"2026-10-30 11:00:00",
            "Fecha apertura":"2026-11-06 12:00:00",
            "Fecha de fallo":"2026-11-11 12:00:00",
        }
        item=registro(fila)
        self.assertIsNotNone(item)
        self.assertEqual(item["fecha_publicacion"],fila["Fecha publicación"])
        self.assertEqual(item["fecha_junta_aclaraciones"],fila["Fecha y hora junta de aclaraciones"])
        self.assertEqual(item["fecha_apertura"],fila["Fecha apertura"])
        self.assertEqual(item["fecha_fallo_programado"],fila["Fecha de fallo"])
        self.assertEqual(item["fecha_fallo"],fila["Fecha de fallo"])
        for campo in ("fecha_publicacion","fecha_junta_aclaraciones","fecha_apertura","fecha_fallo_programado"):
            self.assertIsNotNone(fecha(item[campo]))

    def test_campos_opcionales(self):
        fila={"Dirección del anuncio":"https://ejemplo.mx/detalle/0123456789abcdef0123456789abcdef/procedimiento"}
        item=registro(fila)
        self.assertIsNone(item["fecha_junta_aclaraciones"])
        self.assertIsNone(item["fecha_fallo_programado"])

if __name__=="__main__":
    unittest.main(verbosity=2)
