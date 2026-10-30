"""
Permisos por empresa.

- `empresas_permitidas(user)`: empresas a las que puede entrar (superusuario: todas las activas).
- `PermisosPorEmpresaBackend`: suma a los permisos globales de Django los grupos/permisos que el usuario
  tiene en la empresa activa de su sesión (AccesoEmpresa). La empresa activa la pone
  EmpresaActivaMiddleware en `request.user._empresa_activa`; fuera de una petición (comandos) no hay
  empresa activa y solo cuentan los permisos globales.

Va en AUTHENTICATION_BACKENDS junto a ModelBackend (que sigue autenticando y dando los globales).
"""
from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.models import Permission
from django.contrib.staticfiles import finders
from django.templatetags.static import static

from rh.models import Empresa
from .models import AccesoEmpresa


def logo_de_empresa(empresa):
    """URL del logo: el campo logo de Empresa o static/img/logo_<id>.png (mismo criterio que las tablas dinámicas)."""
    if empresa.logo:
        return empresa.logo.url
    ruta = f"img/logo_{str(empresa.pk).strip().lower()}.png"
    return static(ruta) if finders.find(ruta) else None


def empresas_permitidas(user):
    activas = Empresa.objects.filter(activa=True).order_by('nombre')
    if not user or not user.is_authenticated:
        return activas.none()
    if user.is_superuser:
        return activas
    return activas.filter(accesos_usuario__usuario=user, accesos_usuario__activo=True).distinct()


class PermisosPorEmpresaBackend(BaseBackend):

    def authenticate(self, request, **credentials):
        return None  # La autenticación la hace ModelBackend

    def get_all_permissions(self, user_obj, obj=None):
        if not user_obj.is_active or user_obj.is_anonymous or obj is not None:
            return set()
        empresa = getattr(user_obj, '_empresa_activa', None)
        if not empresa:
            return set()
        cache = getattr(user_obj, '_permisos_empresa_cache', None)
        if cache is None or cache[0] != empresa:
            acceso = AccesoEmpresa.objects.filter(usuario=user_obj, empresa_id=empresa, activo=True).first()
            permisos = set()
            if acceso:
                qs = Permission.objects.filter(accesos_empresa=acceso) | Permission.objects.filter(group__accesos_empresa=acceso)
                permisos = {f"{ct}.{codename}" for ct, codename in qs.values_list('content_type__app_label', 'codename').distinct()}
            cache = (empresa, permisos)
            user_obj._permisos_empresa_cache = cache
        return cache[1]

    def has_perm(self, user_obj, perm, obj=None):
        return perm in self.get_all_permissions(user_obj, obj)

    def has_module_perms(self, user_obj, app_label):
        return any(p.split('.', 1)[0] == app_label for p in self.get_all_permissions(user_obj))
