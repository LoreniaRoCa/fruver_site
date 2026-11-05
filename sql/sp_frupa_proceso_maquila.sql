/*
  dbo.sp_frupa_proceso_maquila  (base Fruverpack, SQL Server 2012)

  Proceso de maquila: lo que entregó el productor (recepción, t_recepciondet) contra lo que salió del
  empaque (t_palet). Un renglón por estiba + producto + etiqueta.

  Lo usan:
    - sincronizar_sqlserver.py 3  -> rep_proceso_maquila en Supabase (tabla dinámica y tablero del portal)
    - Fruverpack, frmTableroMaquila -> directo, con la información al instante

  Parámetros (todos opcionales; @FechaIni y @FechaFin como los demás procedimientos de frmpivotDS):
    @FechaIni, @FechaFin  fecha de la estiba (t_seleccion.d_fecha_sel); toma las temporadas de ese periodo
    @temporada            una temporada; sin fechas ni temporada, la activa (t_temporada.c_activo_tem = '1')

  Columnas:
    - resumen: "estiba | promedio por caja | cajas | kilos recibidos"
    - tipo: 'Empaque' o 'Mermas y subproductos' (envase 03 = KILOGRAMOS / bins)
    - cajas: cajas de empaque; en mermas, bultos
    - kilos: peso promedio del producto (n_pesbul_pro) por cajas
    - kilos_recibidos y cajas_recibidas: solo en el primer renglón de cada estiba (en los demás 0),
      para sumarlos por lote, dueño o variedad sin duplicar

  Ejemplos:
    EXEC dbo.sp_frupa_proceso_maquila
    EXEC dbo.sp_frupa_proceso_maquila @FechaIni = '20261001', @FechaFin = '20261031'
*/
IF OBJECT_ID('dbo.sp_frupa_proceso_maquila', 'P') IS NOT NULL
    DROP PROCEDURE dbo.sp_frupa_proceso_maquila;
GO

