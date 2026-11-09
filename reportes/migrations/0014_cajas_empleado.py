"""
Reporte "Cajas por empleado": cajas etiquetadas por empacador por día, con charola y bolsa.

- Tabla rep_cajas_empleado, la llena `sincronizar_sqlserver.py 4` (dbo.sp_frupa_cajas_empleado; solo reemplaza
  la temporada que trae).
- Permiso reportes.ver_cajas_empleado_pivot, el reporte con su formato base y la opción de menú.
"""
from django.db import migrations

SLUG = 'cajas-empleado'
CODENAME = 'ver_cajas_empleado_pivot'

CREAR_TABLA = """
CREATE TABLE IF NOT EXISTS public.rep_cajas_empleado (
    temporada       text,
    fecha           date,
    dia             text,
    codigo_empleado text,
    empleado        text,
    punto_empaque   text,
    banda           text,
    cultivo         text,
    cajas           integer,
    charola         integer,
    bolsa           integer
);
CREATE INDEX IF NOT EXISTS rep_cajas_empleado_fecha_idx ON public.rep_cajas_empleado (fecha);
CREATE INDEX IF NOT EXISTS rep_cajas_empleado_temporada_idx ON public.rep_cajas_empleado (temporada);
"""

CONSULTA = '''SELECT fecha AS "Fecha", dia AS "Día", codigo_empleado AS "CodigoEmpleado", empleado AS "Empleado",
       punto_empaque AS "PuntoEmpaque", banda AS "Banda", cultivo AS "Cultivo",
       cajas AS "Cajas", charola AS "Charola", bolsa AS "Bolsa"
FROM rep_cajas_empleado
WHERE fecha BETWEEN %s::date AND %s::date'''

# Empleados en renglones, los días en columnas y, por cada día y al final (Gran Total), Cajas, Charola y Bolsa
CONFIGURACION = {
    'showRowTotals': True,
    'fields': [
        {'dataField': 'Empleado', 'caption': 'Empacador', 'area': 'row', 'areaIndex': 0},
        {'dataField': 'Fecha', 'caption': 'Día', 'dataType': 'date', 'format': 'EEEE dd/MM', 'area': 'column', 'areaIndex': 0},
        {'dataField': 'Cajas', 'caption': 'Cajas', 'dataType': 'number', 'summaryType': 'sum', 'format': '#,##0',
         'area': 'data', 'areaIndex': 0},
        {'dataField': 'Charola', 'caption': 'Charola', 'dataType': 'number', 'summaryType': 'sum', 'format': '#,##0',
         'area': 'data', 'areaIndex': 1},
        {'dataField': 'Bolsa', 'caption': 'Bolsa', 'dataType': 'number', 'summaryType': 'sum', 'format': '#,##0',
         'area': 'data', 'areaIndex': 2},
        {'dataField': 'Día', 'caption': 'Día de la semana'},
        {'dataField': 'CodigoEmpleado', 'caption': 'Código de empleado'},
        {'dataField': 'PuntoEmpaque', 'caption': 'Punto de empaque'},
        {'dataField': 'Banda', 'caption': 'Banda'},
        {'dataField': 'Cultivo', 'caption': 'Cultivo'},
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
        content_type=ct, codename=CODENAME, defaults={'name': 'Puede ver el reporte: Cajas por empleado'})

    if not Pivot_Dinamico.objects.filter(slug=SLUG).exists():
        Pivot_Dinamico.objects.create(
            nombre='Cajas por empleado', slug=SLUG, query_sql=CONSULTA, configuracion_pivot=CONFIGURACION,
            fecha_inicio_macro='-6d', fecha_fin_macro='Hoy', icono='bar_chart', permiso_codename=CODENAME,
            activo=True, orden=4)

    modulo = ModuloSistema.objects.filter(slug='reportes').first()
    link = f'/reportes/tablas/?open={SLUG}'
    if modulo and not OpcionModulo.objects.filter(modulo=modulo, link=link).exists():
        OpcionModulo.objects.create(modulo=modulo, grupo='Tablas Dinámicas', orden=0, titulo='Cajas por empleado',
                                    link=link, icono='bar_chart', permiso_requerido=permiso)


def quitar_reporte(apps, schema_editor):
    apps.get_model('core_app', 'OpcionModulo').objects.filter(link=f'/reportes/tablas/?open={SLUG}').delete()
    apps.get_model('reportes', 'Pivot_Dinamico').objects.filter(slug=SLUG).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('reportes', '0013_proceso_maquila_pallets'),
        ('core_app', '0005_accesos_iniciales'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='pivot_dinamico',
            options={'ordering': ['orden', 'nombre'],
                     'permissions': [('ver_inventario_pivot', 'Puede ver el reporte: Inventario Pivot'),
                                     ('ver_ventas_pivot', 'Puede ver el reporte: Ventas Pivot'),
                                     ('ver_proceso_maquila_pivot', 'Puede ver el reporte: Proceso de maquila'),
                                     ('ver_cajas_empleado_pivot', 'Puede ver el reporte: Cajas por empleado')],
                     'verbose_name': 'Reporte Dinámico', 'verbose_name_plural': 'Reportes Dinámicos'},
        ),
        migrations.RunSQL(CREAR_TABLA, 'DROP TABLE IF EXISTS public.rep_cajas_empleado;'),
        migrations.RunPython(crear_reporte, quitar_reporte),
    ]
