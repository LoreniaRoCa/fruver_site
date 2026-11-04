"""
Reporte "Proceso de maquila": lo que entregó el productor (recepción) contra lo que salió del empaque.

- Tabla rep_proceso_maquila, la llena `sincronizar_sqlserver.py 3` (solo reemplaza la temporada que trae).
  Un renglón por estiba + producto + etiqueta y otro "3 Diferencia de proceso" por estiba, así la suma de
  kilos de cada estiba es lo recibido. kilos_recibidos y cajas_recibidas solo vienen en el de diferencia.
- Permiso reportes.ver_proceso_maquila_pivot, el reporte con su formato base y la opción de menú.
"""
from django.db import migrations

SLUG = 'proceso-maquila'
CODENAME = 'ver_proceso_maquila_pivot'

CREAR_TABLA = """
CREATE TABLE IF NOT EXISTS public.rep_proceso_maquila (
    temporada       text,
    estiba          text,
    fecha           date,
    lote            text,
    huerta          text,
    dueno           text,
    cultivo         text,
    variedad        text,
    tipo            text,
    presentacion    text,
    calidad         text,
    envase          text,
    etiqueta        text,
    tamano          text,
    producto        text,
    cajas           numeric,
    kilos           numeric,
    kilos_recibidos numeric,
    cajas_recibidas numeric
);
CREATE INDEX IF NOT EXISTS rep_proceso_maquila_fecha_idx ON public.rep_proceso_maquila (fecha);
CREATE INDEX IF NOT EXISTS rep_proceso_maquila_temporada_idx ON public.rep_proceso_maquila (temporada);
"""

CONSULTA = '''SELECT estiba AS "Estiba", fecha AS "Fecha", lote AS "Lote", huerta AS "Huerta", dueno AS "Dueño",
       cultivo AS "Cultivo", variedad AS "Variedad", tipo AS "Tipo", presentacion AS "Presentación",
       calidad AS "Calidad", envase AS "Envase", etiqueta AS "Etiqueta", tamano AS "Tamaño", producto AS "Producto",
       cajas AS "Cajas", kilos AS "Kilos", kilos_recibidos AS "KilosRecibidos", cajas_recibidas AS "CajasRecibidas"
FROM rep_proceso_maquila
WHERE fecha BETWEEN %s::date AND %s::date'''

# Formato base: como el resumen que se le manda al productor. Filas Dueño > Estiba > Fecha, columnas
# Tipo > Presentación. "% del recibido" = kilos entre el total de la fila (lo recibido, gracias al renglón
# de diferencia). En el selector de campos quedan Lote, Huerta, Variedad, Tamaño, Etiqueta, Producto...
CONFIGURACION = {
    'showRowTotals': True,
    'fields': [
        {'dataField': 'Dueño', 'caption': 'Dueño', 'area': 'row', 'areaIndex': 0, 'expanded': True},
        # Cada estiba tiene una sola fecha: sin renglón de total por estiba
        {'dataField': 'Estiba', 'caption': 'Estiba', 'area': 'row', 'areaIndex': 1, 'expanded': True, 'showTotals': False},
        {'dataField': 'Fecha', 'caption': 'Fecha', 'dataType': 'date', 'format': 'dd/MM/yyyy', 'area': 'row', 'areaIndex': 2},
        {'dataField': 'Tipo', 'caption': 'Tipo', 'area': 'column', 'areaIndex': 0, 'expanded': True},
        {'dataField': 'Presentación', 'caption': 'Presentación', 'area': 'column', 'areaIndex': 1},
        {'dataField': 'Kilos', 'caption': 'Kilos', 'dataType': 'number', 'summaryType': 'sum',
         'format': '#,##0.00', 'area': 'data', 'areaIndex': 0},
        {'name': 'PorcentajeRecibido', 'dataField': 'Kilos', 'caption': '% del recibido', 'dataType': 'number',
         'summaryType': 'sum', 'summaryDisplayMode': 'percentOfRowGrandTotal',
         'format': {'type': 'percent', 'precision': 2}, 'area': 'data', 'areaIndex': 1},
        {'dataField': 'Cajas', 'caption': 'Cajas', 'dataType': 'number', 'summaryType': 'sum',
         'format': '#,##0', 'area': 'data', 'areaIndex': 2},
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


def crear_reporte(apps, schema_editor):
    Pivot_Dinamico = apps.get_model('reportes', 'Pivot_Dinamico')
    ContentType = apps.get_model('contenttypes', 'ContentType')
    Permission = apps.get_model('auth', 'Permission')
    ModuloSistema = apps.get_model('core_app', 'ModuloSistema')
    OpcionModulo = apps.get_model('core_app', 'OpcionModulo')

    # El permiso se crea normalmente al final del migrate; aquí antes, para ligarlo al menú
    ct, _ = ContentType.objects.get_or_create(app_label='reportes', model='pivot_dinamico')
    permiso, _ = Permission.objects.get_or_create(
        content_type=ct, codename=CODENAME, defaults={'name': 'Puede ver el reporte: Proceso de maquila'})

    if not Pivot_Dinamico.objects.filter(slug=SLUG).exists():
        Pivot_Dinamico.objects.create(
            nombre='Proceso de maquila', slug=SLUG, query_sql=CONSULTA, configuracion_pivot=CONFIGURACION,
            fecha_inicio_macro='-1m', fecha_fin_macro='m', icono='agriculture', permiso_codename=CODENAME,
            activo=True, orden=3)

    modulo = ModuloSistema.objects.filter(slug='reportes').first()
    link = f'/reportes/tablas/?open={SLUG}'
    if modulo and not OpcionModulo.objects.filter(modulo=modulo, link=link).exists():
        OpcionModulo.objects.create(modulo=modulo, grupo='Tablas Dinámicas', orden=0, titulo='Proceso de maquila',
                                    link=link, icono='bar_chart', permiso_requerido=permiso)


def quitar_reporte(apps, schema_editor):
    apps.get_model('core_app', 'OpcionModulo').objects.filter(link=f'/reportes/tablas/?open={SLUG}').delete()
    apps.get_model('reportes', 'Pivot_Dinamico').objects.filter(slug=SLUG).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('reportes', '0009_menu_reportes_excel'),
        ('core_app', '0005_accesos_iniciales'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='pivot_dinamico',
            options={'ordering': ['orden', 'nombre'],
                     'permissions': [('ver_inventario_pivot', 'Puede ver el reporte: Inventario Pivot'),
                                     ('ver_ventas_pivot', 'Puede ver el reporte: Ventas Pivot'),
                                     ('ver_proceso_maquila_pivot', 'Puede ver el reporte: Proceso de maquila')],
                     'verbose_name': 'Reporte Dinámico', 'verbose_name_plural': 'Reportes Dinámicos'},
        ),
        migrations.RunSQL(CREAR_TABLA, 'DROP TABLE IF EXISTS public.rep_proceso_maquila;'),
        migrations.RunPython(crear_reporte, quitar_reporte),
    ]
