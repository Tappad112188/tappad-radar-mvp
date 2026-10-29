"""Pruebas de regresion del clasificador comercial TAPPAD."""
import unittest
from diagnosticar_vigencia_v4 import RUBROS, contiene, norm, objeto_principal

class ClasificacionComercial(unittest.TestCase):
    def test_equipo_medico_no_es_informatica(self):
        lic = {"nombre_procedimiento": "INSTALACION, REPARACION Y MANTENIMIENTO DE EQUIPO E INSTRUMENTAL MEDICO Y DE LAB", "descripcion": "EQUIPO E INSTRUMENTAL MEDICO Y DE LABORATORIO"}
        texto = norm(lic["nombre_procedimiento"] + " " + lic["descripcion"])
        self.assertEqual(objeto_principal(lic), 7)
        self.assertFalse(any(contiene(texto, x) for x in RUBROS[3]))
        self.assertTrue(any(contiene(texto, x) for x in RUBROS[7]))

    def test_computo_sigue_identificado(self):
        texto = norm("ADQUISICION DE COMPUTADORAS Y SERVIDORES PARA CENTRO DE COMPUTO")
        self.assertTrue(any(contiene(texto, x) for x in RUBROS[3]))

    def test_obra_sigue_identificada(self):
        self.assertEqual(objeto_principal({"nombre_procedimiento": "CONSTRUCCION DE LINEA DE DRENAJE SANITARIO"}), 13)

    def test_laboratorio_solo_no_es_informatica(self):
        texto = norm("MANTENIMIENTO DE INSTRUMENTAL DE LABORATORIO")
        self.assertFalse(any(contiene(texto, x) for x in RUBROS[3]))

if __name__ == "__main__":
    unittest.main(verbosity=2)
