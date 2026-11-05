"""
Opción "Tablero de maquila" en el menú de Tablas Dinámicas. Se abre en pestaña como las tablas dinámicas
(lista_tablas.html la manda a /reportes/maquila/) y pide el mismo permiso que el reporte Proceso de maquila.
"""
from django.db import migrations

LINK = '/reportes/tablas/?open=tablero-maquila'


def agregar_menu(apps, schema_editor):
    ModuloSistema = apps.get_model('core_app', 'ModuloSistema')
    OpcionModulo = apps.get_model('core_app', 'OpcionModulo')
    Permission = apps.get_model('auth', 'Permission')
    modulo = ModuloSistema.objects.filter(slug='reportes').first()
    if not modulo or OpcionModulo.objects.filter(modulo=modulo, link=LINK).exists():
        return
    permiso = Permission.objects.filter(content_type__app_label='reportes', codename='ver_proceso_maquila_pivot').first()
    OpcionModulo.objects.create(modulo=modulo, grupo='Tablas Dinámicas', orden=0, titulo='Tablero de maquila',
                                link=LINK, icono='dashboard', permiso_requerido=permiso)


def quitar_menu(apps, schema_editor):
    apps.get_model('core_app', 'OpcionModulo').objects.filter(link=LINK).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('reportes', '0011_proceso_maquila_resumen'),
        ('core_app', '0005_accesos_iniciales'),
    ]

    operations = [
        migrations.RunPython(agregar_menu, quitar_menu),
    ]
