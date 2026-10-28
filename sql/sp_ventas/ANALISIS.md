# Análisis de rendimiento: `sp_fru_Ventas_generalDevSeparada_5`

SQL Server 2012, ejecución por un mes.

| Archivo | Contenido |
|---|---|
| `sp_ventas_original.sql` | Copia del procedimiento actual (sin cambios). |
| `sp_ventas_optimizado.sql` | Versión optimizada. Se crea como `sp_fru_Ventas_generalDevSeparada_5_opt` para compararla lado a lado con la actual. Cada cambio está marcado con `--OPT`. |
| `indices_sugeridos.sql` | Diagnóstico de los índices actuales e índices de apoyo. |
| `validacion.sql` | Ejecuta las dos versiones con el mismo mes y compara tiempos, totales y renglones. |

## Causa principal

Aunque el reporte es de **un mes**, varias partes del procedimiento leen y agrupan **tablas completas (toda la historia)** en cada ejecución. El filtro por fecha se aplica hasta el final, cuando el trabajo pesado ya se hizo. Por eso el tiempo crece con el volumen histórico y no con el tamaño del mes.

Las referencias de línea son del archivo original.

### 1. GROUP BY de TODA `facfacturadet` y TODA `sciventa × sciventadet` (el problema más grande)

Este patrón aparece **4 veces** (líneas 371, 445, 504 y 1467):

```sql
INNER JOIN (SELECT C_CODIGO_FAC, ..., SUM(N_KILOS_DFA) ... FROM FACFACTURADET GROUP BY ...) FFD
```

y este otro **4 veces** (líneas 376, 450, 511 y 1474):

```sql
INNER JOIN (select ... sum(VD.N_CANTKILOS_DVT) ... from SCIVENTA JOIN SCIVENTADET group by ...) VD
```

SQL Server no puede bajar el filtro de fecha de `FF` hacia dentro de esas tablas derivadas con `GROUP BY`. El resultado es que agrega millones de renglones (en la práctica, normalmente con un *hash aggregate* sobre la tabla completa) y luego tira casi todo. En las ramas de **remisiones** (líneas 535 y 1508), `FF` ni siquiera tiene filtro de fecha.

**Cambio:** se materializan una sola vez y filtradas:

- `#FacP`: facturas P del mes más los 6 meses anteriores.
- `#FFDP` / `#VDP`: detalle y ventas solo de esas facturas.
- `#FFDRem` / `#VDRem`: detalle y ventas solo de los palets que participan en remisiones (`#PalRem`). El cruce original con `facporc` es por palet, así que el resultado es el mismo.

### 2. `#DESCCOMF`: DISTINCT de todos los acuses y de todo el detalle (líneas 753–805)

- La tabla derivada `acu` hace `DISTINCT Acu.*` sobre **todos** los acuses unidos con facturas y notas. Después se filtra por `acu.Fecha`, que es una columna calculada con `CASE`, y por eso el filtro no puede usar índices.
- `adl` agrupa **todo** `sciacusedetpal` y `dfa` agrupa **todo** `facfacturadet` (otra vez).
- `#DESCCOM` agrupa **toda** la vista `vFruPorcDescComercial`.

**Cambio:** `#Acu` aplica la misma regla de fecha (fecha de la nota si existe; si no, la de la factura) con dos búsquedas por fecha que sí usan índices. Después `adl`, `dfa` y `#DESCCOM` se limitan a esos acuses.

### 3. Gastos por palet de 24 meses (líneas 206–228)

Se cargan los gastos de **todas** las recepciones de 24 meses, aunque al final solo se usan las de los palets facturados, remisionados o mermados en el mes. Además, había dos `GROUP BY` idénticos anidados, y `#GASTOFLETECONC` (líneas 289–296) era una tercera copia agrupada de lo mismo.

**Cambio:** `#RecNec` junta las recepciones que realmente se van a cruzar. Se mantiene también el filtro de 24 meses, así que el resultado no cambia. Queda un solo `GROUP BY` y se elimina `#GASTOFLETECONC`.

### 4. Remisiones calculadas dos veces (líneas 66–189)

`#RemAcum` y `#PorcRemision` ejecutaban exactamente los mismos joins: un *self-join* de `facfacturadet` por palet, que es muy caro sin índice en `(c_codigo_pal, c_codsec_pal)`.

**Cambio:** el detalle se calcula una vez en `#RemDet` y de ahí salen las dos tablas.

### 5. Merma Recepción: filtro `CASE ... BETWEEN` (línea 1388)

```sql
AND case when LIQ... then LIQ.d_fecha_lqd else VTA.d_fecha_vta end BETWEEN @FechaIni AND @FechaFin
```

Este filtro no puede usar índices, así que se leían **todas las mermas de la historia**. Además, la subconsulta de liquidaciones se recalculaba en línea (era idéntica a `#Liq`).

