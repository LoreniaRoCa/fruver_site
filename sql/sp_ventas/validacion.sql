USE [AgroSmart_FRUSA]
GO
/*
	Compara el resultado del procedimiento original contra el optimizado para un mismo mes.
	Requisitos: tener creado [dbo].[sp_fru_Ventas_generalDevSeparada_5_opt] (sp_ventas_optimizado.sql).
	Ejecutar en un horario tranquilo: corre ambos procedimientos completos.
*/
DECLARE @Ini DATETIME = '20260901', @Fin DATETIME = '20260930', @Emp VARCHAR(10) = 'FRUSA'
DECLARE @t0 DATETIME2, @SegOriginal INT, @SegOptimizado INT

IF OBJECT_ID('tempdb..#Orig') IS NOT NULL DROP TABLE #Orig
CREATE TABLE #Orig (
	Tipo VARCHAR(50), Entidad VARCHAR(10), Fecha DATETIME, Factura VARCHAR(100), Viaje VARCHAR(100), Recepcion VARCHAR(100),
	Producto VARCHAR(100), ProductoNPC VARCHAR(100), Presentacion VARCHAR(100), Etiqueta VARCHAR(200), Cliente VARCHAR(100),
	Proveedor VARCHAR(100), Unidad VARCHAR(10), Vendedor VARCHAR(100), Comprador VARCHAR(100), Lugar_Destino VARCHAR(200),
	CantidadVenta DECIMAL(38,8), CantidadFacturada DECIMAL(38,8), VentaBruta DECIMAL(38,8), DifKilo DECIMAL(38,8),
	DifPrecio DECIMAL(38,8), Merma DECIMAL(38,8), DescCom DECIMAL(38,8), BonificacionVenta DECIMAL(38,8),
	NotaCargoVenta DECIMAL(38,8), NotaCargoLiq DECIMAL(38,8), VentaNeta DECIMAL(38,8), CostoFlete DECIMAL(38,8),
	ClienteNombre VARCHAR(300), ProductoNombre VARCHAR(300), NombreVendedor VARCHAR(300),
	Comision DECIMAL(38,8), Proteccion DECIMAL(38,8), Coaseguro DECIMAL(38,8), ImporteGastos DECIMAL(38,8),
	ImporteFlete DECIMAL(38,8), CostoCompra DECIMAL(38,8), Utilidad DECIMAL(38,8), CantidadRecibida DECIMAL(38,8),
	ImporteAPagarProductor DECIMAL(38,8), TipoCompra VARCHAR(10), Bodega VARCHAR(200), Referencia VARCHAR(100),
	TipoCambio DECIMAL(38,8), ChequeCobro VARCHAR(100), BonifMerma DECIMAL(38,8), FechaCosto DATETIME,
	PorcDescuento DECIMAL(38,8), FacturaOrigen VARCHAR(100), ImporteGastosCosto DECIMAL(38,8))

IF OBJECT_ID('tempdb..#Opt') IS NOT NULL DROP TABLE #Opt
SELECT * INTO #Opt FROM #Orig WHERE 1 = 0

SET @t0 = SYSDATETIME()
INSERT INTO #Orig EXEC dbo.sp_fru_Ventas_generalDevSeparada_5 @Ini, @Fin, @Emp
SET @SegOriginal = DATEDIFF(SECOND, @t0, SYSDATETIME())

SET @t0 = SYSDATETIME()
INSERT INTO #Opt EXEC dbo.sp_fru_Ventas_generalDevSeparada_5_opt @Ini, @Fin, @Emp
SET @SegOptimizado = DATEDIFF(SECOND, @t0, SYSDATETIME())

SELECT @SegOriginal SegundosOriginal, @SegOptimizado SegundosOptimizado

-- 1) Totales por tipo de renglón: deben coincidir
SELECT	ISNULL(o.Tipo, n.Tipo) Tipo, o.Renglones RenglonesOrig, n.Renglones RenglonesOpt,
		o.VentaNeta VentaNetaOrig, n.VentaNeta VentaNetaOpt, o.CostoCompra CostoOrig, n.CostoCompra CostoOpt,
		o.Gastos GastosOrig, n.Gastos GastosOpt, o.Utilidad UtilidadOrig, n.Utilidad UtilidadOpt
FROM	(SELECT Tipo, COUNT(*) Renglones, SUM(VentaNeta) VentaNeta, SUM(CostoCompra) CostoCompra,
				SUM(ImporteGastos + ImporteFlete + ImporteGastosCosto) Gastos, SUM(Utilidad) Utilidad FROM #Orig GROUP BY Tipo) o
		FULL JOIN
		(SELECT Tipo, COUNT(*) Renglones, SUM(VentaNeta) VentaNeta, SUM(CostoCompra) CostoCompra,
				SUM(ImporteGastos + ImporteFlete + ImporteGastosCosto) Gastos, SUM(Utilidad) Utilidad FROM #Opt GROUP BY Tipo) n
		ON o.Tipo = n.Tipo
ORDER BY 1

-- 2) Renglones que están en uno y no en el otro (redondeado a 2 decimales). Ambos resultados deben salir vacíos.
;WITH O AS (SELECT Tipo, Fecha, Factura, Recepcion, Presentacion, Etiqueta, Cliente, Proveedor, Vendedor, Referencia, FechaCosto,
				ROUND(CantidadVenta,2) CantidadVenta, ROUND(VentaBruta,2) VentaBruta, ROUND(VentaNeta,2) VentaNeta, ROUND(Comision,2) Comision,
				ROUND(ImporteGastos,2) ImporteGastos, ROUND(ImporteFlete,2) ImporteFlete, ROUND(CostoCompra,2) CostoCompra,
				ROUND(Utilidad,2) Utilidad, ROUND(CantidadRecibida,2) CantidadRecibida, ROUND(ImporteGastosCosto,2) ImporteGastosCosto FROM #Orig),
	  N AS (SELECT Tipo, Fecha, Factura, Recepcion, Presentacion, Etiqueta, Cliente, Proveedor, Vendedor, Referencia, FechaCosto,
				ROUND(CantidadVenta,2) CantidadVenta, ROUND(VentaBruta,2) VentaBruta, ROUND(VentaNeta,2) VentaNeta, ROUND(Comision,2) Comision,
				ROUND(ImporteGastos,2) ImporteGastos, ROUND(ImporteFlete,2) ImporteFlete, ROUND(CostoCompra,2) CostoCompra,
				ROUND(Utilidad,2) Utilidad, ROUND(CantidadRecibida,2) CantidadRecibida, ROUND(ImporteGastosCosto,2) ImporteGastosCosto FROM #Opt)
SELECT 'Solo en ORIGINAL' Donde, * FROM (SELECT * FROM O EXCEPT SELECT * FROM N) x
UNION ALL
SELECT 'Solo en OPTIMIZADO', * FROM (SELECT * FROM N EXCEPT SELECT * FROM O) y
ORDER BY 2, 4, 5
