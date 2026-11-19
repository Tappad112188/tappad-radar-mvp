# Plan de migración de reversión — mínimo privilegio (NO APLICAR)

## Evidencia
- PostgreSQL 17: 11 pruebas aprobadas en Actions #44441190479.
- Las pruebas de activación vs. reversión simulan el orden de bloqueos; no invocan la función real de activación.
- Supabase producción: RLS activo en pagos, suscripciones, acceso y activaciones; FORCE RLS desactivado.
- El SQL original `docs/sql_preparacion_reversion_privada_NO_APLICAR.sql` propone permisos UPDATE directos y políticas USING(true) para un rol NOLOGIN. **No desplegarlo tal cual.**

## Diseño de seguridad objetivo
1. Mantener la verificación del pago y vendedor en un ejecutor privado, nunca en el navegador o webhook.
2. Crear una función privada con permisos de ejecución únicamente para una identidad operativa separada y sin acceso público. Evitar GRANT UPDATE directo sobre tablas comerciales a esa identidad.
3. Definir un límite de confianza comprobable para la evidencia remota: los parámetros JSON no son una firma ni una prueba de pago.
4. Bloquear en el mismo orden en activación y reversión: suscripción, acceso, pago; incorporar pruebas reales de ambas funciones bajo concurrencia.
5. Aplicar política de denegación por defecto a roles `anon` y `authenticated`; comprobar `has_function_privilege`, `has_table_privilege`, membresías y exposición de esquemas.
6. Probar migración y rollback en copia de esquema productivo con FK, RLS, constraints, propietarios y grants. No copiar datos personales ni tokens productivos.
7. Solo después, aprobar DDL productivo idempotente, verificar constraints y advisors, y ejecutar pruebas supervisadas de sandbox.

## Puertas de aprobación
- 11/11 pruebas aisladas: **aprobado**
- Prueba de funciones reales activación/reversión simultáneas: **pendiente**
- Copia fiel de esquema, RLS y permisos: **pendiente**
- Rol operativo sin UPDATE directo: **pendiente**
- Migración productiva: **no aplicada**
- Pago productivo: **no realizado**

## Restricción
No habilitar `TAPPAD_HABILITAR_REVERSION_PRODUCCION` ni ningún flujo de cobro productivo hasta superar las puertas pendientes.
