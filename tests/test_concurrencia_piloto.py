import os, unittest, json, threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import psycopg

DSN=os.getenv("TAPPAD_TEST_POSTGRES_DSN")
ROOT=Path(__file__).resolve().parents[1]/"docs"

@unittest.skipUnless(DSN,"PostgreSQL aislado requerido")
class ConcurrenciaPiloto(unittest.TestCase):
    def test_registro_y_activacion_simultaneos(self):
        with psycopg.connect(DSN) as c:
            self.assertEqual(c.execute("select current_database()").fetchone()[0],"tappad_ci_pruebas")
            for role in ("anon","authenticated","service_role","tappad_activador_privado","tappad_login_activacion"):
                c.execute("DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='"+role+"') THEN CREATE ROLE "+role+" NOLOGIN; END IF; END $$")
            c.execute("GRANT tappad_activador_privado TO tappad_login_activacion")
            c.execute("""CREATE SCHEMA tappad_internal;
            CREATE TABLE public.planes_tappad(id bigint primary key, activo boolean, periodicidad text, precio_mxn numeric);
            CREATE TABLE public.suscripciones_tappad(id bigint primary key, cliente_id bigint, plan_id bigint, proveedor_cobro text, referencia_externa text, estado text, fin_periodo timestamptz, actualizado_en timestamptz);
            CREATE TABLE public.pagos_tappad(id bigint generated always as identity primary key, suscripcion_id bigint, proveedor_cobro text, referencia_externa text, estado text, monto_mxn numeric, fecha_pago timestamptz, unique(proveedor_cobro,referencia_externa));
            CREATE TABLE public.acceso_comercial_tappad(cliente_id bigint primary key, suscripcion_id bigint, estado text, origen text, habilitado_desde timestamptz, vigente_hasta timestamptz, ultima_verificacion timestamptz, actualizado_en timestamptz);
            CREATE TABLE public.activaciones_comerciales_tappad(id bigint generated always as identity primary key, cliente_id bigint, suscripcion_id bigint, pago_id bigint unique, periodo_inicio timestamptz, periodo_fin timestamptz, estado text, evidencia_proveedor jsonb);
            INSERT INTO public.planes_tappad VALUES(1,false,'mensual',449);
            INSERT INTO public.suscripciones_tappad VALUES(5,4,1,'mercadopago_produccion','dbc554730f1141a48cf73881a4e9eb96','pendiente',null,null);""")
            for table in ("planes","suscripciones","pagos","acceso_comercial","activaciones_comerciales"):
                name=table+"_tappad"
                c.execute("ALTER TABLE public."+name+" ENABLE ROW LEVEL SECURITY")
                if table!="activaciones_comerciales":
                    c.execute("GRANT SELECT ON public."+name+" TO tappad_activador_privado")
                    c.execute("CREATE POLICY lectura ON public."+name+" FOR SELECT TO tappad_activador_privado USING (true)")
            c.execute((ROOT/"sql_migracion_activacion_invoker_PENDIENTE_VALIDACION.sql").read_text())
            c.execute((ROOT/"sql_activacion_exclusiva_piloto.sql").read_text())
            c.commit()
            c.execute((ROOT/"sql_registro_pago_piloto.sql").read_text())
            fecha,fin=c.execute("SELECT now()-interval '1 minute',now()-interval '1 minute'+interval '1 month'").fetchone()
        def carrera(fn):
            barrier=threading.Barrier(2)
            def worker():
                with psycopg.connect(DSN) as c:
                    c.execute("SET SESSION AUTHORIZATION tappad_login_activacion")
                    c.execute("SET LOCAL ROLE tappad_activador_privado")
                    c.execute("SET LOCAL statement_timeout='10s'")
                    barrier.wait(timeout=10)
                    return fn(c)
            with ThreadPoolExecutor(max_workers=2) as pool:
                fs=[pool.submit(worker) for _ in range(2)]
                return [f.result(timeout=20) for f in fs]
        ids=carrera(lambda c:c.execute("SELECT tappad_internal.registrar_pago_piloto(%s,%s)",("123456789",fecha)).fetchone()[0])
        self.assertEqual(ids[0],ids[1])
        ev=json.dumps(dict(verificacion_remota="confirmada",entorno="produccion",seller_id="11",payment_id="123456789",preapproval_id="dbc554730f1141a48cf73881a4e9eb96"))
        results=carrera(lambda c:c.execute("SELECT tappad_internal.tappad_aplicar_activacion_comercial(4,5,%s,%s,%s,%s::jsonb)",(ids[0],fecha,fin,ev)).fetchone()[0])
        self.assertEqual(sorted(results),[False,True])
        with psycopg.connect(DSN) as c:
            self.assertEqual(c.execute("SELECT count(*) FROM public.pagos_tappad").fetchone()[0],1)
            self.assertEqual(c.execute("SELECT count(*) FROM public.activaciones_comerciales_tappad").fetchone()[0],1)
            self.assertEqual(c.execute("SELECT estado,vigente_hasta FROM public.acceso_comercial_tappad WHERE cliente_id=4").fetchone(),("habilitado",fin))
