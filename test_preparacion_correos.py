"""Pruebas integrales sin servicios externos ni envíos."""
import unittest
from datetime import datetime
from zoneinfo import ZoneInfo
from preparador_alertas import preparar_alertas, vista_previa_correo

AHORA = datetime(2026, 10, 21, 10, 0, tzinfo=ZoneInfo("America/Monterrey"))

def licitacion(id, fecha="2026-10-23T11:00:00", estado="Coahuila", estatus="vigente"):
    return {
        "id": id, "numero_procedimiento": f"IA-{id}",
        "nombre_procedimiento": "Servicio de mantenimiento",
        "descripcion": "Mantenimiento preventivo",
        "tipo_contratacion": "servicios",
        "entidad_federativa": estado,
        "fecha_apertura": fecha,
        "estatus": estatus,
        "url_procedimiento": f"https://comprasmx.buengobierno.gob.mx/{id}",
    }

PROVEEDORES = [
    {"id": 1, "empresa": "Empresa A", "palabras_clave": "mantenimiento", "activo": True},
    {"id": 2, "empresa": "Empresa B", "palabras_clave": "mantenimiento", "activo": True},
]
COBERTURAS = {1: [{"estado": "Coahuila"}], 2: [{"estado": "Coahuila"}]}

def simular(licitaciones, historial=None, proveedores=None, coberturas=None):
    return preparar_alertas(
        proveedores if proveedores is not None else PROVEEDORES,
        licitaciones, coberturas if coberturas is not None else COBERTURAS,
        historial or [], ahora=AHORA
    )

class TestPreparacionCorreos(unittest.TestCase):
    def test_un_correo_por_proveedor_con_dos_oportunidades(self):
        r = simular([licitacion(101), licitacion(102)])
        self.assertEqual(r["resumen"]["correos_simulados"], 2)
        self.assertEqual(len(r["por_proveedor"][1]), 2)
        self.assertEqual(len(r["por_proveedor"][2]), 2)
    def test_solo_oportunidades_propias(self):
        r = simular([licitacion(101)], proveedores=[
            PROVEEDORES[0],
            {"id": 2, "empresa": "B", "palabras_clave": "limpieza", "activo": True},
        ])
        self.assertEqual(set(r["por_proveedor"]), {1})
    def test_no_duplicados_enviados_o_pendientes(self):
        r = simular([licitacion(101)], [
            {"cliente_id": 1, "licitacion_id": 101, "estado": "enviado"},
            {"cliente_id": 2, "licitacion_id": 101, "estado": "pendiente"},
        ])
        self.assertEqual(r["resumen"]["nuevas"], 0)
        self.assertEqual(r["resumen"]["duplicadas"], 2)
    def test_vencidas_excluidas(self):
        r = simular([licitacion(101, fecha="2026-10-20T11:00:00")])
        self.assertEqual(r["resumen"]["correos_simulados"], 0)
    def test_canceladas_excluidas(self):
        r = simular([licitacion(101, estatus="cancelado")])
        self.assertEqual(r["resumen"]["correos_simulados"], 0)
    def test_fuera_de_cobertura(self):
        r = simular([licitacion(101, estado="Nuevo León")])
        self.assertEqual(r["resumen"]["nuevas"], 0)
    def test_cobertura_sin_definir_no_notifica(self):
        r = simular([licitacion(101)], coberturas={1: [], 2: []})
        self.assertEqual(r["resumen"]["nuevas"], 0)
    def test_error_solo_reintento(self):
        r = simular([licitacion(101)], [
            {"cliente_id": 1, "licitacion_id": 101, "estado": "error"},
        ])
        self.assertEqual(r["resumen"]["reintentos"], 1)
        self.assertEqual(r["resumen"]["nuevas"], 1)
    def test_correo_agrupado(self):
        r = simular([licitacion(101), licitacion(102)])
        correo = vista_previa_correo("Empresa A", r["por_proveedor"][1])
        self.assertIn("IA-101", correo["cuerpo"])
        self.assertIn("IA-102", correo["cuerpo"])

if __name__ == "__main__":
    unittest.main()
