"""
Agrega la sección "Excel" al menú del módulo de Reportes (core_opcion_modulo): la página Reportes en Excel
para todos (ahí solo aparecen los reportes que cada usuario puede ver) y, solo para superusuarios,
las claves y la bitácora de consultas.
"""
from django.db import migrations

GRUPO = 'Excel'

# (orden, título, link, icono, solo superusuario)
OPCIONES = [
    (20, 'Reportes en Excel', '/reportes/excel/', 'table_view', False),
    (21, 'Claves de Excel', '/admin/reportes/claveexcel/', 'key', True),
    (22, 'Bitácora de consultas Excel', '/admin/reportes/bitacoraconsultaexcel/', 'history', True),
]


def agregar_menu(apps, schema_editor):
    ModuloSistema = apps.get_model('core_app', 'ModuloSistema')
    OpcionModulo = apps.get_model('core_app', 'OpcionModulo')
    modulo = ModuloSistema.objects.filter(slug='reportes').first()
    if not modulo or OpcionModulo.objects.filter(modulo=modulo, grupo=GRUPO).exists():
        return
    for orden, titulo, link, icono, solo_superusuario in OPCIONES:
        OpcionModulo.objects.create(modulo=modulo, grupo=GRUPO, orden=orden, titulo=titulo, link=link,
                                    icono=icono, solo_superusuario=solo_superusuario)


def quitar_menu(apps, schema_editor):
    ModuloSistema = apps.get_model('core_app', 'ModuloSistema')
    OpcionModulo = apps.get_model('core_app', 'OpcionModulo')
    OpcionModulo.objects.filter(modulo__in=ModuloSistema.objects.filter(slug='reportes'), grupo=GRUPO).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('reportes', '0008_clave_excel_bitacora_consulta'),
        ('core_app', '0005_accesos_iniciales'),
    ]

    operations = [
        migrations.RunPython(agregar_menu, quitar_menu),
    ]
