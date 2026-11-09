/*
  Tabla dinámica "Cajas por empleado" en la aplicación Fruverpack (base FruverManzana).

  - pivotPrincipal: formato base (empacadores en renglones, días en columnas y, por día y al final,
    Cajas, Charola y Bolsa), con el procedimiento dbo.sp_frupa_cajas_empleado de la base fruverpack.
    Fechas al abrir: del primer día del mes a hoy (MI-0 / M).
  - Menu: opción en Tablas Dinámicas (módulo 2), igual que Inventario.

  Antes: crear dbo.sp_frupa_cajas_empleado en la base fruverpack (sql/sp_frupa_cajas_empleado.sql).
  El formato se generó con el PivotGridControl de DevExpress 23.2 (SaveLayoutToStream).
*/
USE FruverManzana;
GO

IF NOT EXISTS (SELECT 1 FROM dbo.pivotPrincipal WHERE pv_v_palntilla_con = 'CAJAS POR EMPLEADO')
    INSERT INTO dbo.pivotPrincipal (pv_v_palntilla_con, pv_v_xml, pv_v_sp, pv_b_Ejercicio, pv_v_fechaini, pv_v_fechafin)
    VALUES ('CAJAS POR EMPLEADO', N'<XtraSerializer version="1.0" application="PivotGrid">
  <property name="#LayoutVersion" />
  <property name="#LayoutScaleFactor">@1,Width=1@1,Height=1</property>
  <property name="FixedColumnFieldValues" iskey="true" value="0" />
  <property name="Fields" iskey="true" value="10">
    <property name="Item1" isnull="true" iskey="true">
      <property name="Options" isnull="true" iskey="true">
        <property name="AllowRunTimeSummaryChange">true</property>
      </property>
      <property name="ImageIndex">-1</property>
      <property name="ToolTips" isnull="true" iskey="true">
        <property name="HeaderText" />
        <property name="ValueText" />
      </property>
      <property name="FieldEditName" />
      <property name="Name">fieldempleado</property>
      <property name="Area">RowArea</property>
      <property name="FieldName">empleado</property>
      <property name="Caption">Empacador</property>
      <property name="Index">0</property>
      <property name="AreaIndex">0</property>
      <property name="MinWidth">20</property>
      <property name="Width">260</property>
    </property>
    <property name="Item2" isnull="true" iskey="true">
      <property name="Options" isnull="true" iskey="true">
        <property name="AllowRunTimeSummaryChange">true</property>
      </property>
      <property name="ImageIndex">-1</property>
      <property name="ToolTips" isnull="true" iskey="true">
        <property name="HeaderText" />
        <property name="ValueText" />
      </property>
      <property name="FieldEditName" />
      <property name="Name">fieldfecha</property>
      <property name="Area">ColumnArea</property>
      <property name="GroupInterval">Date</property>
      <property name="FieldName">fecha</property>
      <property name="UnboundFieldName">fieldfecha</property>
      <property name="Caption">Día</property>
      <property name="ValueFormat" isnull="true" iskey="true">
        <property name="FormatString">dddd dd/MM</property>
        <property name="FormatType">DateTime</property>
      </property>
      <property name="Index">1</property>
      <property name="AreaIndex">0</property>
      <property name="MinWidth">20</property>
      <property name="Width">100</property>
    </property>
    <property name="Item3" isnull="true" iskey="true">
      <property name="Options" isnull="true" iskey="true">
        <property name="AllowRunTimeSummaryChange">true</property>
      </property>
      <property name="ImageIndex">-1</property>
      <property name="ToolTips" isnull="true" iskey="true">
        <property name="HeaderText" />
        <property name="ValueText" />
      </property>
      <property name="FieldEditName" />
      <property name="Name">fieldcajas</property>
      <property name="Area">DataArea</property>
      <property name="FieldName">cajas</property>
      <property name="Caption">Cajas</property>
      <property name="CellFormat" isnull="true" iskey="true">
        <property name="FormatString">n0</property>
        <property name="FormatType">Numeric</property>
      </property>
      <property name="Index">2</property>
      <property name="AreaIndex">0</property>
      <property name="MinWidth">20</property>
      <property name="Width">55</property>
    </property>
    <property name="Item4" isnull="true" iskey="true">
      <property name="Options" isnull="true" iskey="true">
        <property name="AllowRunTimeSummaryChange">true</property>
      </property>
      <property name="ImageIndex">-1</property>
      <property name="ToolTips" isnull="true" iskey="true">
        <property name="HeaderText" />
        <property name="ValueText" />
      </property>
      <property name="FieldEditName" />
      <property name="Name">fieldcharola</property>
      <property name="Area">DataArea</property>
      <property name="FieldName">charola</property>
      <property name="Caption">Charola</property>
      <property name="CellFormat" isnull="true" iskey="true">
        <property name="FormatString">n0</property>
        <property name="FormatType">Numeric</property>
      </property>
      <property name="Index">3</property>
      <property name="AreaIndex">1</property>
      <property name="MinWidth">20</property>
      <property name="Width">55</property>
    </property>
    <property name="Item5" isnull="true" iskey="true">
      <property name="Options" isnull="true" iskey="true">
        <property name="AllowRunTimeSummaryChange">true</property>
      </property>
      <property name="ImageIndex">-1</property>
      <property name="ToolTips" isnull="true" iskey="true">
        <property name="HeaderText" />
        <property name="ValueText" />
      </property>
      <property name="FieldEditName" />
      <property name="Name">fieldbolsa</property>
      <property name="Area">DataArea</property>
      <property name="FieldName">bolsa</property>
      <property name="Caption">Bolsa</property>
      <property name="CellFormat" isnull="true" iskey="true">
        <property name="FormatString">n0</property>
        <property name="FormatType">Numeric</property>
      </property>
      <property name="Index">4</property>
      <property name="AreaIndex">2</property>
      <property name="MinWidth">20</property>
      <property name="Width">55</property>
    </property>
    <property name="Item6" isnull="true" iskey="true">
      <property name="Options" isnull="true" iskey="true">
        <property name="AllowRunTimeSummaryChange">true</property>
      </property>
      <property name="ImageIndex">-1</property>
      <property name="ToolTips" isnull="true" iskey="true">
        <property name="HeaderText" />
        <property name="ValueText" />
      </property>
      <property name="FieldEditName" />
      <property name="Name">fielddia</property>
      <property name="FieldName">dia</property>
      <property name="Caption">Día de la semana</property>
      <property name="Index">5</property>
      <property name="AreaIndex">0</property>
      <property name="MinWidth">20</property>
      <property name="Width">100</property>
      <property name="Visible">false</property>
    </property>
    <property name="Item7" isnull="true" iskey="true">
      <property name="Options" isnull="true" iskey="true">
        <property name="AllowRunTimeSummaryChange">true</property>
      </property>
      <property name="ImageIndex">-1</property>
      <property name="ToolTips" isnull="true" iskey="true">
        <property name="HeaderText" />
        <property name="ValueText" />
      </property>
      <property name="FieldEditName" />
      <property name="Name">fieldcodigoempleado</property>
      <property name="FieldName">codigo_empleado</property>
      <property name="Caption">Código de empleado</property>
      <property name="Index">6</property>
      <property name="AreaIndex">1</property>
      <property name="MinWidth">20</property>
      <property name="Width">100</property>
      <property name="Visible">false</property>
    </property>
    <property name="Item8" isnull="true" iskey="true">
      <property name="Options" isnull="true" iskey="true">
        <property name="AllowRunTimeSummaryChange">true</property>
      </property>
      <property name="ImageIndex">-1</property>
      <property name="ToolTips" isnull="true" iskey="true">
        <property name="HeaderText" />
        <property name="ValueText" />
      </property>
      <property name="FieldEditName" />
      <property name="Name">fieldpuntoempaque</property>
      <property name="FieldName">punto_empaque</property>
      <property name="Caption">Punto de empaque</property>
      <property name="Index">7</property>
      <property name="AreaIndex">2</property>
      <property name="MinWidth">20</property>
      <property name="Width">100</property>
      <property name="Visible">false</property>
    </property>
    <property name="Item9" isnull="true" iskey="true">
      <property name="Options" isnull="true" iskey="true">
        <property name="AllowRunTimeSummaryChange">true</property>
      </property>
      <property name="ImageIndex">-1</property>
      <property name="ToolTips" isnull="true" iskey="true">
        <property name="HeaderText" />
        <property name="ValueText" />
      </property>
      <property name="FieldEditName" />
      <property name="Name">fieldbanda</property>
      <property name="FieldName">banda</property>
      <property name="Caption">Banda</property>
      <property name="Index">8</property>
      <property name="AreaIndex">3</property>
      <property name="MinWidth">20</property>
      <property name="Width">100</property>
      <property name="Visible">false</property>
    </property>
    <property name="Item10" isnull="true" iskey="true">
      <property name="Options" isnull="true" iskey="true">
        <property name="AllowRunTimeSummaryChange">true</property>
      </property>
      <property name="ImageIndex">-1</property>
      <property name="ToolTips" isnull="true" iskey="true">
        <property name="HeaderText" />
        <property name="ValueText" />
      </property>
      <property name="FieldEditName" />
      <property name="Name">fieldcultivo</property>
      <property name="FieldName">cultivo</property>
      <property name="Caption">Cultivo</property>
      <property name="Index">9</property>
      <property name="AreaIndex">4</property>
      <property name="MinWidth">20</property>
      <property name="Width">100</property>
      <property name="Visible">false</property>
    </property>
  </property>
  <property name="Prefilter" isnull="true" iskey="true">
    <property name="Enabled">true</property>
  </property>
  <property name="FixedLineWidth">2</property>
  <property name="Groups" iskey="true" value="0" />
  <property name="FormatRules" iskey="true" value="0" />
  <property name="FormatConditions" iskey="true" value="0" />
</XtraSerializer>', 'sp_frupa_cajas_empleado', 0, 'MI-0', 'M');
GO

IF NOT EXISTS (SELECT 1 FROM dbo.Menu WHERE n_clave_mod = 2 AND s_reporte_mnu = 'CAJAS POR EMPLEADO')
    INSERT INTO dbo.Menu (n_clave_mod, n_clave_mnu, s_nombre_mnu, s_forma_mnu, s_tipo_mnu, s_tipoforma_mnu, s_reporte_mnu)
    SELECT 2, ISNULL(MAX(n_clave_mnu), 0) + 1, 'Cajas por empleado', 'frmpivotDS', '4', 1, 'CAJAS POR EMPLEADO'
    FROM   dbo.Menu WHERE n_clave_mod = 2;
GO
