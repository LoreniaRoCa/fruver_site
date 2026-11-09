/*
  Opción "Reportes en Excel" en el menú de la aplicación Fruverpack (base FruverManzana).

  Abre la página Reportes en Excel del portal (frmReportesExcel): ahí cada usuario genera su clave de Excel y
  descarga las plantillas (Inventario, Proceso de maquila, Cajas por empleado...).

  Va en el módulo 1 (Empaque): frmMain trata todo lo del módulo 2 como tabla dinámica (frmpivotDS).
  Se le da acceso a los mismos usuarios que tienen "Abrir Proceso"; agrega o quita usuarios en Usuario_Menu.
  La dirección del portal se puede cambiar en Fruverpack.exe.config (appSettings, clave UrlPortal).
*/
USE FruverManzana;
GO

IF NOT EXISTS (SELECT 1 FROM dbo.Menu WHERE s_forma_mnu = 'frmReportesExcel')
    INSERT INTO dbo.Menu (n_clave_mod, n_clave_mnu, s_nombre_mnu, s_forma_mnu, s_tipo_mnu, s_tipoforma_mnu, s_reporte_mnu)
    SELECT 1, ISNULL(MAX(n_clave_mnu), 0) + 1, 'Reportes en Excel', 'frmReportesExcel', '1', 1, NULL
    FROM   dbo.Menu WHERE n_clave_mod = 1;
GO

INSERT INTO dbo.Usuario_Menu (n_clave_mod, n_clave_mnu, s_clave_inv)
SELECT  um.n_clave_mod, mnu.n_clave_mnu, um.s_clave_inv
FROM    dbo.Usuario_Menu um
        INNER JOIN dbo.Menu mnu ON mnu.n_clave_mod = 1 AND mnu.s_forma_mnu = 'frmReportesExcel'
WHERE   um.n_clave_mod = 1 AND um.n_clave_mnu = 2   -- quienes tienen "Abrir Proceso"
        AND NOT EXISTS (SELECT 1 FROM dbo.Usuario_Menu x
                        WHERE x.n_clave_mod = 1 AND x.n_clave_mnu = mnu.n_clave_mnu AND x.s_clave_inv = um.s_clave_inv);
GO
