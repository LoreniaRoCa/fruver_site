/*
  Vista "Proceso de maquila" en la aplicación Fruverpack (base FruverManzana), módulo Vistas.

  Lista los renglones de dbo.sp_frupa_proceso_maquila (base fruverpack): por estiba, lo que salió del empaque y de
  mermas, con lo recibido (kilos y pallets) solo en el primer renglón de cada estiba para que los totales no dupliquen.
  Formato base: estiba, fecha, dueño, lote, huerta, variedad, tipo, presentación, tamaño, etiqueta, producto, cajas,
  kilos y lo recibido, con totales; en el selector de columnas quedan Resumen proceso, Calidad, Envase, Cultivo y
  Temporada.

  Antes: sql/fruverpack_vistas.sql (tablas y módulo Vistas) en FruverManzana y dbo.sp_frupa_proceso_maquila en fruverpack.
*/
USE FruverManzana;
GO

IF NOT EXISTS (SELECT 1 FROM dbo.gridPrincipal WHERE gr_v_plantilla_con = 'PROCESO DE MAQUILA')
    INSERT INTO dbo.gridPrincipal (gr_v_plantilla_con, gr_v_xml, gr_v_bd, gr_v_script, gr_b_fecha1, gr_b_fecha2, gr_b_list,
                                   gr_v_list_caption, gr_v_list_script, gr_n_list_tipo, gr_b_list2, gr_v_list2_caption,
                                   gr_v_list2_script, gr_n_list2_tipo, gr_b_consultar_ini)
    VALUES ('PROCESO DE MAQUILA', N'<XtraSerializer version="1.0" application="View">
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
  <property name="Columns" iskey="true" value="20">
    <property name="Item1" isnull="true" iskey="true">
      <property name="Name">colestiba</property>
      <property name="Caption">Estiba</property>
      <property name="ImageAlignment">Near</property>
      <property name="ImageIndex">-1</property>
      <property name="FieldName">estiba</property>
      <property name="ColumnEditName" />
      <property name="VisibleIndex">0</property>
      <property name="Visible">true</property>
      <property name="Width">110</property>
      <property name="MinWidth">15</property>
      <property name="MaxWidth">0</property>
      <property name="UnboundDataTypeName" />
      <property name="Summary" iskey="true" value="1">
        <property name="Item1" isnull="true" iskey="true">
          <property name="Tag" isnull="true" />
          <property name="FieldName">estiba</property>
          <property name="SummaryType">Count</property>
          <property name="Mode">AllRows</property>
          <property name="DisplayFormat">Renglones: {0:n0}</property>
        </property>
      </property>
    </property>
    <property name="Item2" isnull="true" iskey="true">
      <property name="Name">colfecha</property>
      <property name="Caption">Fecha</property>
      <property name="ImageAlignment">Near</property>
      <property name="ImageIndex">-1</property>
      <property name="FieldName">fecha</property>
      <property name="ColumnEditName" />
      <property name="VisibleIndex">1</property>
      <property name="Visible">true</property>
      <property name="Width">80</property>
      <property name="DisplayFormat" isnull="true" iskey="true">
        <property name="FormatString">d</property>
        <property name="FormatType">DateTime</property>
      </property>
      <property name="MinWidth">15</property>
      <property name="MaxWidth">0</property>
      <property name="UnboundDataTypeName" />
    </property>
    <property name="Item3" isnull="true" iskey="true">
      <property name="Name">coldueno</property>
      <property name="Caption">Dueño</property>
      <property name="ImageAlignment">Near</property>
      <property name="ImageIndex">-1</property>
      <property name="FieldName">dueno</property>
      <property name="ColumnEditName" />
      <property name="VisibleIndex">2</property>
      <property name="Visible">true</property>
      <property name="Width">220</property>
      <property name="MinWidth">15</property>
      <property name="MaxWidth">0</property>
      <property name="UnboundDataTypeName" />
    </property>
    <property name="Item4" isnull="true" iskey="true">
      <property name="Name">collote</property>
      <property name="Caption">Lote</property>
      <property name="ImageAlignment">Near</property>
      <property name="ImageIndex">-1</property>
      <property name="FieldName">lote</property>
      <property name="ColumnEditName" />
      <property name="VisibleIndex">3</property>
      <property name="Visible">true</property>
      <property name="Width">240</property>
      <property name="MinWidth">15</property>
      <property name="MaxWidth">0</property>
      <property name="UnboundDataTypeName" />
    </property>
    <property name="Item5" isnull="true" iskey="true">
      <property name="Name">colhuerta</property>
      <property name="Caption">Huerta</property>
      <property name="ImageAlignment">Near</property>
      <property name="ImageIndex">-1</property>
      <property name="FieldName">huerta</property>
      <property name="ColumnEditName" />
      <property name="VisibleIndex">4</property>
      <property name="Visible">true</property>
      <property name="Width">220</property>
      <property name="MinWidth">15</property>
      <property name="MaxWidth">0</property>
      <property name="UnboundDataTypeName" />
    </property>
    <property name="Item6" isnull="true" iskey="true">
      <property name="Name">colvariedad</property>
      <property name="Caption">Variedad</property>
      <property name="ImageAlignment">Near</property>
      <property name="ImageIndex">-1</property>
      <property name="FieldName">variedad</property>
      <property name="ColumnEditName" />
      <property name="VisibleIndex">5</property>
      <property name="Visible">true</property>
      <property name="Width">120</property>
      <property name="MinWidth">15</property>
      <property name="MaxWidth">0</property>
      <property name="UnboundDataTypeName" />
    </property>
    <property name="Item7" isnull="true" iskey="true">
      <property name="Name">coltipo</property>
      <property name="Caption">Tipo</property>
      <property name="ImageAlignment">Near</property>
      <property name="ImageIndex">-1</property>
      <property name="FieldName">tipo</property>
      <property name="ColumnEditName" />
      <property name="VisibleIndex">6</property>
      <property name="Visible">true</property>
      <property name="Width">140</property>
      <property name="MinWidth">15</property>
      <property name="MaxWidth">0</property>
      <property name="UnboundDataTypeName" />
    </property>
    <property name="Item8" isnull="true" iskey="true">
      <property name="Name">colpresentacion</property>
      <property name="Caption">Presentación</property>
      <property name="ImageAlignment">Near</property>
      <property name="ImageIndex">-1</property>
      <property name="FieldName">presentacion</property>
      <property name="ColumnEditName" />
      <property name="VisibleIndex">7</property>
      <property name="Visible">true</property>
      <property name="Width">140</property>
      <property name="MinWidth">15</property>
      <property name="MaxWidth">0</property>
      <property name="UnboundDataTypeName" />
    </property>
    <property name="Item9" isnull="true" iskey="true">
      <property name="Name">coltamano</property>
      <property name="Caption">Tamaño</property>
      <property name="ImageAlignment">Near</property>
      <property name="ImageIndex">-1</property>
      <property name="FieldName">tamano</property>
      <property name="ColumnEditName" />
      <property name="VisibleIndex">8</property>
      <property name="Visible">true</property>
      <property name="Width">70</property>
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
      <property name="Width">120</property>
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
      <property name="Width">140</property>
      <property name="MinWidth">15</property>
      <property name="MaxWidth">0</property>
      <property name="UnboundDataTypeName" />
    </property>
    <property name="Item12" isnull="true" iskey="true">
      <property name="Name">colcajas</property>
      <property name="Caption">Cajas / bultos</property>
      <property name="ImageAlignment">Near</property>
      <property name="ImageIndex">-1</property>
      <property name="FieldName">cajas</property>
      <property name="ColumnEditName" />
      <property name="VisibleIndex">11</property>
      <property name="Visible">true</property>
      <property name="Width">85</property>
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
    <property name="Item13" isnull="true" iskey="true">
      <property name="Name">colkilos</property>
      <property name="Caption">Kilos</property>
      <property name="ImageAlignment">Near</property>
      <property name="ImageIndex">-1</property>
      <property name="FieldName">kilos</property>
      <property name="ColumnEditName" />
      <property name="VisibleIndex">12</property>
      <property name="Visible">true</property>
      <property name="Width">95</property>
      <property name="DisplayFormat" isnull="true" iskey="true">
        <property name="FormatString">n2</property>
        <property name="FormatType">Numeric</property>
      </property>
      <property name="MinWidth">15</property>
      <property name="MaxWidth">0</property>
      <property name="UnboundDataTypeName" />
      <property name="Summary" iskey="true" value="1">
        <property name="Item1" isnull="true" iskey="true">
          <property name="Tag" isnull="true" />
          <property name="FieldName">kilos</property>
          <property name="SummaryType">Sum</property>
          <property name="Mode">AllRows</property>
          <property name="DisplayFormat">{0:n2}</property>
        </property>
      </property>
    </property>
    <property name="Item14" isnull="true" iskey="true">
      <property name="Name">colkilos_recibidos</property>
      <property name="Caption">Kilos recibidos</property>
      <property name="ImageAlignment">Near</property>
      <property name="ImageIndex">-1</property>
      <property name="FieldName">kilos_recibidos</property>
      <property name="ColumnEditName" />
      <property name="VisibleIndex">13</property>
      <property name="Visible">true</property>
      <property name="Width">100</property>
      <property name="DisplayFormat" isnull="true" iskey="true">
        <property name="FormatString">n2</property>
        <property name="FormatType">Numeric</property>
      </property>
      <property name="MinWidth">15</property>
      <property name="MaxWidth">0</property>
      <property name="UnboundDataTypeName" />
      <property name="Summary" iskey="true" value="1">
        <property name="Item1" isnull="true" iskey="true">
          <property name="Tag" isnull="true" />
          <property name="FieldName">kilos_recibidos</property>
          <property name="SummaryType">Sum</property>
          <property name="Mode">AllRows</property>
          <property name="DisplayFormat">{0:n2}</property>
        </property>
      </property>
    </property>
    <property name="Item15" isnull="true" iskey="true">
      <property name="Name">colcajas_recibidas</property>
      <property name="Caption">Pallets recibidos</property>
      <property name="ImageAlignment">Near</property>
      <property name="ImageIndex">-1</property>
      <property name="FieldName">cajas_recibidas</property>
      <property name="ColumnEditName" />
      <property name="VisibleIndex">14</property>
      <property name="Visible">true</property>
      <property name="Width">90</property>
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
          <property name="FieldName">cajas_recibidas</property>
          <property name="SummaryType">Sum</property>
          <property name="Mode">AllRows</property>
          <property name="DisplayFormat">{0:n0}</property>
        </property>
      </property>
    </property>
    <property name="Item16" isnull="true" iskey="true">
      <property name="Name">colresumen</property>
      <property name="Caption">Resumen proceso</property>
      <property name="ImageAlignment">Near</property>
      <property name="ImageIndex">-1</property>
      <property name="FieldName">resumen</property>
      <property name="ColumnEditName" />
      <property name="Width">330</property>
      <property name="MinWidth">15</property>
      <property name="MaxWidth">0</property>
      <property name="UnboundDataTypeName" />
    </property>
    <property name="Item17" isnull="true" iskey="true">
      <property name="Name">colcalidad</property>
      <property name="Caption">Calidad</property>
      <property name="ImageAlignment">Near</property>
      <property name="ImageIndex">-1</property>
      <property name="FieldName">calidad</property>
      <property name="ColumnEditName" />
      <property name="Width">160</property>
      <property name="MinWidth">15</property>
      <property name="MaxWidth">0</property>
      <property name="UnboundDataTypeName" />
    </property>
    <property name="Item18" isnull="true" iskey="true">
      <property name="Name">colenvase</property>
      <property name="Caption">Envase</property>
      <property name="ImageAlignment">Near</property>
      <property name="ImageIndex">-1</property>
      <property name="FieldName">envase</property>
      <property name="ColumnEditName" />
      <property name="Width">120</property>
      <property name="MinWidth">15</property>
      <property name="MaxWidth">0</property>
      <property name="UnboundDataTypeName" />
    </property>
    <property name="Item19" isnull="true" iskey="true">
      <property name="Name">colcultivo</property>
      <property name="Caption">Cultivo</property>
      <property name="ImageAlignment">Near</property>
      <property name="ImageIndex">-1</property>
      <property name="FieldName">cultivo</property>
      <property name="ColumnEditName" />
      <property name="Width">140</property>
      <property name="MinWidth">15</property>
      <property name="MaxWidth">0</property>
      <property name="UnboundDataTypeName" />
    </property>
    <property name="Item20" isnull="true" iskey="true">
      <property name="Name">coltemporada</property>
      <property name="Caption">Temporada</property>
      <property name="ImageAlignment">Near</property>
      <property name="ImageIndex">-1</property>
      <property name="FieldName">temporada</property>
      <property name="ColumnEditName" />
      <property name="Width">70</property>
      <property name="MinWidth">15</property>
      <property name="MaxWidth">0</property>
      <property name="UnboundDataTypeName" />
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
      <property name="Orders">Ascending</property>
      <property name="Columns">colestiba</property>
    </property>
    <property name="Content" isnull="true" iskey="true">
      <property name="GroupCount">0</property>
    </property>
  </property>
  <property name="FormatConditions" iskey="true" value="0" />
  <property name="GroupSummarySortInfoState" />
  <property name="FindFilterText" />
  <property name="FindPanelVisible">false</property>
</XtraSerializer>', 'Inventum', 'exec dbo.sp_frupa_proceso_maquila @FechaIni, @FechaFin',
            1, 1, 0, NULL, NULL, NULL, 0, NULL, NULL, NULL, 1);
