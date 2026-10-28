USE [AgroSmart_FRUSA]
GO
/*
	Índices de apoyo para sp_fru_Ventas_generalDevSeparada_5(_opt)

	1) Ejecutar primero la SECCIÓN A para ver los índices que YA existen. Si ya hay uno con las mismas
	   columnas clave (en el mismo orden), no crear el sugerido.
	2) Crear los índices fuera del horario de operación: en SQL Server 2012 Standard la creación bloquea la tabla
	   (ONLINE = ON solo existe en Enterprise).
	3) Los nombres de columna se tomaron del procedimiento; ajustar si alguna difiere.
*/

---------------------------------------------------------------------------------------------------
-- SECCIÓN A. Índices existentes en las tablas involucradas
---------------------------------------------------------------------------------------------------
SELECT	t.name Tabla, i.name Indice, i.type_desc, i.is_primary_key,
		STUFF((SELECT ', ' + c.name FROM sys.index_columns ic JOIN sys.columns c ON c.object_id = ic.object_id AND c.column_id = ic.column_id
			   WHERE ic.object_id = i.object_id AND ic.index_id = i.index_id AND ic.is_included_column = 0 ORDER BY ic.key_ordinal FOR XML PATH('')), 1, 2, '') Llave,
		STUFF((SELECT ', ' + c.name FROM sys.index_columns ic JOIN sys.columns c ON c.object_id = ic.object_id AND c.column_id = ic.column_id
			   WHERE ic.object_id = i.object_id AND ic.index_id = i.index_id AND ic.is_included_column = 1 FOR XML PATH('')), 1, 2, '') Incluidas
FROM	sys.indexes i JOIN sys.tables t ON t.object_id = i.object_id
WHERE	t.name IN ('facfactura', 'facfacturadet', 'sciventa', 'sciventadet', 'FruGastosPorPalet', 'scirecepcion', 'scidevolucion',
				   'sciliquidacionproductor', 't_palet', 'sciAcuse', 'sciacusedetpal', 'FruGasRepetidos')
		AND i.type > 0
ORDER BY t.name, i.index_id

-- Tamaño de las tablas (filas)
SELECT	t.name Tabla, SUM(p.rows) Filas
FROM	sys.tables t JOIN sys.partitions p ON p.object_id = t.object_id AND p.index_id IN (0, 1)
WHERE	t.name IN ('facfactura', 'facfacturadet', 'sciventa', 'sciventadet', 'FruGastosPorPalet', 'scirecepcion', 'scidevolucion',
				   'sciliquidacionproductor', 't_palet', 'sciAcuse', 'sciacusedetpal')
GROUP BY t.name ORDER BY 2 DESC

-- Índices que el propio SQL Server reporta como faltantes (se reinicia al reiniciar el servicio)
SELECT TOP 30 d.statement Tabla, d.equality_columns, d.inequality_columns, d.included_columns,
		s.user_seeks + s.user_scans Usos, CONVERT(int, s.avg_total_user_cost * s.avg_user_impact * (s.user_seeks + s.user_scans)) Beneficio
FROM	sys.dm_db_missing_index_details d JOIN sys.dm_db_missing_index_groups g ON g.index_handle = d.index_handle
		JOIN sys.dm_db_missing_index_group_stats s ON s.group_handle = g.index_group_handle
WHERE	d.database_id = DB_ID()
ORDER BY Beneficio DESC
GO

---------------------------------------------------------------------------------------------------
-- SECCIÓN B. Índices sugeridos (prioridad de mayor a menor)
---------------------------------------------------------------------------------------------------

-- 1. Detalle de factura por palet: self-join de remisiones (#RemDet), #FFDRem y #RecNec.
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID('dbo.facfacturadet') AND name = 'IX_facfacturadet_palet')
	CREATE NONCLUSTERED INDEX IX_facfacturadet_palet ON dbo.facfacturadet (c_codigo_pal, c_codsec_pal)
	INCLUDE (c_codigo_fac, c_serie_fac, c_grupo_fac, n_kilos_dfa, n_bultos_dfa) WITH (SORT_IN_TEMPDB = ON)
GO

-- 2. Gastos por recepción: carga de #GASTOFLETEDET.
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID('dbo.FruGastosPorPalet') AND name = 'IX_FruGastosPorPalet_rec')
	CREATE NONCLUSTERED INDEX IX_FruGastosPorPalet_rec ON dbo.FruGastosPorPalet (c_codigo_rec)
	INCLUDE (c_codigo_pal, c_codsec_pal, c_codigo_man, c_serie_fac, c_grupo_fac, c_codigo_fac,
			 c_tipo_gto, c_codigo_ccf, c_extemporaneo_gto, n_importe_gto, c_adicional_gto) WITH (SORT_IN_TEMPDB = ON)
GO

