"""
Proceso de maquila sin el renglón "Diferencia de proceso":
- Columna resumen ("estiba | promedio por caja | cajas | kilos recibidos") para agrupar por proceso.
- kilos_recibidos y cajas_recibidas vienen solo en el primer renglón de cada estiba.
- "% del recibido" con el campo porcentajeDe: kilos de la celda entre los kilos recibidos del total del renglón.
"""
from django.db import migrations

SLUG = 'proceso-maquila'

CONSULTA = '''SELECT resumen AS "ResumenProceso", estiba AS "Estiba", fecha AS "Fecha", lote AS "Lote", huerta AS "Huerta",
       dueno AS "Dueño", cultivo AS "Cultivo", variedad AS "Variedad", tipo AS "Tipo", presentacion AS "Presentación",
       calidad AS "Calidad", envase AS "Envase", etiqueta AS "Etiqueta", tamano AS "Tamaño", producto AS "Producto",
       cajas AS "Cajas", kilos AS "Kilos", kilos_recibidos AS "KilosRecibidos", cajas_recibidas AS "CajasRecibidas"
FROM rep_proceso_maquila
WHERE fecha BETWEEN %s::date AND %s::date'''

# Filas Dueño > Resumen proceso, columnas Tipo > Presentación (el desglose va en columnas para que el
# "% del recibido" sea contra todo lo recibido de las estibas del renglón).
CONFIGURACION = {
    'showRowTotals': True,
    'fields': [
        {'dataField': 'Dueño', 'caption': 'Dueño', 'area': 'row', 'areaIndex': 0, 'expanded': True},
        {'dataField': 'ResumenProceso', 'caption': 'Resumen proceso', 'area': 'row', 'areaIndex': 1},
        {'dataField': 'Tipo', 'caption': 'Tipo', 'area': 'column', 'areaIndex': 0, 'expanded': True},
        {'dataField': 'Presentación', 'caption': 'Presentación', 'area': 'column', 'areaIndex': 1},
        {'dataField': 'Kilos', 'caption': 'Kilos', 'dataType': 'number', 'summaryType': 'sum',
         'format': '#,##0.00', 'area': 'data', 'areaIndex': 0},
        {'name': 'PorcentajeRecibido', 'caption': '% del recibido',
         'porcentajeDe': {'numerador': 'Kilos', 'denominador': 'KilosRecibidos'},
         'format': {'type': 'percent', 'precision': 2}, 'area': 'data', 'areaIndex': 1},
        {'dataField': 'Cajas', 'caption': 'Cajas', 'dataType': 'number', 'summaryType': 'sum',
         'format': '#,##0', 'area': 'data', 'areaIndex': 2},
        {'dataField': 'Estiba', 'caption': 'Estiba'},
        {'dataField': 'Fecha', 'caption': 'Fecha', 'dataType': 'date', 'format': 'dd/MM/yyyy'},
        {'dataField': 'Lote', 'caption': 'Lote'},
        {'dataField': 'Huerta', 'caption': 'Huerta'},
        {'dataField': 'Cultivo', 'caption': 'Cultivo'},
        {'dataField': 'Variedad', 'caption': 'Variedad'},
        {'dataField': 'Calidad', 'caption': 'Calidad'},
        {'dataField': 'Envase', 'caption': 'Envase'},
        {'dataField': 'Etiqueta', 'caption': 'Etiqueta'},
        {'dataField': 'Tamaño', 'caption': 'Tamaño'},
        {'dataField': 'Producto', 'caption': 'Producto'},
        {'dataField': 'KilosRecibidos', 'caption': 'Kilos recibidos', 'dataType': 'number', 'summaryType': 'sum',
         'format': '#,##0.00'},
        {'dataField': 'CajasRecibidas', 'caption': 'Cajas recibidas', 'dataType': 'number', 'summaryType': 'sum',
         'format': '#,##0'},
        {'name': 'PromedioPorCaja', 'caption': 'Prom. kg por caja recibida',
         'cociente': {'numerador': 'KilosRecibidos', 'denominador': 'CajasRecibidas'}, 'format': '#,##0.00'},
    ],
}


def actualizar_reporte(apps, schema_editor):
    apps.get_model('reportes', 'Pivot_Dinamico').objects.filter(slug=SLUG).update(
        query_sql=CONSULTA, configuracion_pivot=CONFIGURACION)


class Migration(migrations.Migration):

    dependencies = [
        ('reportes', '0010_proceso_maquila'),
    ]

    operations = [
        migrations.RunSQL('ALTER TABLE public.rep_proceso_maquila ADD COLUMN IF NOT EXISTS resumen text;',
                          'ALTER TABLE public.rep_proceso_maquila DROP COLUMN IF EXISTS resumen;'),
        migrations.RunPython(actualizar_reporte, migrations.RunPython.noop),
    ]
