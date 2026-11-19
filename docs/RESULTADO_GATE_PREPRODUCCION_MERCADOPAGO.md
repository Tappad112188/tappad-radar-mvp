# Resultado de compuerta productiva de solo lectura — Mercado Pago

Fecha: 2026-11-19. Proyecto Supabase: rgzjrziulhobgjfhwvfw.

Se ejecutó `docs/sql_gate_despliegue_mercadopago_lectura.sql` en producción **sin escrituras**.

| Comprobación | Valor |
| --- | --- |
| Base | postgres |
| CHECK contracargo | false |
| Función de reversión instalada | false |
| Rol privado NOLOGIN | false |
| Función de activación privada con firma esperada | false |
| anon puede ejecutar reversión | false |
| authenticated puede ejecutar reversión | false |
| Tablas comerciales con RLS | 4 |
| Dictamen | BLOQUEADO_PENDIENTE_MIGRACION |

La CI aislada 44640108995 completó correctamente, incluyendo reversión histórica y contracargo vigente.
https://github.com/Tappad112188/tappad-radar-mvp/actions/runs/44640108995

**No confundir:** pruebas exitosas en PostgreSQL efímero no significan migración instalada o autorización de cobros productivos.

## Pendientes previos al despliegue
- Verificar mecanismo de ejecución segura del worker con consulta directa a Mercado Pago y secretos aislados.
- Revisar SQL de migración exacto, esquema de roles y permisos efectivos.
- Preparar y verificar copia de seguridad y plan de reversión.
- Obtener autorización explícita para cambios DDL productivos.
- Tras migrar, volver a ejecutar la compuerta y verificar el resultado, sin habilitar cobros hasta la prueba supervisada.
