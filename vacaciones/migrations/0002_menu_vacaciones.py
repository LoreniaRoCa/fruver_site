"""
Agrega la sección "Vacaciones" al menú del módulo de Recursos Humanos (core_opcion_modulo),
entre "Evaluaciones de Desempeño" y "Catálogos del Sistema".
"""
from django.db import migrations
from django.db.models import F

GRUPO = 'Vacaciones'

# (orden, título, link, icono, (app_label, model, codename, nombre del permiso) o None)
OPCIONES = [
    (5, 'Mis vacaciones', '/admin/rh/vacaciones/mis/', 'beach_access', None),
    (6, 'Solicitar vacaciones', '/admin/rh/vacaciones/solicitar/', 'event_available', None),
    (7, 'Aprobaciones', '/admin/rh/vacaciones/aprobaciones/', 'task_alt', None),
    (8, 'Solicitudes del personal', '/admin/rh/vacaciones/solicitudes/', 'list_alt',
     ('vacaciones', 'politicavacaciones', 'autorizar_rh', 'Puede dar la autorización de RH y ver las vacaciones del personal')),
    (9, 'Saldos del personal', '/admin/rh/vacaciones/personal/', 'account_balance_wallet',
     ('vacaciones', 'politicavacaciones', 'autorizar_rh', 'Puede dar la autorización de RH y ver las vacaciones del personal')),
    (10, 'Días inhábiles', '/admin/vacaciones/diainhabil/', 'event_busy',
     ('vacaciones', 'diainhabil', 'view_diainhabil', 'Can view Día inhábil')),
    (11, 'Ajuste de saldos', '/admin/vacaciones/saldovacaciones/', 'edit_calendar',
     ('vacaciones', 'saldovacaciones', 'view_saldovacaciones', 'Can view Saldo de vacaciones')),
    (12, 'Política de vacaciones', '/admin/vacaciones/politicavacaciones/', 'tune',
     ('vacaciones', 'politicavacaciones', 'view_politicavacaciones', 'Can view Política de vacaciones')),
]
DESPLAZAMIENTO_CATALOGOS = 10


def agregar_menu(apps, schema_editor):
    ModuloSistema = apps.get_model('core_app', 'ModuloSistema')
    OpcionModulo = apps.get_model('core_app', 'OpcionModulo')
    ContentType = apps.get_model('contenttypes', 'ContentType')
    Permission = apps.get_model('auth', 'Permission')

    modulo = ModuloSistema.objects.filter(slug='rh').first()
    if not modulo or OpcionModulo.objects.filter(modulo=modulo, grupo=GRUPO).exists():
        return

    # Recorre las opciones que estaban después de Evaluaciones (Catálogos) para dejar espacio
    OpcionModulo.objects.filter(modulo=modulo, orden__gte=5).exclude(grupo=GRUPO).update(
        orden=F('orden') + DESPLAZAMIENTO_CATALOGOS)

    for orden, titulo, link, icono, permiso in OPCIONES:
        permiso_obj = None
        if permiso:
            app_label, model, codename, nombre = permiso
            # Los permisos se crean normalmente al final del migrate; aquí se crean antes para ligarlos al menú
            ct, _ = ContentType.objects.get_or_create(app_label=app_label, model=model)
            permiso_obj, _ = Permission.objects.get_or_create(content_type=ct, codename=codename, defaults={'name': nombre})
        OpcionModulo.objects.create(modulo=modulo, grupo=GRUPO, orden=orden, titulo=titulo,
                                    link=link, icono=icono, permiso_requerido=permiso_obj)


def quitar_menu(apps, schema_editor):
    ModuloSistema = apps.get_model('core_app', 'ModuloSistema')
    OpcionModulo = apps.get_model('core_app', 'OpcionModulo')
    modulo = ModuloSistema.objects.filter(slug='rh').first()
    if not modulo or not OpcionModulo.objects.filter(modulo=modulo, grupo=GRUPO).exists():
        return
    OpcionModulo.objects.filter(modulo=modulo, grupo=GRUPO).delete()
    OpcionModulo.objects.filter(modulo=modulo, orden__gte=5 + DESPLAZAMIENTO_CATALOGOS).update(
        orden=F('orden') - DESPLAZAMIENTO_CATALOGOS)


class Migration(migrations.Migration):

    dependencies = [
        ('vacaciones', '0001_initial'),
        ('core_app', '0003_opcionmodulo_grupo'),
        ('contenttypes', '0002_remove_content_type_name'),
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.RunPython(agregar_menu, quitar_menu),
    ]
