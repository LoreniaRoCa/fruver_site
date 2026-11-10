/*
  Vistas en la aplicación Fruverpack (base FruverManzana): consultas de listado (GridView), no tablas dinámicas.
  Misma funcionalidad que en Sistema Fruver (frmgridviewDS + frmGridFormatos).

  - gridPrincipal: una fila por vista (gr_v_plantilla_con = s_reporte_mnu del menú):
      gr_v_script   lo que se ejecuta, con @FechaIni / @FechaFin y los filtros de lista (@<caption sin espacios>)
      gr_v_bd       'Inventum' = base fruverpack (ConexionEyePlus); cualquier otro valor = FruverManzana
      gr_b_fecha1/2 pide fecha inicial / final;  gr_b_list/2 + caption + script + tipo: listas de filtro
      gr_b_consultar_ini  consulta al abrir;  gr_v_xml  formato base (layout del GridView)
  - gridFormatos: formatos que cada usuario guarda de una vista (botón Agregar / Guardar).
  - Módulo "Vistas" en el menú, con la vista Pallets (dbo.sp_frupa_pallets en la base fruverpack).

  Para agregar otra vista: una fila en gridPrincipal y otra en Menu (módulo Vistas, s_forma_mnu = 'frmgridviewDS',
  s_reporte_mnu = gr_v_plantilla_con). Antes: crear dbo.sp_frupa_pallets en la base fruverpack.
*/
USE FruverManzana;
GO

IF OBJECT_ID('dbo.gridPrincipal', 'U') IS NULL
CREATE TABLE [dbo].[gridPrincipal](
	[gr_v_plantilla_con] [varchar](150) NOT NULL,
	[gr_v_xml] [xml] NULL,
	[gr_v_bd] [varchar](50) NULL,
	[gr_v_script] [varchar](max) NULL,
	[gr_b_fecha1] [bit] NULL,
	[gr_b_fecha2] [bit] NULL,
	[gr_b_list] [bit] NULL,
	[gr_v_list_caption] [varchar](50) NULL,
	[gr_v_list_script] [varchar](max) NULL,
	[gr_n_list_tipo] [smallint] NULL,
	[gr_b_list2] [bit] NULL,
	[gr_v_list2_caption] [varchar](50) NULL,
	[gr_v_list2_script] [varchar](max) NULL,
	[gr_n_list2_tipo] [smallint] NULL,
	[gr_b_consultar_ini] [bit] NULL,
 CONSTRAINT [IX_gridPrincipal] PRIMARY KEY CLUSTERED ([gr_v_plantilla_con] ASC)
) ON [PRIMARY] TEXTIMAGE_ON [PRIMARY];
GO

IF OBJECT_ID('dbo.gridFormatos', 'U') IS NULL
CREATE TABLE [dbo].[gridFormatos](
	[gr_v_usuario_con] [varchar](20) NOT NULL,
	[gr_v_plantilla_con] [varchar](150) NOT NULL,
	[gr_v_nombre_con] [varchar](150) NOT NULL,
	[gr_b_default] [bit] NULL,
	[gr_v_xml] [xml] NULL,
 CONSTRAINT [IX_gridFormatos] PRIMARY KEY CLUSTERED ([gr_v_usuario_con] ASC, [gr_v_plantilla_con] ASC, [gr_v_nombre_con] ASC)
) ON [PRIMARY] TEXTIMAGE_ON [PRIMARY];
GO

