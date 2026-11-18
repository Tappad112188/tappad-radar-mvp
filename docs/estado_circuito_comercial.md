# Cierre del circuito de activacion comercial (estado real)

## Arquitectura

1. Worker privado consulta pagos_tappad, suscripciones_tappad y planes_tappad
   mediante credenciales de servidor.
2. Consulta directamente API Mercado Pago y verifica pago, preapproval, monto,
   moneda, estado y vendedor esperado (TAPPAD_MERCADOPAGO_SELLER_ID).
3. Abre conexion PostgreSQL PRIVADA y llama
   tappad_internal.tappad_aplicar_activacion_comercial en una transaccion.
4. La funcion bloquea duplicados mediante UNIQUE(pago_id), valida relaciones,
   plan y periodo, y actualiza suscripcion, activacion y acceso atomicamente.
5. Ante error, rollback; ante exito, commit.

## Estado y bloqueos

- La funcion SQL esta desplegada en esquema no expuesto y no admite anon,
  authenticated ni service_role.
- Existe tappad_activador_privado NOLOGIN con EXECUTE, sin acceso a tablas.
  **Por tanto, no puede completar la transaccion en este estado.**
- NO hay worker desplegado con identidad y credenciales de PostgreSQL privadas.
- No hay seller_id productivo configurado, ni pagos productivos conciliados.
- La fecha de inicio/fin aun es parametro del worker; se debe derivar de
  evidencia del proveedor y de la politica de renovacion antes de produccion.
- NO habilitar el flag TAPPAD_HABILITAR_ACTIVACION_PRODUCCION hasta cerrar esto.
- La funcion actual no valida criptograficamente p_evidencia; la autenticidad
  depende exclusivamente de un worker de confianza y su aislamiento.

## Validacion previa a produccion

1. Configurar worker servidor privado y credenciales de minimo privilegio.
2. Definir modelo de permisos de la funcion (RLS y tablas) y probar en staging.
3. Implementar calculo del ciclo de facturacion desde evidencia verificada.
4. Pruebas de rollback, pago duplicado, simultaneidad, pago cancelado, seller
   distinto y renovaciones (incluidas anticipadas).
5. Revisar CI y una transaccion integral en staging; despues aprobar despliegue.
6. Requerir aprobacion explicita para habilitar cobros o activaciones reales.

No copiar credenciales de produccion a GitHub, pruebas o frontend.

## Auditoria de solo lectura 2026-11-17

Se consultaron directamente las tablas de Supabase sin realizar escrituras:
- Suscripcion 1, cliente 4: estado `prueba`, proveedor `mercadopago_prueba`, `fin_periodo` nulo.
- Acceso comercial: estado `prueba`, `vigente_hasta` nulo.
- Un pago local registrado y cero activaciones comerciales.

**Interpretacion:** el pago del piloto no constituye una activacion productiva. No se debe transformar ni migrar automaticamente a `mercadopago_produccion`.

### Hallazgos de codigo que impiden el cierre productivo

- `worker_activacion_comercial.py` exige `--activar`, confirmacion `ACTIVAR`, variable `TAPPAD_HABILITAR_ACTIVACION_PRODUCCION=SI`, seller esperado y DSN privado. Mantener estos bloqueos.
- `activacion_privada_postgres.py` deriva el periodo de la fecha del pago local y periodicidad del plan. Rechaza pagos con mas de siete dias y renovaciones anticipadas cuyo vencimiento anterior sea futuro. Por tanto, **no esta demostrada la gestion completa de renovaciones anticipadas ni de reintentos tardios**.
- No se ha comprobado un worker privado desplegado con permisos PostgreSQL suficientes; una ejecucion local de pruebas no sustituye una transaccion en staging.
- Antes de habilitar produccion se requiere validar reversos, disputas, expiracion, reintentos idempotentes, concurrencia, y que un webhook no conceda acceso por si solo.

### Criterio de salida

Completar worker privado, identidad de minimo privilegio y pruebas de staging; documentar politica de renovacion y cobro; comprobar conciliacion de vendedor, importe, moneda y suscripcion remota; solicitar aprobacion explicita antes de activar cobros o acceso comercial productivo. Ninguna tarea de SECOP o ComprasMX debe alterarse durante este trabajo.

## Cancelaciones, contracargos y vencimientos — politica de acceso (2026-11-17)

El filtro de alertas SECOP `acceso_comercial_vigente` consulta en lectura la suscripcion, el acceso, la activacion y el pago asociado. Exige suscripcion `activa`, acceso `habilitado`, activacion `aplicada`, pago `pagado`, periodo no vencido y proveedor productivo permitido. Las pruebas de regresion ahora cubren suscripciones canceladas/suspendidas, pagos reembolsados/rechazados/con contracargo y activaciones revocadas.

**Limitacion critica:** estas verificaciones solo surten efecto cuando el estado local se actualiza de manera confiable. No existe en este cambio un procesador de webhook ni una conciliacion remota automatica de reembolsos, disputas o cancelaciones. Un contracargo en Mercado Pago que no se refleje en `pagos_tappad` puede dejar un acceso indebidamente habilitado hasta su deteccion. No declarar completo el circuito de cancelaciones ni habilitar produccion antes de cerrar esta brecha.

Politica propuesta para el cierre: recibir eventos autenticados, consultar estado actual directamente a Mercado Pago, vincular por payment_id/preapproval_id, registrar transicion de estado idempotente y auditable en backend privado, y bloquear nuevas alertas ante estados de riesgo confirmados. La cancelacion de una renovacion futura y la revocacion por reembolso/contracargo deben tratarse por separado; no revocar periodos ya pagados solo por la cancelacion de renovacion automatica sin validar las condiciones del contrato.