CREATE PROCEDURE dbo.sp_frupa_proceso_maquila
    @FechaIni  DATE = NULL,
    @FechaFin  DATE = NULL,
    @temporada CHAR(2) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @empresa CHAR(2) = '00';
    DECLARE @temporadas TABLE (c_codigo_tem CHAR(2) PRIMARY KEY);

    IF @temporada IS NOT NULL
        INSERT INTO @temporadas VALUES (@temporada);
    ELSE IF @FechaIni IS NULL AND @FechaFin IS NULL
        INSERT INTO @temporadas
        SELECT TOP 1 c_codigo_tem FROM dbo.t_temporada WITH (NOLOCK) WHERE c_activo_tem = '1' ORDER BY c_codigo_tem DESC;
    ELSE
        INSERT INTO @temporadas
        SELECT DISTINCT c_codigo_tem FROM dbo.t_seleccion WITH (NOLOCK)
        WHERE  (@FechaIni IS NULL OR d_fecha_sel >= @FechaIni) AND (@FechaFin IS NULL OR d_fecha_sel < DATEADD(DAY, 1, @FechaFin));

    WITH Pal AS (
        SELECT  pal.c_codigo_tem, pal.c_codigo_sel, pal.c_codigo_pro, pal.c_codigo_eti, pal.c_codigo_env,
                n_bulxpa_pal = SUM(pal.n_bulxpa_pal)
        FROM    dbo.t_palet pal WITH (NOLOCK)
        WHERE   pal.c_codigo_tem IN (SELECT c_codigo_tem FROM @temporadas) AND pal.c_codigo_emp = @empresa
        GROUP BY pal.c_codigo_tem, pal.c_codigo_sel, pal.c_codigo_pro, pal.c_codigo_eti, pal.c_codigo_env
    ),
    Cant AS (
        SELECT  red.c_codigo_tem, red.c_codigo_sel,
                Kilos = SUM(ISNULL(red.n_kilos_red, 0.0)),
                Cajas = SUM(ISNULL(red.n_cajascorte_red, 0))
        FROM    dbo.t_recepciondet red WITH (NOLOCK)
        WHERE   red.c_codigo_tem IN (SELECT c_codigo_tem FROM @temporadas)
        GROUP BY red.c_codigo_tem, red.c_codigo_sel
    ),
    Est AS (
        SELECT  sel.c_codigo_tem, sel.c_codigo_sel,
                fecha    = CAST(sel.d_fecha_sel AS DATE),
                lote     = RTRIM(lot.c_codigo_lot) + ' ' + lot.v_nombre_lot,
                huerta   = hue.v_nombre_hue,
                dueno    = CASE WHEN ISNULL(dno.v_pagara_dno, '') = '' THEN dno.v_nombre_dno ELSE dno.v_pagara_dno END,
                cultivo  = cul.v_nombre_cul,
                variedad = vari.v_nombre_var,
                kilos_recibidos = Cant.Kilos,
                cajas_recibidas = Cant.Cajas,
                resumen  = sel.c_codigo_sel
                           + ' | ' + FORMAT(Cant.Kilos / NULLIF(Cant.Cajas, 0), 'N2', 'en-US') + ' kg/caja'
                           + ' | ' + FORMAT(Cant.Cajas, 'N0', 'en-US') + ' cajas'
                           + ' | ' + FORMAT(Cant.Kilos, 'N2', 'en-US') + ' kg'
        FROM    dbo.t_seleccion sel WITH (NOLOCK)
                INNER JOIN Cant ON Cant.c_codigo_sel = sel.c_codigo_sel AND Cant.c_codigo_tem = sel.c_codigo_tem
                INNER JOIN dbo.t_lote lot WITH (NOLOCK) ON lot.c_codigo_lot = sel.c_codigo_lot AND lot.c_codigo_tem = sel.c_codigo_tem
                INNER JOIN dbo.t_cultivo cul WITH (NOLOCK) ON cul.c_codigo_cul = lot.c_codigo_cul
                INNER JOIN dbo.cosvariedad vari WITH (NOLOCK) ON vari.c_codigo_var = lot.c_codigo_var
                LEFT  JOIN dbo.t_huerto hue WITH (NOLOCK) ON hue.c_codigo_hue = lot.c_codigo_hue
                LEFT  JOIN dbo.t_duenio dno WITH (NOLOCK) ON dno.c_codigo_dno = hue.c_codigo_dno
        WHERE   sel.c_codigo_tem IN (SELECT c_codigo_tem FROM @temporadas)
                AND (@FechaIni IS NULL OR sel.d_fecha_sel >= @FechaIni)
                AND (@FechaFin IS NULL OR sel.d_fecha_sel < DATEADD(DAY, 1, @FechaFin))
    ),
    Det AS (
        SELECT  Est.c_codigo_tem, Est.c_codigo_sel,
                -- Envase 03 (KILOGRAMOS / bins) = mermas y subproductos; lo demás es empaque
                tipo         = CASE WHEN Pal.c_codigo_env = '03' THEN 'Mermas y subproductos' ELSE 'Empaque' END,
                presentacion = CASE WHEN Pal.c_codigo_env = '03'                                           THEN tam.v_nombre_tam
                                    WHEN ISNULL(cal.v_nombre_prc, tam.v_nombre_tam) LIKE 'CHAROLA SELECTA%'  THEN 'Selecta charola'
                                    WHEN ISNULL(cal.v_nombre_prc, tam.v_nombre_tam) LIKE 'CHAROLA COMERCIAL%' THEN 'Comercial charola'
                                    WHEN ISNULL(cal.v_nombre_prc, tam.v_nombre_tam) LIKE 'BOLSA%'             THEN 'Bolsa'
                                    ELSE ISNULL(cal.v_nombre_prc, tam.v_nombre_tam) END,
                calidad  = ISNULL(cal.v_nombre_prc, tam.v_nombre_tam),
                envase   = env.v_nombre_env,
                etiqueta = RTRIM(eti.v_nombre_eti),
                tamano   = tam.v_nombre_tam,
                producto = pro.v_nombre_pro,
                cajas    = Pal.n_bulxpa_pal,
                kilos    = pro.n_pesbul_pro * Pal.n_bulxpa_pal,  -- peso promedio del producto
                -- Lo recibido solo en el primer renglón de la estiba
                primero  = ROW_NUMBER() OVER (PARTITION BY Est.c_codigo_tem, Est.c_codigo_sel ORDER BY Pal.c_codigo_env, pro.c_codigo_pro, Pal.c_codigo_eti)
        FROM    Pal
                INNER JOIN Est ON Est.c_codigo_sel = Pal.c_codigo_sel AND Est.c_codigo_tem = Pal.c_codigo_tem
                INNER JOIN dbo.t_producto pro WITH (NOLOCK) ON pro.c_codigo_pro = Pal.c_codigo_pro
                LEFT  JOIN dbo.t_producto_calidad cal WITH (NOLOCK) ON cal.c_codigo_prc = pro.c_codigo_prc
                INNER JOIN dbo.t_tamanio tam WITH (NOLOCK) ON tam.c_codigo_tam = pro.c_codigo_tam
                INNER JOIN dbo.t_etiqueta eti WITH (NOLOCK) ON eti.c_codigo_eti = Pal.c_codigo_eti
                INNER JOIN dbo.t_envase env WITH (NOLOCK) ON env.c_codigo_env = Pal.c_codigo_env
    )
    SELECT  temporada = Est.c_codigo_tem, estiba = Est.c_codigo_sel, Est.fecha, Est.lote, Est.huerta, Est.dueno,
            Est.cultivo, Est.variedad, Est.resumen, Det.tipo, Det.presentacion, Det.calidad, Det.envase, Det.etiqueta,
            Det.tamano, Det.producto, Det.cajas, Det.kilos,
            kilos_recibidos = CASE WHEN Det.primero = 1 THEN Est.kilos_recibidos ELSE 0 END,
            cajas_recibidas = CASE WHEN Det.primero = 1 THEN Est.cajas_recibidas ELSE 0 END
    FROM    Det
            INNER JOIN Est ON Est.c_codigo_sel = Det.c_codigo_sel AND Est.c_codigo_tem = Det.c_codigo_tem
    ORDER BY Est.c_codigo_tem, Est.c_codigo_sel, Det.tipo, Det.presentacion, Det.tamano;
END
GO
