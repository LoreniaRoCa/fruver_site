from django.conf import settings
from django.shortcuts import redirect
from rh.admin import admin_site  # Mantenemos el registro del admin_site personalizado
from .models import ModuloSistema, OpcionModulo

class NavegacionDinamicaMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path.lower()
        modulo_slug = None

        # Detectar el módulo activo por la URL
        if any(k in path for k in ['/admin/rh/', '/admin/vacaciones/', 'evaluacion', 'empleado', 'puesto', 'departamento', 'competencia', 'resumen', 'panel']):
            modulo_slug = 'rh'
        elif any(k in path for k in ['/inventario/', '/reportes/', 'pivot']):
            modulo_slug = 'reportes'
        elif any(k in path for k in ['/admin/auth/', '/auth/', '/user/', '/group/']):
            modulo_slug = 'seguridad'

        if modulo_slug and request.user.is_authenticated:
            # Consultar las opciones permitidas
            opciones_qs = OpcionModulo.objects.filter(
                modulo__slug=modulo_slug,
                modulo__activo=True
            ).select_related('permiso_requerido', 'permiso_requerido__content_type').order_by('orden')

            # 🌟 AGRUPACIÓN DINÁMICA POR GRUPO DE OPCIONES:
            agrupado = {}
            for op in opciones_qs:
                # 1. Validar restricción de superusuario
                if op.solo_superusuario and not request.user.is_superuser:
                    continue

                # 2. Validar restricción por Permiso de Django
                if op.permiso_requerido and not request.user.is_superuser:
                    cod_permiso = f"{op.permiso_requerido.content_type.app_label}.{op.permiso_requerido.codename}"
                    if not request.user.has_perm(cod_permiso):
                        continue  # Oculta la opción si no tiene el permiso

                # 3. Clasificar dentro del grupo correspondiente
                nombre_grupo = op.grupo if op.grupo else "Navegación del Módulo"
                if nombre_grupo not in agrupado:
                    agrupado[nombre_grupo] = []

                agrupado[nombre_grupo].append({
                    "title": op.titulo,
                    "link": op.link,
                    "icon": op.icono,
                })

            # 🌟 CONSTRUCCIÓN FINAL DE LAESTRUCTURA DE NAVEGACIÓN PARA UNFOLD:
            navigation_structure = []
            for grupo_titulo, items in agrupado.items():
                if items:  # Si el usuario tiene acceso a al menos un ítem del grupo
                    navigation_structure.append({
                        "title": grupo_titulo,
                        "separator": True,  # 🟢 Activa el título estilizado en el sidebar de Unfold
                        "items": items
                    })

            # Asignar la navegación calculada en tiempo real
            settings.UNFOLD["SIDEBAR"]["navigation"] = navigation_structure

        return self.get_response(request)

class EmpresaActivaMiddleware:
    """
    Valida la empresa activa de la sesión contra las empresas permitidas del usuario y la deja en
    `request.user._empresa_activa` para que PermisosPorEmpresaBackend calcule los permisos de esa empresa.
    - Si la de la sesión no le corresponde y solo tiene una, la toma automáticamente.
    - Si tiene varias (o ninguna), lo manda a elegir empresa.
    Va después de AuthenticationMiddleware y antes de los middlewares que consultan permisos.
    """
    RUTAS_EXENTAS = ('/admin/login', '/cerrar-sesion', '/seleccionar-empresa', '/static/', '/media/',
                     '/cambiar-password-obligatorio', '/evaluacion/acceso/', '/favicon')

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            from .empresas import empresas_permitidas

            empresa = request.session.get('empresa_activa') or request.session.get('empresa_id')
            permitidas = list(empresas_permitidas(request.user).values_list('pk', flat=True))
            if empresa not in permitidas:
                empresa = permitidas[0] if len(permitidas) == 1 else None
                request.session['empresa_id'] = request.session['empresa_activa'] = empresa
                if empresa is None and not request.path.lower().startswith(self.RUTAS_EXENTAS):
                    return redirect('seleccionar_empresa')
            request.user._empresa_activa = empresa

        return self.get_response(request)