-- 3. Facturas por grupo y fecha: #FacP, #Ventas, remisiones, LIQ.
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID('dbo.facfactura') AND name = 'IX_facfactura_grupo_fecha')
	CREATE NONCLUSTERED INDEX IX_facfactura_grupo_fecha ON dbo.facfactura (c_grupo_fac, d_fecha_fac)
	INCLUDE (c_codigo_fac, c_serie_fac, c_codigo_vta, c_tipovta_vta, c_estatus_fac, c_activo_fac) WITH (SORT_IN_TEMPDB = ON)
GO

-- 4. Notas ligadas a acuse (#Acu: NOT EXISTS y fecha de la nota).
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID('dbo.facfactura') AND name = 'IX_facfactura_codigo_acu')
	CREATE NONCLUSTERED INDEX IX_facfactura_codigo_acu ON dbo.facfactura (c_codigo_acu) INCLUDE (d_fecha_fac) WITH (SORT_IN_TEMPDB = ON)
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID('dbo.facfactura') AND name = 'IX_facfactura_fecha')
	CREATE NONCLUSTERED INDEX IX_facfactura_fecha ON dbo.facfactura (d_fecha_fac) INCLUDE (c_codigo_acu, c_grupo_fac) WITH (SORT_IN_TEMPDB = ON)
GO

-- 5. Detalle de venta por palet: mermas de remisión, #VDRem, #VtaMerma, #RecNec.
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID('dbo.sciventadet') AND name = 'IX_sciventadet_palet')
	CREATE NONCLUSTERED INDEX IX_sciventadet_palet ON dbo.sciventadet (c_codigo_pal, c_codsec_pal)
	INCLUDE (c_codigo_vta, c_tipovta_vta, n_cantkilos_dvt, n_cantidad_dvt) WITH (SORT_IN_TEMPDB = ON)
GO

-- 6. Ventas de merma por fecha (#VtaMerma).
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID('dbo.sciventa') AND name = 'IX_sciventa_tipo_fecha')
	CREATE NONCLUSTERED INDEX IX_sciventa_tipo_fecha ON dbo.sciventa (c_tipovta_vta, d_fecha_vta) INCLUDE (c_activo_vta) WITH (SORT_IN_TEMPDB = ON)
GO

-- 7. Ventas por acuse (#DevFac, devoluciones tipo 'D').
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID('dbo.sciventa') AND name = 'IX_sciventa_acu')
	CREATE NONCLUSTERED INDEX IX_sciventa_acu ON dbo.sciventa (c_codigo_acu) INCLUDE (c_activo_vta, c_cancelada_vta) WITH (SORT_IN_TEMPDB = ON)
GO

-- 8. Devoluciones por fecha y por factura origen.
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID('dbo.scidevolucion') AND name = 'IX_scidevolucion_fecha')
	CREATE NONCLUSTERED INDEX IX_scidevolucion_fecha ON dbo.scidevolucion (d_fecha_dev)
	INCLUDE (c_codigo_vta, c_tipovta_vta, c_facturaorigen_fac, c_serieorigen_fac, c_grupoorigen_fac, c_tipo_dev) WITH (SORT_IN_TEMPDB = ON)
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID('dbo.scidevolucion') AND name = 'IX_scidevolucion_origen')
	CREATE NONCLUSTERED INDEX IX_scidevolucion_origen ON dbo.scidevolucion (c_facturaorigen_fac, c_serieorigen_fac, c_grupoorigen_fac)
	INCLUDE (c_codigo_vta, c_tipovta_vta) WITH (SORT_IN_TEMPDB = ON)
GO

-- 9. Liquidaciones y palets por recepción/lote/referencia (#Liq, #VtaMerma, joins LIQ).
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID('dbo.sciliquidacionproductor') AND name = 'IX_sciliquidacionproductor_rec')
	CREATE NONCLUSTERED INDEX IX_sciliquidacionproductor_rec ON dbo.sciliquidacionproductor (c_codigo_rec, c_codigo_lot, c_referencia_red) WITH (SORT_IN_TEMPDB = ON)
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID('dbo.t_palet') AND name = 'IX_t_palet_rec_lot_red')
	CREATE NONCLUSTERED INDEX IX_t_palet_rec_lot_red ON dbo.t_palet (c_codigo_rec, c_codigo_lot, c_referencia_red) WITH (SORT_IN_TEMPDB = ON)
GO

-- 10. Acuse por factura (#Acu).
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID('dbo.sciAcuse') AND name = 'IX_sciAcuse_factura')
	CREATE NONCLUSTERED INDEX IX_sciAcuse_factura ON dbo.sciAcuse (c_codigo_fac, c_serie_fac, c_grupo_fac) WITH (SORT_IN_TEMPDB = ON)
GO

-- Después de crear índices conviene actualizar estadísticas de las tablas grandes:
-- UPDATE STATISTICS dbo.facfactura WITH FULLSCAN
-- UPDATE STATISTICS dbo.facfacturadet
-- UPDATE STATISTICS dbo.FruGastosPorPalet
-- UPDATE STATISTICS dbo.sciventadet
