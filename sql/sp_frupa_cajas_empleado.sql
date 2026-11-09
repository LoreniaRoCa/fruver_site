/*
  dbo.sp_frupa_cajas_empleado  (base fruverpack, SQL Server 2012)

  Cajas por empleado: cajas etiquetadas por cada empacador por día (t_controlcaja_pallet), con el desglose
  en charola y bolsa. Mismo criterio que el reporte "Reporte de cajas por empleado" (sp_cajaemp_fruv):
    - Charola: calidad con código externo A o C;  Bolsa: B;  Cajas: todas las cajas del empleado.
  A diferencia de sp_cajaemp_fruv no llena una tabla temporal: regresa los renglones del periodo.

  Lo usan:
    - sincronizar_sqlserver.py 4  -> rep_cajas_empleado en Supabase (tabla dinámica del portal)
    - Fruverpack, frmpivotDS (plantilla CAJAS POR EMPLEADO)

  Parámetros (todos opcionales; @FechaIni y @FechaFin como los demás procedimientos de frmpivotDS):
    @FechaIni, @FechaFin  fecha de la caja (d_fechacaja_ccp); toma las temporadas de ese periodo
    @temporada            una temporada; sin fechas ni temporada, la activa (t_temporada.c_activo_tem = '1')

  El día de la semana se calcula sin DATEPART(WEEKDAY) para que no dependa del idioma de la conexión
  (el 01/01/1900 fue lunes).

  Ejemplos:
    EXEC dbo.sp_frupa_cajas_empleado
    EXEC dbo.sp_frupa_cajas_empleado @FechaIni = '20261102', @FechaFin = '20261107'
*/
IF OBJECT_ID('dbo.sp_frupa_cajas_empleado', 'P') IS NOT NULL
    DROP PROCEDURE dbo.sp_frupa_cajas_empleado;
GO

CREATE PROCEDURE dbo.sp_frupa_cajas_empleado
    @FechaIni  DATE = NULL,
    @FechaFin  DATE = NULL,
    @temporada CHAR(2) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @temporadas TABLE (c_codigo_tem CHAR(2) PRIMARY KEY);

    IF @temporada IS NOT NULL
        INSERT INTO @temporadas VALUES (@temporada);
    ELSE IF @FechaIni IS NULL AND @FechaFin IS NULL
        INSERT INTO @temporadas
        SELECT TOP 1 c_codigo_tem FROM dbo.t_temporada WITH (NOLOCK) WHERE c_activo_tem = '1' ORDER BY c_codigo_tem DESC;
    ELSE
        INSERT INTO @temporadas
        SELECT DISTINCT c_codigo_tem FROM dbo.t_controlcaja_pallet WITH (NOLOCK)
        WHERE  (@FechaIni IS NULL OR d_fechacaja_ccp >= @FechaIni) AND (@FechaFin IS NULL OR d_fechacaja_ccp < DATEADD(DAY, 1, @FechaFin));

    SELECT  temporada      = ccp.c_codigo_tem,
            fecha          = CAST(ccp.d_fechacaja_ccp AS DATE),
            dia            = CASE DATEDIFF(DAY, '19000101', CAST(ccp.d_fechacaja_ccp AS DATE)) % 7
                                  WHEN 0 THEN 'LUNES' WHEN 1 THEN 'MARTES' WHEN 2 THEN 'MIERCOLES' WHEN 3 THEN 'JUEVES'
                                  WHEN 4 THEN 'VIERNES' WHEN 5 THEN 'SABADO' ELSE 'DOMINGO' END,
            codigo_empleado = ccp.c_codigo_emp,
            empleado       = LTRIM(RTRIM(REPLACE(ISNULL(nom.v_apellidopat_emp, '') + ' ' + ISNULL(nom.v_apellidomat_emp, '') + ' '
                                                 + ISNULL(nom.v_nombre_emp, ''), '  ', ' '))),
            punto_empaque  = pem.v_nombre_pem,
            banda          = ISNULL(bnd.v_nombre_bnd, ccp.c_codigo_bnd),
            cultivo        = cul.v_nombre_cul,
            cajas          = COUNT(*),
            charola        = SUM(CASE WHEN cal.v_codext_prc IN ('A', 'C') THEN 1 ELSE 0 END),
            bolsa          = SUM(CASE WHEN cal.v_codext_prc = 'B' THEN 1 ELSE 0 END)
    FROM    dbo.t_controlcaja_pallet ccp WITH (NOLOCK)
            LEFT JOIN dbo.nomempleados nom WITH (NOLOCK) ON nom.c_codigo_emp = ccp.c_codigo_emp
            LEFT JOIN dbo.t_producto pro WITH (NOLOCK) ON pro.c_codigo_pro = LEFT(ccp.c_codigo_pro, 4)
            LEFT JOIN dbo.t_cultivo cul WITH (NOLOCK) ON cul.c_codigo_cul = pro.c_codigo_cul
            LEFT JOIN dbo.t_producto_calidad cal WITH (NOLOCK) ON cal.c_codigo_prc = pro.c_codigo_prc
            LEFT JOIN dbo.t_puntoempaque pem WITH (NOLOCK) ON pem.c_codigo_pem = ccp.c_codigo_pem
            LEFT JOIN dbo.t_banda bnd WITH (NOLOCK) ON bnd.c_codigo_bnd = ccp.c_codigo_bnd
    WHERE   ccp.c_codigo_tem IN (SELECT c_codigo_tem FROM @temporadas)
            AND (@FechaIni IS NULL OR ccp.d_fechacaja_ccp >= @FechaIni)
            AND (@FechaFin IS NULL OR ccp.d_fechacaja_ccp < DATEADD(DAY, 1, @FechaFin))
    GROUP BY ccp.c_codigo_tem, CAST(ccp.d_fechacaja_ccp AS DATE), ccp.c_codigo_emp, nom.v_apellidopat_emp, nom.v_apellidomat_emp,
             nom.v_nombre_emp, pem.v_nombre_pem, ISNULL(bnd.v_nombre_bnd, ccp.c_codigo_bnd), cul.v_nombre_cul
    ORDER BY empleado, fecha;
END
GO