GO

IF NOT EXISTS (SELECT 1 FROM dbo.Menu WHERE s_forma_mnu = 'frmgridviewDS' AND s_reporte_mnu = 'PROCESO DE MAQUILA')
    INSERT INTO dbo.Menu (n_clave_mod, n_clave_mnu, s_nombre_mnu, s_forma_mnu, s_tipo_mnu, s_tipoforma_mnu, s_reporte_mnu)
    SELECT mdl.n_clave_mod, ISNULL((SELECT MAX(n_clave_mnu) FROM dbo.Menu WHERE n_clave_mod = mdl.n_clave_mod), 0) + 1,
           'Proceso de maquila', 'frmgridviewDS', '1', 1, 'PROCESO DE MAQUILA'
    FROM   dbo.Modulo mdl WHERE mdl.s_nombre_mod = 'Vistas';
GO

-- Acceso: los mismos usuarios que tienen la vista Pallets
INSERT INTO dbo.Usuario_Menu (n_clave_mod, n_clave_mnu, s_clave_inv)
SELECT  nueva.n_clave_mod, nueva.n_clave_mnu, um.s_clave_inv
FROM    dbo.Usuario_Menu um
        INNER JOIN dbo.Menu pal ON pal.n_clave_mod = um.n_clave_mod AND pal.n_clave_mnu = um.n_clave_mnu
                               AND pal.s_forma_mnu = 'frmgridviewDS' AND pal.s_reporte_mnu = 'PALLETS'
        INNER JOIN dbo.Menu nueva ON nueva.s_forma_mnu = 'frmgridviewDS' AND nueva.s_reporte_mnu = 'PROCESO DE MAQUILA'
WHERE   NOT EXISTS (SELECT 1 FROM dbo.Usuario_Menu x
                    WHERE x.n_clave_mod = nueva.n_clave_mod AND x.n_clave_mnu = nueva.n_clave_mnu AND x.s_clave_inv = um.s_clave_inv);
GO
