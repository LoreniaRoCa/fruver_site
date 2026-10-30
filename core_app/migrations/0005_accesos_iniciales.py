"""
Accesos iniciales para que nadie pierda la entrada al instalar los permisos por empresa:
- Usuario ligado a un Empleado -> acceso a la empresa de ese empleado.
- Usuario sin Empleado (no superusuario) -> acceso a todas las empresas activas, como hasta ahora.
Los superusuarios no necesitan registros: entran a todas las empresas activas.
Sus grupos y permisos de Django se quedan como globales (valen en todas sus empresas).
"""
from django.db import migrations


def crear_accesos(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    Empleado = apps.get_model('rh', 'Empleado')
    Empresa = apps.get_model('rh', 'Empresa')
    AccesoEmpresa = apps.get_model('core_app', 'AccesoEmpresa')

    activas = list(Empresa.objects.filter(activa=True).values_list('pk', flat=True))
    empresas_por_usuario = {}
    for user_id, empresa_id in Empleado.objects.filter(user__isnull=False, empresa__isnull=False).values_list('user_id', 'empresa_id'):
        empresas_por_usuario.setdefault(user_id, set()).add(empresa_id)

    nuevos = []
    for user in User.objects.filter(is_superuser=False):
        for empresa_id in empresas_por_usuario.get(user.pk) or activas:
            nuevos.append(AccesoEmpresa(usuario_id=user.pk, empresa_id=empresa_id, activo=True))
    AccesoEmpresa.objects.bulk_create(nuevos, ignore_conflicts=True)


class Migration(migrations.Migration):

    dependencies = [
        ('core_app', '0004_acceso_empresa'),
        ('rh', '0035_empresa_logo'),
    ]

    operations = [
        migrations.RunPython(crear_accesos, migrations.RunPython.noop),
    ]