**Cambio:** `#VtaMerma` es un conjunto candidato que se arma con dos búsquedas indexables, una por fecha de venta y otra por fecha de liquidación. El filtro original se conserva tal cual. `#Liq` se crea al inicio y se reutiliza.

### 6. Problemas de estimación del optimizador

- `@CFDIDescarga` es una **variable tabla**: SQL Server 2012 siempre estima 1 fila para ella y elige *nested loops* en la consulta de `#Ventas`. → Se cambia a `#CFDIDescarga` con índice (y `COLLATE DATABASE_DEFAULT` para no tener conflictos de intercalación).
- `fnFruDevolucionDesglosadaNPC3` se unía directamente. Si es una función *multi-statement*, SQL 2012 también estima 1 fila. → Se materializa en `#DevNPC` con índice.
- Pasar las fechas a variables locales (`@FechaI`) evita el *parameter sniffing*, pero hace que el optimizador **no conozca las fechas** y estime a ciegas. → Las consultas pesadas llevan `OPTION (RECOMPILE)`, que usa los valores reales en cada ejecución. El costo de recompilar es de milisegundos.
- `#Ventas`, `#DESCCOMF`, `#AjustesNC`, `#Costo` y `#PorcRemision` no tenían índice, y se cruzan entre sí por 6 a 10 columnas. → Se agregan índices *clustered*.

## Índices (`indices_sugeridos.sql`)

Los más importantes, en este orden:

1. `facfacturadet (c_codigo_pal, c_codsec_pal)`: *self-join* de remisiones.
2. `FruGastosPorPalet (c_codigo_rec) INCLUDE (...)`.
3. `facfactura (c_grupo_fac, d_fecha_fac)` y `facfactura (c_codigo_acu)`.
4. `sciventadet (c_codigo_pal, c_codsec_pal)` y `sciventa (c_tipovta_vta, d_fecha_vta)`.

Revisa la sección A del script antes de crearlos, porque algunos pueden existir ya con otro nombre.

## Posibles errores detectados (NO se modificaron, para no cambiar resultados)

Están igual en la versión optimizada. Conviene revisarlos con el área contable:

1. **Join FF → FFD sin grupo** (líneas 375, 449, 508, 606 y 1471):
   ```sql
   AND FF.C_SERIE_FAC = FFD.C_SERIE_FAC
   AND FF.C_SERIE_FAC = FFD.C_SERIE_FAC   -- repetido; probablemente debía ser C_GRUPO_FAC
   ```
   Si existe el mismo código y serie en otro grupo (P/R/N/C), se mezclan sus detalles y se **duplican cantidades e importes**. Esto también afecta a `#Ventas`.
2. **Comparación sin efecto** (líneas 401 y 475): `tempF.c_grupo_fac = tempF.c_grupo_fac` siempre es verdadero; seguramente debía ser `dev.c_grupo_fac`.
3. **`#RemAcum`** (rama "Facturado") se une con `scidevolucion`. Si una remisión tiene más de una devolución, la cantidad se multiplica en esa rama pero no en la de merma, y se sesga el porcentaje `porc`.
4. `#FacOrig` y `#Notas` pueden duplicar renglones si una póliza cancela más de una factura.

## Cómo implementarlo

1. Ejecutar la sección A de `indices_sugeridos.sql` y crear los índices que falten (fuera de horario).
2. Ejecutar `sp_ventas_optimizado.sql` para crear `sp_fru_Ventas_generalDevSeparada_5_opt`.
3. Ejecutar `validacion.sql` con uno o dos meses recientes y uno antiguo. Los totales por `Tipo` deben coincidir, y las dos consultas de diferencias deben salir vacías.
4. Cuando quede validado, cambiar el encabezado a `ALTER PROCEDURE [dbo].[sp_fru_Ventas_generalDevSeparada_5]` y quitar la versión `_opt`.

Para ver qué sentencia tarda más en cualquiera de las dos versiones:

```sql
SET STATISTICS IO, TIME ON
EXEC dbo.sp_fru_Ventas_generalDevSeparada_5_opt '20260901', '20260930', 'FRUSA'
```

(o incluir el plan de ejecución real en SSMS).

### Nota sobre equivalencia

Todos los filtros nuevos son **superconjuntos** de lo que el procedimiento original terminaba usando, y los filtros originales se conservan. Por eso el resultado debe ser idéntico. La única diferencia teórica es que la rama "Merma Recepción" ahora lee `n_porcentajecomision_lqd` desde `#Liq`, que lo guarda como `decimal(18,4)`. Antes lo hacía así solo "Merma Remisión". Solo cambiaría el resultado si un porcentaje de comisión tuviera más de 4 decimales.

No pude ejecutarlo contra la base de datos: el script de validación es la prueba.
