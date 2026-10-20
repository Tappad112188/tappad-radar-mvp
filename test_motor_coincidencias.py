"""Pruebas sin red ni acceso a datos de proveedores reales."""
import unittest

from motor_coincidencias import (
    normalizar, palabras_proveedor, evaluar_licitacion, generar_coincidencias,
)


class MotorCoincidenciasTests(unittest.TestCase):
    def setUp(self):
        self.proveedor = {"id": 1, "activo": True, "palabras_clave": "Papelería, limpieza; mantenimiento"}
        self.coahuila = [{"estado": "Coahuila", "municipio": "Saltillo"}]

    def licitacion(self, estado="Coahuila de Zaragoza", nombre="Servicio de limpieza", ident=101):
        return {
            "id": ident, "nombre_procedimiento": nombre,
            "descripcion": "", "tipo_contratacion": "Servicios",
            "entidad_federativa": estado,
        }

    def test_normalizacion_acentos_y_mayusculas(self):
        self.assertEqual(normalizar("  PAPELERÍA  "), "papeleria")
        self.assertEqual(palabras_proveedor("Limpieza, limpieza; PAPELERÍA"), ["limpieza", "papeleria"])

    def test_dentro_de_cobertura(self):
        r = evaluar_licitacion(self.proveedor, self.licitacion(), self.coahuila)
        self.assertTrue(r["coincide"])
        self.assertEqual(r["categoria"], "dentro_de_cobertura")
        self.assertEqual(r["terminos"], ["limpieza"])

    def test_fuera_de_cobertura_solo_exploracion(self):
        lic = self.licitacion("Nuevo León")
        r = evaluar_licitacion(self.proveedor, lic, self.coahuila)
        self.assertTrue(r["coincidencia_tematica"])
        self.assertFalse(r["coincide"])
        self.assertEqual(r["categoria"], "fuera_de_cobertura")
        self.assertEqual(generar_coincidencias([self.proveedor], [lic], {1: self.coahuila}), [])
        self.assertEqual(len(generar_coincidencias(
            [self.proveedor], [lic], {1: self.coahuila}, incluir_fuera_de_cobertura=True
        )), 1)

    def test_cobertura_no_definida(self):
        r = evaluar_licitacion(self.proveedor, self.licitacion(None), self.coahuila)
        self.assertEqual(r["categoria"], "cobertura_sin_definir")
        self.assertTrue(r["coincide"])

    def test_sin_coincidencia_tematica(self):
        r = evaluar_licitacion(self.proveedor, self.licitacion(nombre="Compra de vehículos"), self.coahuila)
        self.assertFalse(r["coincide"])
        self.assertFalse(r["coincidencia_tematica"])

    def test_no_coincidencia_por_subcadena(self):
        r = evaluar_licitacion(
            {"id": 1, "palabras_clave": "oficina"},
            self.licitacion(nombre="Equipamiento de oficinistas"), self.coahuila
        )
        self.assertFalse(r["coincidencia_tematica"])

    def test_excluir_inactivos(self):
        p = {**self.proveedor, "activo": False}
        self.assertEqual(generar_coincidencias([p], [self.licitacion()], {1: self.coahuila}), [])


if __name__ == "__main__":
    unittest.main()
