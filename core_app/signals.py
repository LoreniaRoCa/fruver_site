from django.db.models.signals import post_save
from django.dispatch import receiver

from rh.models import Empleado
from .models import AccesoEmpresa


@receiver(post_save, sender=Empleado)
def acceso_a_empresa_del_empleado(sender, instance, **kwargs):
    """Al ligar un usuario a un empleado, el usuario obtiene acceso a la empresa de ese empleado
    (sin grupos; los roles se asignan en la ficha del usuario). No reactiva un acceso que se desactivó."""
    if instance.user_id and instance.empresa_id:
        AccesoEmpresa.objects.get_or_create(usuario_id=instance.user_id, empresa_id=instance.empresa_id)
