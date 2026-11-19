"""Integracion REAL PostgreSQL del worker privado; datos ficticios y rollback.

Ejecutar solo contra una BD desechable: TAPPAD_TEST_POSTGRES_DSN.
No conecta con Mercado Pago ni Supabase.
"""
import os
import unittest
from pathlib import Path
from unittest.mock import patch
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor

try:
    import psycopg
except ImportError:
    psycopg = None

from conciliar_reversion_privada_postgres import conciliar_reversion_privada
from verificar_pago_mercadopago_servidor import VerificacionRechazada

DSN = os.getenv("TAPPAD_TEST_POSTGRES_DSN")
SQL = Path(__file__).resolve().parents[1] / "docs/sql_conciliacion_reversion_mercadopago_borrador.sql"


@unittest.skipUnless(DSN and psycopg, "Se requiere PostgreSQL desechable y psycopg")
class IntegracionWorkerPostgres(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Exigir nombre de BD de pruebas: nunca ejecutar en produccion.
        with psycopg.connect(DSN) as conn:
            dbname = conn.execute("SELECT current_database()").fetchone()[0]
            if dbname not in ("tappad_radar_pruebas", "tappad_ci_pruebas"):
                raise RuntimeError("Base no autorizada para pruebas: " + dbname)
            for role in ("anon", "authenticated"):
                conn.execute("DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '" + role + "') THEN CREATE ROLE " + role + " NOLOGIN; END IF; END $$")
            conn.execute("""CREATE TABLE IF NOT EXISTS public.suscripciones_tappad
              (id bigint PRIMARY KEY, cliente_id bigint NOT NULL, proveedor_cobro text NOT NULL,
               referencia_externa text NOT NULL, estado text DEFAULT 'activa')""")
            conn.execute("""CREATE TABLE IF NOT EXISTS public.pagos_tappad
              (id bigint PRIMARY KEY, suscripcion_id bigint NOT NULL REFERENCES public.suscripciones_tappad(id),
               proveedor_cobro text NOT NULL, referencia_externa text NOT NULL, estado text NOT NULL)""")
            conn.execute("""CREATE TABLE IF NOT EXISTS public.acceso_comercial_tappad
              (cliente_id bigint PRIMARY KEY, suscripcion_id bigint NOT NULL,
               estado text NOT NULL, vigente_hasta timestamptz, actualizado_en timestamptz)""")
            conn.execute("""CREATE TABLE IF NOT EXISTS public.activaciones_comerciales_tappad
              (id bigint PRIMARY KEY, cliente_id bigint NOT NULL, suscripcion_id bigint NOT NULL,
               pago_id bigint NOT NULL, estado text NOT NULL, periodo_inicio timestamptz,
               periodo_fin timestamptz)""")
            conn.execute(SQL.read_text(encoding="utf-8"))
            # Fixture fija, separada de cualquier dato productivo.
            conn.execute("DELETE FROM tappad_internal.auditoria_estados_mercadopago")
            conn.execute("DELETE FROM public.activaciones_comerciales_tappad")
            conn.execute("DELETE FROM public.acceso_comercial_tappad")
            conn.execute("DELETE FROM public.pagos_tappad")
            conn.execute("DELETE FROM public.suscripciones_tappad")
            conn.execute("""INSERT INTO public.suscripciones_tappad (id,cliente_id,proveedor_cobro,referencia_externa) VALUES
              (7,4,'mercadopago_produccion','sub-1'),
              (8,5,'mercadopago_produccion','sub-2'),
              (9,6,'mercadopago_produccion','sub-3')""")
            conn.execute("""INSERT INTO public.pagos_tappad VALUES
              (9,7,'mercadopago_produccion','pay-1','pagado'),
              (10,8,'mercadopago_produccion','pay-2','pagado'),
              (11,9,'mercadopago_produccion','pay-3','pagado')""")
            now = datetime.now(timezone.utc)
            conn.execute("""INSERT INTO public.acceso_comercial_tappad VALUES
              (4,7,'habilitado',%s,now()),(5,8,'habilitado',%s,now()),
              (6,9,'habilitado',%s,now())""", (now+timedelta(days=15),)*3)
            conn.execute("""INSERT INTO public.activaciones_comerciales_tappad VALUES
              (1,4,7,9,'aplicada',%s,%s),
              (2,5,8,10,'aplicada',%s,%s),
              (3,6,9,11,'aplicada',%s,%s)""",
              (now-timedelta(days=15),now+timedelta(days=15))*3)

    def auditar(self, sub, pay, *, token, seller_id_esperado):
        return {"decision":"revision_revocacion_pago",
                "estado_pago_remoto":"refunded" if pay["id"] != 10 else "charged_back",
                "evidencia":{"origen":"consulta_directa_mercadopago",
                             "seller_id":str(seller_id_esperado),
                             "payment_id":pay["referencia_externa"],
                             "preapproval_id":sub["referencia_externa"]}}

    def ejecutar(self, pago, auditar=None):
        return conciliar_reversion_privada(pago, postgres_dsn=DSN,
             token="SIMULADO_SIN_RED", seller_id="11", permitir=True,
             auditar=auditar or self.auditar)

    def test_01_reembolso_y_suspension(self):
        with patch.dict(os.environ, {"TAPPAD_HABILITAR_REVERSION_PRODUCCION":"SI"}):
            self.assertEqual(self.ejecutar(9)["estado"], "aplicada")
        with psycopg.connect(DSN) as conn:
            self.assertEqual(conn.execute("SELECT estado FROM public.pagos_tappad WHERE id=9").fetchone()[0],"reembolsado")
            self.assertEqual(conn.execute("SELECT estado FROM public.acceso_comercial_tappad WHERE cliente_id=4").fetchone()[0],"suspendido")
            self.assertEqual(conn.execute("SELECT count(*) FROM tappad_internal.auditoria_estados_mercadopago WHERE pago_id=9").fetchone()[0],1)

    def test_02_idempotencia(self):
        with patch.dict(os.environ, {"TAPPAD_HABILITAR_REVERSION_PRODUCCION":"SI"}):
            self.assertEqual(self.ejecutar(9)["estado"], "ya_conciliada")
        with psycopg.connect(DSN) as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM tappad_internal.auditoria_estados_mercadopago WHERE pago_id=9").fetchone()[0],1)

    def test_03_contracargo(self):
        with patch.dict(os.environ, {"TAPPAD_HABILITAR_REVERSION_PRODUCCION":"SI"}):
            self.assertEqual(self.ejecutar(10)["estado"], "aplicada")
        with psycopg.connect(DSN) as conn:
            self.assertEqual(conn.execute("SELECT estado FROM public.pagos_tappad WHERE id=10").fetchone()[0],"contracargo")

    def test_04_sin_reversion_no_escribe(self):
        def aprobado(*args, **kwargs):
            return {"decision":"pago_aprobado_sujeto_a_conciliacion"}
        with patch.dict(os.environ, {"TAPPAD_HABILITAR_REVERSION_PRODUCCION":"SI"}):
            self.assertEqual(self.ejecutar(11, aprobado)["escrituras"],0)
        with psycopg.connect(DSN) as conn:
            self.assertEqual(conn.execute("SELECT estado FROM public.pagos_tappad WHERE id=11").fetchone()[0],"pagado")

    def test_05_evidencia_falsa_revierte(self):
        def falsa(*args, **kwargs):
            return {"decision":"revision_revocacion_pago","estado_pago_remoto":"refunded",
                    "evidencia":{"seller_id":"999","payment_id":"pay-3","preapproval_id":"sub-3"}}
        with patch.dict(os.environ, {"TAPPAD_HABILITAR_REVERSION_PRODUCCION":"SI"}):
            with self.assertRaises(VerificacionRechazada):
                self.ejecutar(11, falsa)
        with psycopg.connect(DSN) as conn:
            self.assertEqual(conn.execute("SELECT estado FROM public.pagos_tappad WHERE id=11").fetchone()[0],"pagado")


    def test_06_roles_publicos_sin_permiso_ejecucion(self):
        firma = "tappad_internal.conciliar_reversion_pago(bigint,bigint,text,jsonb)"
        with psycopg.connect(DSN) as conn:
            for rol in ("anon", "authenticated"):
                tiene = conn.execute(
                    "SELECT has_function_privilege(%s,%s,'EXECUTE')",
                    (rol, firma)).fetchone()[0]
                self.assertFalse(tiene, f"Permiso indebido: {rol}")
                esquema = conn.execute(
                    "SELECT has_schema_privilege(%s,'tappad_internal','USAGE')",
                    (rol,)).fetchone()[0]
                self.assertFalse(esquema, f"Esquema privado accesible: {rol}")

    def test_07_funcion_rechaza_estado_nulo_sin_escribir(self):
        with psycopg.connect(DSN) as conn:
            with self.assertRaises(psycopg.Error):
                conn.execute(
                    """SELECT tappad_internal.conciliar_reversion_pago(
                       11,9,NULL,%s::jsonb)""",
                    ('{"origen":"consulta_directa_mercadopago","payment_id":"pay-3","preapproval_id":"sub-3","seller_id":"11"}',))
            conn.rollback()
            self.assertEqual(conn.execute(
                "SELECT estado FROM public.pagos_tappad WHERE id=11").fetchone()[0],
                "pagado")


    def test_08_rol_privado_minimo_sin_privilegios_admin(self):
        """Rol NOLOGIN sin superusuario, BYPASSRLS, CREATE ni grants publicos."""
        firma = "tappad_internal.conciliar_reversion_pago(bigint,bigint,text,jsonb)"
        with psycopg.connect(DSN) as conn:
            conn.execute("""DO $worker_role$ BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='tappad_worker_ci')
                THEN CREATE ROLE tappad_worker_ci NOLOGIN NOSUPERUSER NOCREATEDB
                    NOCREATEROLE NOREPLICATION NOBYPASSRLS;
                END IF;
            END $worker_role$""")
            # El rol se crea solamente en la base efimera de CI.
            conn.execute("GRANT USAGE ON SCHEMA tappad_internal TO tappad_worker_ci")
            for tabla in ("suscripciones_tappad", "pagos_tappad",
                          "acceso_comercial_tappad", "activaciones_comerciales_tappad"):
                conn.execute("GRANT SELECT ON TABLE public." + tabla + " TO tappad_worker_ci")
            conn.execute("GRANT UPDATE (estado) ON public.suscripciones_tappad TO tappad_worker_ci")
            conn.execute("GRANT UPDATE (estado) ON public.pagos_tappad TO tappad_worker_ci")
            conn.execute("GRANT UPDATE (estado, actualizado_en) ON public.acceso_comercial_tappad TO tappad_worker_ci")
            conn.execute("GRANT INSERT ON tappad_internal.auditoria_estados_mercadopago TO tappad_worker_ci")
            conn.execute("GRANT USAGE ON SEQUENCE tappad_internal.auditoria_estados_mercadopago_id_seq TO tappad_worker_ci")
            conn.execute("GRANT EXECUTE ON FUNCTION " + firma + " TO tappad_worker_ci")
            props = conn.execute("""SELECT rolsuper, rolcreatedb, rolcreaterole,
                                     rolbypassrls, rolcanlogin
                                     FROM pg_roles WHERE rolname='tappad_worker_ci'""").fetchone()
            self.assertEqual(props, (False, False, False, False, False))
            self.assertFalse(conn.execute(
                "SELECT has_schema_privilege('tappad_worker_ci','public','CREATE')").fetchone()[0])
            self.assertFalse(conn.execute(
                "SELECT has_table_privilege('tappad_worker_ci','public.pagos_tappad','INSERT')").fetchone()[0])
            self.assertFalse(conn.execute(
                "SELECT has_column_privilege('tappad_worker_ci','public.suscripciones_tappad','referencia_externa','UPDATE')").fetchone()[0])
            conn.execute("SET LOCAL ROLE tappad_worker_ci")
            self.assertEqual(conn.execute("SELECT current_user").fetchone()[0], "tappad_worker_ci")
            result = conn.execute(
                """SELECT tappad_internal.conciliar_reversion_pago(
                   11,9,'refunded',%s::jsonb)""",
                ('{"origen":"consulta_directa_mercadopago","payment_id":"pay-3","preapproval_id":"sub-3","seller_id":"11"}',)).fetchone()[0]
            self.assertTrue(result)
            conn.execute("RESET ROLE")
            self.assertEqual(conn.execute(
                "SELECT estado FROM public.pagos_tappad WHERE id=11").fetchone()[0], "reembolsado")
            conn.rollback()
        with psycopg.connect(DSN) as check:
            self.assertEqual(check.execute(
                "SELECT estado FROM public.pagos_tappad WHERE id=11").fetchone()[0], "pagado")


    def test_09_concurrencia_dos_workers_un_solo_pago(self):
        """Dos conexiones simultaneas no generan doble auditoria."""
        with patch.dict(os.environ, {"TAPPAD_HABILITAR_REVERSION_PRODUCCION":"SI"}):
            with ThreadPoolExecutor(max_workers=2) as pool:
                resultados = list(pool.map(self.ejecutar, (11, 11)))
        self.assertEqual(sorted(x["estado"] for x in resultados),
                         ["aplicada", "ya_conciliada"])
        with psycopg.connect(DSN) as conn:
            self.assertEqual(conn.execute(
                "SELECT count(*) FROM tappad_internal.auditoria_estados_mercadopago WHERE pago_id=11"
            ).fetchone()[0], 1)


    def test_10_concurrencia_activacion_y_reversion_sin_deadlock(self):
        """Activacion y reversion compiten por locks en orden suscripcion -> acceso -> pago."""
        from threading import Barrier
        barrier = Barrier(2)
        def activacion_simulada():
            with psycopg.connect(DSN, options="-c lock_timeout=3000 -c statement_timeout=6000") as conn:
                barrier.wait(timeout=5)
                with conn.cursor() as cur:
                    cur.execute("SELECT id FROM public.suscripciones_tappad WHERE id=9 FOR UPDATE")
                    cur.execute("SELECT cliente_id FROM public.acceso_comercial_tappad WHERE cliente_id=6 FOR UPDATE")
                    cur.execute("SELECT id FROM public.pagos_tappad WHERE id=11 FOR UPDATE")
                    cur.execute("SELECT estado FROM public.pagos_tappad WHERE id=11")
                    return cur.fetchone()[0]
        def reversion_simulada():
            with psycopg.connect(DSN, options="-c lock_timeout=3000 -c statement_timeout=6000") as conn:
                barrier.wait(timeout=5)
                with conn.cursor() as cur:
                    cur.execute("SELECT id FROM public.suscripciones_tappad WHERE id=9 FOR UPDATE")
                    cur.execute("SELECT cliente_id FROM public.acceso_comercial_tappad WHERE cliente_id=6 FOR UPDATE")
                    cur.execute("SELECT id FROM public.pagos_tappad WHERE id=11 FOR UPDATE")
                    cur.execute("SELECT estado FROM public.pagos_tappad WHERE id=11")
                    return cur.fetchone()[0]
        with psycopg.connect(DSN) as baseline_conn:
            estado_inicial = baseline_conn.execute("SELECT estado FROM public.pagos_tappad WHERE id=11").fetchone()[0]
        with ThreadPoolExecutor(max_workers=2) as pool:
            a = pool.submit(activacion_simulada)
            b = pool.submit(reversion_simulada)
            self.assertEqual(a.result(timeout=8), estado_inicial)
            self.assertEqual(b.result(timeout=8), estado_inicial)
        with psycopg.connect(DSN) as conn:
            self.assertEqual(conn.execute("SELECT estado FROM public.pagos_tappad WHERE id=11").fetchone()[0], estado_inicial)

    def test_11_rol_publico_no_puede_escribir_tablas_de_reversion(self):
        with psycopg.connect(DSN) as conn:
            for rol in ("anon", "authenticated"):
                self.assertFalse(conn.execute(
                    "SELECT has_table_privilege(%s,'tappad_internal.auditoria_estados_mercadopago','INSERT')",
                    (rol,)).fetchone()[0])
                self.assertFalse(conn.execute(
                    "SELECT has_table_privilege(%s,'tappad_internal.auditoria_estados_mercadopago','SELECT')",
                    (rol,)).fetchone()[0])


    def test_12_reversion_rechaza_suscripcion_ajena_y_no_escribe(self):
        """No debe permitirse revertir un pago vinculado a otra suscripcion."""
        with psycopg.connect(DSN) as conn:
            before = conn.execute(
                "SELECT estado FROM public.pagos_tappad WHERE id=10"
            ).fetchone()[0]
            count_before = conn.execute(
                "SELECT count(*) FROM tappad_internal.auditoria_estados_mercadopago WHERE pago_id=10"
            ).fetchone()[0]
            with self.assertRaises(psycopg.Error):
                conn.execute(
                    """SELECT tappad_internal.conciliar_reversion_pago(
                       10,7,'refunded',%s::jsonb)""",
                    ('{"origen":"consulta_directa_mercadopago","payment_id":"pay-2","preapproval_id":"sub-1","seller_id":"11"}',))
            conn.rollback()
            self.assertEqual(conn.execute(
                "SELECT estado FROM public.pagos_tappad WHERE id=10"
            ).fetchone()[0], before)
            self.assertEqual(conn.execute(
                "SELECT count(*) FROM tappad_internal.auditoria_estados_mercadopago WHERE pago_id=10"
            ).fetchone()[0], count_before)

    def test_13_reversion_conflictiva_no_sobrescribe_contracargo(self):
        """Un pago ya marcado contracargo no puede mutar a reembolsado."""
        with psycopg.connect(DSN) as conn:
            self.assertEqual(conn.execute(
                "SELECT estado FROM public.pagos_tappad WHERE id=10"
            ).fetchone()[0], "contracargo")
            with self.assertRaises(psycopg.Error):
                conn.execute(
                    """SELECT tappad_internal.conciliar_reversion_pago(
                       10,8,'refunded',%s::jsonb)""",
                    ('{"origen":"consulta_directa_mercadopago","payment_id":"pay-2","preapproval_id":"sub-2","seller_id":"11"}',))
            conn.rollback()
            self.assertEqual(conn.execute(
                "SELECT estado FROM public.pagos_tappad WHERE id=10"
            ).fetchone()[0], "contracargo")



    def test_14_migracion_reversion_en_postgres_efimero(self):
        """Ejecuta DDL de preparacion en transaccion desechable; comprueba RLS y rol."""
        preparation = (Path(__file__).resolve().parents[1] /
                       "docs/sql_preparacion_reversion_privada_NO_APLICAR.sql").read_text(encoding="utf-8")
        with psycopg.connect(DSN) as conn:
            self.assertEqual(conn.execute("SELECT current_database()").fetchone()[0],
                             "tappad_ci_pruebas")
            # Simular constraint anterior documentado. No tocar produccion.
            conn.execute("""ALTER TABLE public.pagos_tappad
                ADD CONSTRAINT pagos_tappad_estado_check
                CHECK (estado IN ('pendiente','pagado','fallido','reembolsado','cancelado'))""")
            conn.execute("ALTER TABLE public.suscripciones_tappad ENABLE ROW LEVEL SECURITY")
            conn.execute("ALTER TABLE public.pagos_tappad ENABLE ROW LEVEL SECURITY")
            conn.execute("ALTER TABLE public.acceso_comercial_tappad ENABLE ROW LEVEL SECURITY")
            conn.execute("ALTER TABLE public.activaciones_comerciales_tappad ENABLE ROW LEVEL SECURITY")
            # psycopg admite BEGIN/COMMIT dentro del script; DDL solo en BD efimera.
            conn.commit()
            try:
                conn.execute(preparation)
                allowed = conn.execute("""SELECT pg_get_constraintdef(oid)
                    FROM pg_constraint WHERE conname='pagos_tappad_estado_check'
                      AND conrelid='public.pagos_tappad'::regclass""").fetchone()[0]
                self.assertIn("contracargo", allowed)
                self.assertEqual(conn.execute("""SELECT rolcanlogin,rolbypassrls
                    FROM pg_roles WHERE rolname='tappad_reversion_privada'""").fetchone(),
                    (False, False))
                self.assertTrue(conn.execute("""SELECT relrowsecurity FROM pg_class
                    WHERE oid='tappad_internal.auditoria_estados_mercadopago'::regclass""").fetchone()[0])
                self.assertFalse(conn.execute("""SELECT has_function_privilege(
                    'anon','tappad_internal.conciliar_reversion_pago(bigint,bigint,text,jsonb)','EXECUTE')""").fetchone()[0])
                self.assertTrue(conn.execute("""SELECT has_function_privilege(
                    'tappad_reversion_privada',
                    'tappad_internal.conciliar_reversion_pago(bigint,bigint,text,jsonb)','EXECUTE')""").fetchone()[0])
            finally:
                # Solo base desechable, reiniciada en cada ejecucion de Actions.
                conn.rollback()


if __name__ == "__main__":
    unittest.main()
