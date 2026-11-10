/*
  dbo.sp_frupa_pallets  (base fruverpack, SQL Server 2012)

  Pallets: cada pallet empacado (t_palet) con su etiqueta, producto, lote, manifiesto y estiba.
  Un pallet mixto tiene un renglón por sección (c_codsec_pal).

  Lo usan:
    - sincronizar_sqlserver.py 5  -> rep_pallets en Supabase (plantilla de Excel "Pallets" del portal)

  Parámetros (todos opcionales; @FechaIni y @FechaFin como los demás procedimientos de frmpivotDS):
    @FechaIni, @FechaFin  fecha de empaque (d_empaque_pal); toma las temporadas de ese periodo
    @temporada            una temporada; sin fechas ni temporada, la activa (t_temporada.c_activo_tem = '1')

  Ejemplos:
    EXEC dbo.sp_frupa_pallets
    EXEC dbo.sp_frupa_pallets @FechaIni = '20261101', @FechaFin = '20261110'
*/
IF OBJECT_ID('dbo.sp_frupa_pallets', 'P') IS NOT NULL
    DROP PROCEDURE dbo.sp_frupa_pallets;
GO

CREATE PROCEDURE dbo.sp_frupa_pallets
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
        SELECT DISTINCT c_codigo_tem FROM dbo.t_palet WITH (NOLOCK)
        WHERE  (@FechaIni IS NULL OR d_empaque_pal >= @FechaIni) AND (@FechaFin IS NULL OR d_empaque_pal < DATEADD(DAY, 1, @FechaFin));

    SELECT  temporada   = pal.c_codigo_tem,
            pallet      = pal.c_codigo_pal,
            seccion     = pal.c_codsec_pal,
            fecha       = CAST(pal.d_empaque_pal AS DATE),
            hora        = pal.c_hora_pal,
            lote        = pal.c_codigo_lot,
            nombre_lote = lot.v_nombre_lot,
            manifiesto  = RTRIM(pal.c_codigo_man),
            estiba      = ISNULL(RTRIM(pal.c_codigo_est), ''),
            seleccion   = pal.c_codigo_sel,
            etiqueta    = RTRIM(eti.v_nombre_eti),
            producto    = pro.v_nombre_pro,
            cajas       = pal.n_bulxpa_pal
    FROM    dbo.t_palet pal WITH (NOLOCK)
            INNER JOIN dbo.t_producto pro WITH (NOLOCK) ON pro.c_codigo_pro = pal.c_codigo_pro
            INNER JOIN dbo.t_etiqueta eti WITH (NOLOCK) ON eti.c_codigo_eti = pal.c_codigo_eti
            LEFT  JOIN dbo.t_lote lot WITH (NOLOCK) ON lot.c_codigo_tem = pal.c_codigo_tem AND lot.c_codigo_lot = pal.c_codigo_lot
    WHERE   pal.c_codigo_tem IN (SELECT c_codigo_tem FROM @temporadas)
            AND (@FechaIni IS NULL OR pal.d_empaque_pal >= @FechaIni)
            AND (@FechaFin IS NULL OR pal.d_empaque_pal < DATEADD(DAY, 1, @FechaFin))
    ORDER BY pal.d_empaque_pal, pal.c_codigo_pal, pal.c_codsec_pal;
END
GO