IF NOT EXISTS (SELECT 1 FROM dbo.gridPrincipal WHERE gr_v_plantilla_con = 'PALLETS')
    INSERT INTO dbo.gridPrincipal (gr_v_plantilla_con, gr_v_xml, gr_v_bd, gr_v_script, gr_b_fecha1, gr_b_fecha2, gr_b_list,
                                   gr_v_list_caption, gr_v_list_script, gr_n_list_tipo, gr_b_list2, gr_v_list2_caption,
                                   gr_v_list2_script, gr_n_list2_tipo, gr_b_consultar_ini)
    VALUES ('PALLETS', N'<XtraSerializer version="1.0" application="View">
  <property name="#LayoutVersion" />
  <property name="#LayoutScaleFactor">@1,Width=1@1,Height=1</property>
  <property name="OptionsBehavior" isnull="true" iskey="true">
    <property name="Editable">false</property>
  </property>
  <property name="OptionsView" isnull="true" iskey="true">
    <property name="ColumnAutoWidth">false</property>
    <property name="ShowAutoFilterRow">true</property>
    <property name="ShowFooter">true</property>
  </property>
  <property name="FixedLineWidth">2</property>
  <property name="IndicatorWidth">-1</property>
  <property name="ColumnPanelRowHeight">-1</property>
  <property name="RowSeparatorHeight">0</property>
  <property name="FooterPanelHeight">-1</property>
  <property name="HorzScrollVisibility">Auto</property>
  <property name="VertScrollVisibility">Auto</property>
  <property name="RowHeight">-1</property>
  <property name="GroupRowHeight">-1</property>
  <property name="GroupFormat">{0}: [#image]{1} {2}</property>
  <property name="ChildGridLevelName" />
  <property name="VertScrollTipFieldName" />
  <property name="PreviewFieldName" />
  <property name="GroupPanelText" />
  <property name="NewItemRowText" />
  <property name="LevelIndent">-1</property>
  <property name="PreviewIndent">-1</property>
  <property name="PreviewLineCount">-1</property>
  <property name="ScrollStyle">LiveVertScroll, LiveHorzScroll</property>
  <property name="FocusRectStyle">CellFocus</property>
  <property name="HorzScrollStep">0</property>
  <property name="ActiveFilterEnabled">true</property>
  <property name="ViewCaptionHeight">-1</property>
  <property name="Columns" iskey="true" value="12">
    <property name="Item1" isnull="true" iskey="true">
      <property name="Name">colpallet</property>
      <property name="Caption">Pallet</property>
      <property name="ImageAlignment">Near</property>
      <property name="ImageIndex">-1</property>
      <property name="FieldName">pallet</property>
      <property name="ColumnEditName" />
      <property name="VisibleIndex">0</property>
      <property name="Visible">true</property>
      <property name="Width">120</property>
      <property name="MinWidth">15</property>
      <property name="MaxWidth">0</property>
      <property name="UnboundDataTypeName" />
      <property name="Summary" iskey="true" value="1">
        <property name="Item1" isnull="true" iskey="true">
          <property name="Tag" isnull="true" />
          <property name="FieldName">pallet</property>
          <property name="SummaryType">Count</property>
          <property name="Mode">AllRows</property>
          <property name="DisplayFormat">Renglones: {0:n0}</property>
        </property>
      </property>
    </property>
    <property name="Item2" isnull="true" iskey="true">
      <property name="Name">colseccion</property>
      <property name="Caption">Sección</property>
      <property name="ImageAlignment">Near</property>
      <property name="ImageIndex">-1</property>
      <property name="FieldName">seccion</property>
      <property name="ColumnEditName" />
      <property name="VisibleIndex">1</property>
      <property name="Visible">true</property>
      <property name="Width">55</property>
      <property name="MinWidth">15</property>
      <property name="MaxWidth">0</property>
      <property name="UnboundDataTypeName" />
    </property>
    <property name="Item3" isnull="true" iskey="true">
      <property name="Name">colfecha</property>
      <property name="Caption">Fecha empaque</property>
      <property name="ImageAlignment">Near</property>
      <property name="ImageIndex">-1</property>
      <property name="FieldName">fecha</property>
      <property name="ColumnEditName" />
      <property name="VisibleIndex">2</property>
      <property name="Visible">true</property>
      <property name="Width">85</property>
      <property name="DisplayFormat" isnull="true" iskey="true">
        <property name="FormatString">d</property>
        <property name="FormatType">DateTime</property>
      </property>
      <property name="MinWidth">15</property>
      <property name="MaxWidth">0</property>
      <property name="UnboundDataTypeName" />
    </property>
    <property name="Item4" isnull="true" iskey="true">
      <property name="Name">colhora</property>
      <property name="Caption">Hora</property>
      <property name="ImageAlignment">Near</property>
      <property name="ImageIndex">-1</property>
      <property name="FieldName">hora</property>
      <property name="ColumnEditName" />
      <property name="VisibleIndex">3</property>
      <property name="Visible">true</property>
      <property name="Width">65</property>
      <property name="MinWidth">15</property>
      <property name="MaxWidth">0</property>
      <property name="UnboundDataTypeName" />
    </property>
    <property name="Item5" isnull="true" iskey="true">
      <property name="Name">collote</property>
      <property name="Caption">Lote</property>
      <property name="ImageAlignment">Near</property>
      <property name="ImageIndex">-1</property>
      <property name="FieldName">lote</property>
      <property name="ColumnEditName" />
      <property name="VisibleIndex">4</property>
      <property name="Visible">true</property>
      <property name="Width">50</property>
      <property name="MinWidth">15</property>
      <property name="MaxWidth">0</property>
      <property name="UnboundDataTypeName" />
    </property>
    <property name="Item6" isnull="true" iskey="true">
      <property name="Name">colnombre_lote</property>
      <property name="Caption">Nombre del lote</property>
      <property name="ImageAlignment">Near</property>
      <property name="ImageIndex">-1</property>
      <property name="FieldName">nombre_lote</property>
      <property name="ColumnEditName" />
      <property name="VisibleIndex">5</property>
      <property name="Visible">true</property>
      <property name="Width">260</property>
      <property name="MinWidth">15</property>
      <property name="MaxWidth">0</property>
      <property name="UnboundDataTypeName" />
    </property>
    <property name="Item7" isnull="true" iskey="true">
      <property name="Name">colmanifiesto</property>
      <property name="Caption">Manifiesto</property>
      <property name="ImageAlignment">Near</property>
      <property name="ImageIndex">-1</property>
      <property name="FieldName">manifiesto</property>
      <property name="ColumnEditName" />
      <property name="VisibleIndex">6</property>
      <property name="Visible">true</property>
      <property name="Width">80</property>
      <property name="MinWidth">15</property>
      <property name="MaxWidth">0</property>
      <property name="UnboundDataTypeName" />
    </property>
    <property name="Item8" isnull="true" iskey="true">
      <property name="Name">colestiba</property>
      <property name="Caption">Estiba</property>
      <property name="ImageAlignment">Near</property>
      <property name="ImageIndex">-1</property>
      <property name="FieldName">estiba</property>
      <property name="ColumnEditName" />
      <property name="VisibleIndex">7</property>
      <property name="Visible">true</property>
      <property name="Width">70</property>
      <property name="MinWidth">15</property>
      <property name="MaxWidth">0</property>
      <property name="UnboundDataTypeName" />
    </property>
    <property name="Item9" isnull="true" iskey="true">
      <property name="Name">colseleccion</property>
      <property name="Caption">Selección</property>
      <property name="ImageAlignment">Near</property>
      <property name="ImageIndex">-1</property>
      <property name="FieldName">seleccion</property>
      <property name="ColumnEditName" />
      <property name="VisibleIndex">8</property>
      <property name="Visible">true</property>
      <property name="Width">85</property>
      <property name="MinWidth">15</property>
      <property name="MaxWidth">0</property>
      <property name="UnboundDataTypeName" />
    </property>
    <property name="Item10" isnull="true" iskey="true">
      <property name="Name">coletiqueta</property>
      <property name="Caption">Etiqueta</property>
      <property name="ImageAlignment">Near</property>
      <property name="ImageIndex">-1</property>
      <property name="FieldName">etiqueta</property>
      <property name="ColumnEditName" />
      <property name="VisibleIndex">9</property>
      <property name="Visible">true</property>
      <property name="Width">130</property>
      <property name="MinWidth">15</property>
      <property name="MaxWidth">0</property>
      <property name="UnboundDataTypeName" />
    </property>
    <property name="Item11" isnull="true" iskey="true">
      <property name="Name">colproducto</property>
      <property name="Caption">Producto</property>
      <property name="ImageAlignment">Near</property>
      <property name="ImageIndex">-1</property>
      <property name="FieldName">producto</property>
      <property name="ColumnEditName" />
      <property name="VisibleIndex">10</property>
      <property name="Visible">true</property>
      <property name="Width">170</property>
      <property name="MinWidth">15</property>
      <property name="MaxWidth">0</property>
      <property name="UnboundDataTypeName" />
    </property>
    <property name="Item12" isnull="true" iskey="true">
      <property name="Name">colcajas</property>
      <property name="Caption">Cajas</property>
      <property name="ImageAlignment">Near</property>
      <property name="ImageIndex">-1</property>
      <property name="FieldName">cajas</property>
      <property name="ColumnEditName" />
      <property name="VisibleIndex">11</property>
      <property name="Visible">true</property>
      <property name="Width">70</property>
      <property name="DisplayFormat" isnull="true" iskey="true">
        <property name="FormatString">n0</property>
        <property name="FormatType">Numeric</property>
      </property>
      <property name="MinWidth">15</property>
      <property name="MaxWidth">0</property>
      <property name="UnboundDataTypeName" />
      <property name="Summary" iskey="true" value="1">
        <property name="Item1" isnull="true" iskey="true">
          <property name="Tag" isnull="true" />
          <property name="FieldName">cajas</property>
          <property name="SummaryType">Sum</property>
          <property name="Mode">AllRows</property>
          <property name="DisplayFormat">{0:n0}</property>
        </property>
      </property>
    </property>
  </property>
  <property name="ViewCaption" />
  <property name="BorderStyle">Default</property>
  <property name="SynchronizeClones">true</property>
  <property name="DetailTabHeaderLocation">Top</property>
  <property name="Name" />
  <property name="DetailHeight">350</property>
  <property name="Tag" isnull="true" />
  <property name="GroupSummary" iskey="true" value="0" />
  <property name="ActiveFilterString" />
  <property name="FormatRules" iskey="true" value="0" />
  <property name="SortInfoState" iskey="true" value="1">
    <property name="Item1" isnull="true" iskey="true">
      <property name="Orders">Descending</property>
      <property name="Columns">colfecha</property>
    </property>
    <property name="Content" isnull="true" iskey="true">
      <property name="GroupCount">0</property>
    </property>
  </property>
  <property name="FormatConditions" iskey="true" value="0" />
  <property name="GroupSummarySortInfoState" />
  <property name="FindFilterText" />
  <property name="FindPanelVisible">false</property>
</XtraSerializer>', 'Inventum', 'exec dbo.sp_frupa_pallets @FechaIni, @FechaFin',
            1, 1, 0, NULL, NULL, NULL, 0, NULL, NULL, NULL, 1);
GO

-- Módulo "Vistas" y la opción Pallets
IF NOT EXISTS (SELECT 1 FROM dbo.Modulo WHERE s_nombre_mod = 'Vistas')
    INSERT INTO dbo.Modulo (n_clave_mod, s_nombre_mod) SELECT ISNULL(MAX(n_clave_mod), 0) + 1, 'Vistas' FROM dbo.Modulo;
GO

IF NOT EXISTS (SELECT 1 FROM dbo.Menu WHERE s_forma_mnu = 'frmgridviewDS' AND s_reporte_mnu = 'PALLETS')
    INSERT INTO dbo.Menu (n_clave_mod, n_clave_mnu, s_nombre_mnu, s_forma_mnu, s_tipo_mnu, s_tipoforma_mnu, s_reporte_mnu)
    SELECT mdl.n_clave_mod, ISNULL((SELECT MAX(n_clave_mnu) FROM dbo.Menu WHERE n_clave_mod = mdl.n_clave_mod), 0) + 1,
           'Pallets', 'frmgridviewDS', '1', 1, 'PALLETS'
    FROM   dbo.Modulo mdl WHERE mdl.s_nombre_mod = 'Vistas';
GO

-- Acceso: los mismos usuarios que tienen "Abrir Proceso"; agrega o quita usuarios en Usuario_Menu
INSERT INTO dbo.Usuario_Menu (n_clave_mod, n_clave_mnu, s_clave_inv)
SELECT  mnu.n_clave_mod, mnu.n_clave_mnu, um.s_clave_inv
FROM    dbo.Usuario_Menu um
        INNER JOIN dbo.Menu mnu ON mnu.s_forma_mnu = 'frmgridviewDS' AND mnu.s_reporte_mnu = 'PALLETS'
WHERE   um.n_clave_mod = 1 AND um.n_clave_mnu = 2
        AND NOT EXISTS (SELECT 1 FROM dbo.Usuario_Menu x
                        WHERE x.n_clave_mod = mnu.n_clave_mod AND x.n_clave_mnu = mnu.n_clave_mnu AND x.s_clave_inv = um.s_clave_inv);
GO
