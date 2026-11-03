# Crea la plantilla de Excel de un reporte manejando Excel por COM. Lo llama
# `python manage.py crear_plantilla_excel <slug>`, que arma la especificación (spec.json):
# consultas de Power Query, acomodo de la tabla dinámica, formatos y celdas de parámetros.
#
# Hojas: Parámetros (empresa, fechas, estado de la última actualización), Reporte (tabla dinámica)
# y Datos (tabla que llena Power Query).
param(
    [Parameter(Mandatory = $true)][string]$Spec,
    [Parameter(Mandatory = $true)][string]$Salida
)
$ErrorActionPreference = 'Stop'
$s = Get-Content -Raw -Encoding UTF8 $Spec | ConvertFrom-Json

function Fijar-Propiedad($objeto, $propiedad, $argumentos) {
    # Propiedades con parámetro de COM (p. ej. PivotField.Subtotals(1) = False)
    [System.__ComObject].InvokeMember($propiedad, [System.Reflection.BindingFlags]::SetProperty, $null, $objeto, $argumentos) | Out-Null
}

function Tabla-De-Consulta($hoja, $celda, $consulta, $nombre) {
    $conexion = "OLEDB;Provider=Microsoft.Mashup.OleDb.1;Data Source=`$Workbook`$;Location=$consulta;Extended Properties=`"`""
    $lo = $hoja.ListObjects.Add(0, $conexion, [Type]::Missing, 1, $hoja.Range($celda))
    $lo.Name = $nombre
    $lo.QueryTable.CommandType = 2  # xlCmdSql
    $lo.QueryTable.CommandText = "SELECT * FROM [$consulta]"
    $lo.QueryTable.BackgroundQuery = $false  # Actualizar todo: primero los datos y después la tabla dinámica
    $lo.QueryTable.RefreshOnFileOpen = $false
    $lo.QueryTable.Refresh($false) | Out-Null
    return $lo
}

$verdeOscuro = 0x326B47   # BGR de #476b32
$verdeClaro = 0xF0F7F2    # BGR de #f2f7f0
$amarillo = 0xCCF2FF      # BGR de #fff2cc
$gris = 0x8B7464          # BGR de #64748b

$xl = New-Object -ComObject Excel.Application
$xl.Visible = [bool]$s.visible
$xl.DisplayAlerts = $false
$wb = $null
try {
    $wb = $xl.Workbooks.Add()
    while ($wb.Worksheets.Count -gt 1) { $wb.Worksheets.Item($wb.Worksheets.Count).Delete() }

    # ------------------------------------------------------------ Parámetros
    $par = $wb.Worksheets.Item(1)
    $par.Name = $s.hoja_parametros
    $xl.ActiveWindow.DisplayGridlines = $false
    $par.Columns.Item(1).ColumnWidth = 2
    $par.Columns.Item(2).ColumnWidth = 20
    $par.Columns.Item(3).ColumnWidth = 34
    $par.Columns.Item(4).ColumnWidth = 22
    $par.Columns.Item(5).ColumnWidth = 60

    $par.Range('B1').Value2 = 'SITE FRUVER'
    $par.Range('B1').Font.Bold = $true
    $par.Range('B1').Font.Color = $verdeOscuro
    $par.Range('B2').Value2 = $s.nombre
    $par.Range('B2').Font.Bold = $true
    $par.Range('B2').Font.Size = 16

    $etiquetas = [ordered]@{ servidor = 'Portal'; empresa = 'Empresa'; fecha_inicio = 'Fecha inicial'; fecha_fin = 'Fecha final' }
    foreach ($clave in $etiquetas.Keys) {
        $ref = $s.celdas.$clave
        $fila = [int]($ref.Substring(1))
        $par.Range("B$fila").Value2 = $etiquetas[$clave]
        $par.Range("B$fila").Font.Bold = $true
        $celda = $par.Range($ref)
        $celda.Interior.Color = if ($clave -eq 'servidor') { $verdeClaro } else { $amarillo }
        $celda.Borders.LineStyle = 1
        $celda.Borders.Color = 0xC0C0C0
        $celda.HorizontalAlignment = -4131  # izquierda
        # Fecha: se le pone una fecha para que Excel use su formato de fecha corta (respeta el idioma del equipo;
        # 'dd/mm/yyyy' escrito por COM en un Excel en español queda como texto 'yyyy'). El portal la reemplaza al descargar.
        if ($clave -like 'fecha_*') { $celda.Value = (Get-Date).Date } else { $celda.NumberFormat = '@' }
        if ($clave -eq 'servidor') { $celda.Font.Color = $gris }
        $wb.Names.Add($s.nombres.$clave, "='$($s.hoja_parametros)'!`$$($ref.Substring(0,1))`$$fila") | Out-Null
    }
    $nota = $par.Range($s.celdas.empresas)
    $nota.Font.Italic = $true
    $nota.Font.Color = $gris
    $par.Range('C6:C7').Validation.Add(4, 1, 7, '36526') | Out-Null  # xlValidateDate, mayor o igual a 01/01/2000 (número: no depende del idioma)
    $par.Range('C6:C7').Validation.ErrorMessage = 'Escribe una fecha, por ejemplo 01/10/2026'

    $par.Range('B9').Value2 = 'Cambia la empresa o las fechas y usa Datos > Actualizar todo (Ctrl+Alt+F5).'
    $par.Range('B10').Value2 = 'La primera vez Excel pide credenciales: elige "Básica", tu usuario del portal y como contraseña tu clave de Excel.'
    $par.Range('B11').Value2 = 'La clave se genera en el portal: Reportes en Excel. Es personal; no la compartas.'
    $par.Range('B9:B11').Font.Color = $gris
    $par.Range('B13').Value2 = 'Última actualización'
    $par.Range('B13').Font.Bold = $true

    # ------------------------------------------------------------ Consultas
    $wb.Queries.Add('Datos', $s.m_datos) | Out-Null
    $wb.Queries.Add('Estado', $s.m_estado) | Out-Null
    $wb.Queries.FastCombine = $true  # parámetros de la hoja + portal en la misma consulta sin pedir niveles de privacidad

    $estado = Tabla-De-Consulta $par 'B14' 'Estado' 'tblEstado'
    $estado.TableStyle = 'TableStyleLight14'

    $rep = $wb.Worksheets.Add([Type]::Missing, $par)
    $rep.Name = 'Reporte'
    $dat = $wb.Worksheets.Add([Type]::Missing, $rep)
    $dat.Name = 'Datos'
    $datos = Tabla-De-Consulta $dat 'A1' 'Datos' 'tblDatos'
    $datos.TableStyle = 'TableStyleLight14'

    # ------------------------------------------------------------ Reporte (tabla dinámica)
    $rep.Activate()
    $xl.ActiveWindow.DisplayGridlines = $false
    $rep.Range('A1').Value2 = $s.nombre.ToUpper()
    $rep.Range('A1').Font.Bold = $true
    $rep.Range('A1').Font.Size = 14
    $rep.Range('A2').Formula = '=IFERROR(INDEX(tblEstado[Empresa],1),"")'
    $rep.Range('A2').Font.Bold = $true
    $rep.Range('A3').Formula = '="Período: Del "&TEXT(DAY(pFechaInicio),"00")&"/"&TEXT(MONTH(pFechaInicio),"00")&"/"&YEAR(pFechaInicio)&" al "&TEXT(DAY(pFechaFin),"00")&"/"&TEXT(MONTH(pFechaFin),"00")&"/"&YEAR(pFechaFin)'
    $rep.Range('A3').Font.Italic = $true
    $rep.Range('A3').Font.Color = $gris

    $destino = if ($s.filtros_pagina.Count -gt 0) { "A$(6 + $s.filtros_pagina.Count)" } else { 'A5' }
    $cache = $wb.PivotCaches().Create(1, 'tblDatos', 6)  # xlDatabase, Excel 2013+
    $pt = $cache.CreatePivotTable($rep.Range($destino), 'tdReporte', $true, 6)
    $pt.RowAxisLayout(1)  # tabular, como en el portal
    $pt.TableStyle2 = 'PivotStyleMedium7'
    $pt.PrintTitles = $true
    $pt.RepeatItemsOnEachPrintedPage = $true
    $pt.NullString = ''

    $posicion = 1
    # Orden ascendente: en Excel los números van antes que el texto (Tamaño: 56, 64 ... 216, CANICA)
    foreach ($nombre in $s.filas) { $f = $pt.PivotFields($nombre); $f.Orientation = 1; $f.Position = $posicion; $f.AutoSort(1, $nombre); $posicion++ }
    $posicion = 1
    foreach ($nombre in $s.columnas) { $f = $pt.PivotFields($nombre); $f.Orientation = 2; $f.Position = $posicion; $f.AutoSort(1, $nombre); $posicion++ }
    foreach ($nombre in $s.filtros_pagina) { $f = $pt.PivotFields($nombre); $f.Orientation = 3 }
    foreach ($d in $s.datos) {
        # El nombre de un campo de datos no puede ser igual al de la columna: se le agrega un espacio
        $df = $pt.AddDataField($pt.PivotFields($d.campo), "$($d.titulo) ", $d.resumen)
        $df.NumberFormat = $d.formato
    }
    if (-not $s.subtotales) {
        foreach ($nombre in $s.filas + $s.columnas) { Fijar-Propiedad $pt.PivotFields($nombre) 'Subtotals' @(1, $false) }
    }
    foreach ($filtro in $s.filtros_etiqueta) {
        try { $pt.PivotFields($filtro.campo).PivotFilters.Add2($filtro.tipo, [Type]::Missing, $filtro.valor) | Out-Null }
        catch { Write-Output "Aviso: no se pudo aplicar el filtro de $($filtro.campo): $($_.Exception.Message)" }
    }
    $pt.PivotCache().RefreshOnFileOpen = $false

    # Anchos fijos (Excel no ajusta bien las columnas de agrupación al actualizar): las de agrupación amplias
    # y las de datos angostas, para que al imprimir en una hoja no se les quite espacio a Variedad, Etiqueta...
    $pt.HasAutoFormat = $false
    $agrupacion = [Math]::Max(1, $s.filas.Count)
    for ($c = 1; $c -le $agrupacion; $c++) { $rep.Columns.Item($c).ColumnWidth = 28 }
    for ($c = $agrupacion + 1; $c -le $agrupacion + 60; $c++) { $rep.Columns.Item($c).ColumnWidth = 10 }

    # Impresión: carta horizontal, ajustada al ancho de una hoja
    try {
        $ps = $rep.PageSetup
        $ps.Orientation = 2
        $ps.PaperSize = 1
        $ps.Zoom = $false
        $ps.FitToPagesWide = 1
        $ps.FitToPagesTall = $false
        $ps.LeftMargin = $xl.InchesToPoints(0.3); $ps.RightMargin = $xl.InchesToPoints(0.3)
        $ps.TopMargin = $xl.InchesToPoints(0.4); $ps.BottomMargin = $xl.InchesToPoints(0.5)
        $ps.LeftFooter = $s.nombre
        $ps.RightFooter = 'Página &P de &N'
    } catch { Write-Output "Aviso: no se configuró la impresión ($($_.Exception.Message))" }

    $par.Activate()
    $par.Range($s.celdas.empresa).Select()
    $wb.SaveAs($Salida, 51)  # xlOpenXMLWorkbook
    Write-Output "Excel guardó $Salida"
}
catch {
    [Console]::Error.WriteLine($_.Exception.Message + "`n" + $_.InvocationInfo.PositionMessage)
    exit 1
}
finally {
    if ($wb) { $wb.Close($false) }
    $xl.Quit()
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($xl) | Out-Null
}
