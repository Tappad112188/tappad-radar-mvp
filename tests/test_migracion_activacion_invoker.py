import os
import unittest
from pathlib import Path
import psycopg

DSN = os.getenv("TAPPAD_TEST_POSTGRES_DSN")
SQL = Path(__file__).resolve().parents[1] / "docs/sql_migracion_activacion_invoker_PENDIENTE_VALIDACION.sql"

@unittest.skipUnless(DSN, "PostgreSQL aislado requerido")
class ActivacionInvoker(unittest.TestCase):
    def test_migracion_y_evidencia(self):
        with psycopg.connect(DSN) as c:
            self.assertEqual(c.execute("select current_database()").fetchone()[0], "tappad_ci_pruebas")
            for role in ("anon","authenticated","service_role","tappad_activador_privado"):
                c.execute("DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='"+role+"') THEN CREATE ROLE "+role+" NOLOGIN; END IF; END $$")
            c.execute("""CREATE SCHEMA tappad_internal;
            CREATE TABLE public.planes_tappad(id bigint primary key, activo boolean, periodicidad text, precio_mxn numeric);
            CREATE TABLE public.suscripciones_tappad(id bigint primary key, cliente_id bigint, plan_id bigint, proveedor_cobro text, referencia_externa text, estado text, fin_periodo timestamptz, actualizado_en timestamptz);
            CREATE TABLE public.pagos_tappad(id bigint primary key, suscripcion_id bigint, proveedor_cobro text, referencia_externa text, estado text, monto_mxn numeric, fecha_pago timestamptz);
            CREATE TABLE public.acceso_comercial_tappad(cliente_id bigint primary key, suscripcion_id bigint, estado text, origen text, habilitado_desde timestamptz, vigente_hasta timestamptz, ultima_verificacion timestamptz, actualizado_en timestamptz);
            CREATE TABLE public.activaciones_comerciales_tappad(id bigint generated always as identity primary key, cliente_id bigint, suscripcion_id bigint, pago_id bigint unique, periodo_inicio timestamptz, periodo_fin timestamptz, estado text, evidencia_proveedor jsonb);
            INSERT INTO public.planes_tappad VALUES (1,true,'mensual',100);
            INSERT INTO public.suscripciones_tappad VALUES (1,1,1,'mercadopago_produccion','sub','pendiente',null,null);
            INSERT INTO public.pagos_tappad VALUES (1,1,'mercadopago_produccion','pay','pagado',100,now()-interval '1 minute');""")
            for table in ("planes","suscripciones","pagos","acceso_comercial","activaciones_comerciales"):
                name=table+"_tappad"
                c.execute("ALTER TABLE public."+name+" ENABLE ROW LEVEL SECURITY")
                if table!="activaciones_comerciales":
                    c.execute("GRANT SELECT ON public."+name+" TO tappad_activador_privado")
                    c.execute("CREATE POLICY lectura ON public."+name+" FOR SELECT TO tappad_activador_privado USING (true)")
            c.execute(SQL.read_text(encoding="utf-8"))
            c.execute("SET LOCAL ROLE tappad_activador_privado")
            call="SELECT tappad_internal.tappad_aplicar_activacion_comercial(1,1,1,now()-interval '1 minute',now()-interval '1 minute'+interval '1 month',%s::jsonb)"
            import json
            evidence=dict(verificacion_remota="confirmada",entorno="produccion",seller_id="11",payment_id="pay",preapproval_id="sub")
            for key in evidence:
                invalid=dict(evidence)
                del invalid[key]
                self.assertFalse(c.execute(call,(json.dumps(invalid),)).fetchone()[0],key)
            self.assertTrue(c.execute(call,(json.dumps(evidence),)).fetchone()[0])
            self.assertFalse(c.execute(call,(json.dumps(evidence),)).fetchone()[0])
            self.assertEqual(c.execute("SELECT count(*) FROM public.activaciones_comerciales_tappad").fetchone()[0],1)
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                with c.transaction():
                    c.execute("UPDATE public.pagos_tappad SET id=id WHERE id=1")
            self.assertEqual(c.execute("SELECT estado FROM public.pagos_tappad WHERE id=1").fetchone()[0],"pagado")
            c.execute("RESET ROLE")
            for role in ("anon","authenticated","service_role"):
                self.assertFalse(c.execute("SELECT has_function_privilege(%s,'tappad_internal.tappad_aplicar_activacion_comercial(bigint,bigint,bigint,timestamptz,timestamptz,jsonb)','EXECUTE')",(role,)).fetchone()[0])
            c.rollback()
