"""
Reporte "Pallets" (solo plantilla de Excel): cada pallet empacado con etiqueta, producto, lote, manifiesto y estiba.

- Tabla rep_pallets, la llena `sincronizar_sqlserver.py 5` (dbo.sp_frupa_pallets; solo reemplaza la temporada
  que trae).
- Permiso reportes.ver_pallets_pivot y el reporte (lo usa la API de Excel). Sin opción de menú: no se abre
  como tabla dinámica en el portal, solo aparece en Reportes en Excel.
"""
from django.db import migrations

SLUG = 'pallets'
CODENAME = 'ver_pallets_pivot'

CREAR_TABLA = """
CREATE TABLE IF NOT EXISTS public.rep_pallets (
    temporada   text,
    pallet      text,
    seccion     text,
    fecha       date,
    hora        text,
    lote        text,
    nombre_lote text,
    manifiesto  text,
    estiba      text,
    seleccion   text,
    etiqueta    text,
    producto    text,
    cajas       numeric
);
CREATE INDEX IF NOT EXISTS rep_pallets_fecha_idx ON public.rep_pallets (fecha);
CREATE INDEX IF NOT EXISTS rep_pallets_temporada_idx ON public.rep_pallets (temporada);
"""

CONSULTA = '''SELECT pallet AS "Pallet", seccion AS "Sección", fecha AS "Fecha", hora AS "Hora", lote AS "Lote",
       nombre_lote AS "NombreLote", manifiesto AS "Manifiesto", estiba AS "Estiba", seleccion AS "Selección",
       etiqueta AS "Etiqueta", producto AS "Producto", cajas AS "Cajas"
FROM rep_pallets
WHERE fecha BETWEEN %s::date AND %s::date'''

# Formato base de la plantilla de Excel: cajas por etiqueta y producto; los demás campos quedan en la hoja Datos
CONFIGURACION = {
    'fields': [
        {'dataField': 'Etiqueta', 'caption': 'Etiqueta', 'area': 'row', 'areaIndex': 0},
        {'dataField': 'Producto', 'caption': 'Producto', 'area': 'row', 'areaIndex': 1},
        {'dataField': 'Cajas', 'caption': 'Cajas', 'dataType': 'number', 'summaryType': 'sum', 'format': '#,##0',
         'area': 'data', 'areaIndex': 0},
        {'dataField': 'Pallet', 'caption': 'Pallet'},
        {'dataField': 'Sección', 'caption': 'Sección'},
        {'dataField': 'Fecha', 'caption': 'Fecha de empaque', 'dataType': 'date', 'format': 'dd/MM/yyyy'},
        {'dataField': 'Hora', 'caption': 'Hora'},
        {'dataField': 'Lote', 'caption': 'Lote'},
        {'dataField': 'NombreLote', 'caption': 'Nombre del lote'},
        {'dataField': 'Manifiesto', 'caption': 'Manifiesto'},
        {'dataField': 'Estiba', 'caption': 'Estiba'},
        {'dataField': 'Selección', 'caption': 'Selección'},
    ],
}


def crear_reporte(apps, schema_editor):
    Pivot_Dinamico = apps.get_model('reportes', 'Pivot_Dinamico')
    ContentType = apps.get_model('contenttypes', 'ContentType')
    Permission = apps.get_model('auth', 'Permission')
    ct, _ = ContentType.objects.get_or_create(app_label='reportes', model='pivot_dinamico')
    Permission.objects.get_or_create(content_type=ct, codename=CODENAME, defaults={'name': 'Puede ver el reporte: Pallets'})
    if not Pivot_Dinamico.objects.filter(slug=SLUG).exists():
        Pivot_Dinamico.objects.create(
            nombre='Pallets', slug=SLUG, query_sql=CONSULTA, configuracion_pivot=CONFIGURACION,
            fecha_inicio_macro='M', fecha_fin_macro='Hoy', icono='bar_chart', permiso_codename=CODENAME,
            activo=True, orden=5)


def quitar_reporte(apps, schema_editor):
    apps.get_model('reportes', 'Pivot_Dinamico').objects.filter(slug=SLUG).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('reportes', '0014_cajas_empleado'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='pivot_dinamico',
            options={'ordering': ['orden', 'nombre'],
                     'permissions': [('ver_inventario_pivot', 'Puede ver el reporte: Inventario Pivot'),
                                     ('ver_ventas_pivot', 'Puede ver el reporte: Ventas Pivot'),
                                     ('ver_proceso_maquila_pivot', 'Puede ver el reporte: Proceso de maquila'),
                                     ('ver_cajas_empleado_pivot', 'Puede ver el reporte: Cajas por empleado'),
                                     ('ver_pallets_pivot', 'Puede ver el reporte: Pallets')],
                     'verbose_name': 'Reporte Dinámico', 'verbose_name_plural': 'Reportes Dinámicos'},
        ),
        migrations.RunSQL(CREAR_TABLA, 'DROP TABLE IF EXISTS public.rep_pallets;'),
        migrations.RunPython(crear_reporte, quitar_reporte),
    ]
