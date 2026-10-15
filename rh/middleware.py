# rh/middleware.py
from django.conf import settings
from rh.admin import admin_site  # 🌟 Importamos tu instancia de AdminSite
from django.urls import reverse
from django.db.utils import OperationalError, ProgrammingError
from django.shortcuts import redirect
from reportes.models import Pivot_Dinamico

class RestringirAccesoAdminMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path.lower()

        # 1. Módulo Seguridad del Sitio
        if any(k in path for k in ['/admin/auth/', '/auth/', '/user/', '/group/']):
            titulo_modulo = "Seguridad del Sitio"
            settings.UNFOLD["SITE_HEADER"] = titulo_modulo
            settings.UNFOLD["SITE_TITLE"] = titulo_modulo
            admin_site.site_header = titulo_modulo
            admin_site.site_title = titulo_modulo

            if request.user.is_authenticated and request.user.is_superuser:
                settings.UNFOLD["SIDEBAR"]["navigation"] = getattr(settings, 'NAV_SEGURIDAD', [])
            else:
                settings.UNFOLD["SIDEBAR"]["navigation"] = getattr(settings, 'NAV_RECURSOS_HUMANOS', [])

        # 2. Módulo Tablas Dinámicas
        elif any(k in path for k in ['/reportes/', 'pivot']):
            titulo_modulo = "Tablas Dinámicas"
            settings.UNFOLD["SITE_HEADER"] = titulo_modulo
            settings.UNFOLD["SITE_TITLE"] = titulo_modulo
            admin_site.site_header = titulo_modulo
            admin_site.site_title = titulo_modulo

            items_reportes = []
            try:
                reportes_db = Pivot_Dinamico.objects.filter(activo=True).order_by('orden', 'nombre')
                for rep in reportes_db:
                    items_reportes.append({
                        "title": rep.nombre,
                        # Lógica: Si ya está en la vista contenedora llama JS, de lo contrario navega abriendo la pestaña por URL
                        "link": f"javascript:if(window.parent && window.parent.abrirTabReporte){{window.parent.abrirTabReporte('{rep.slug}', '{rep.nombre}', '/reportes/pivot/{rep.slug}/');}}else if(window.abrirTabReporte){{window.abrirTabReporte('{rep.slug}', '{rep.nombre}', '/reportes/pivot/{rep.slug}/');}}else{{window.location.href='/reportes/tablas/?open={rep.slug}';}}",
                        "icon": rep.icono if rep.icono else "bar_chart",
                    })
            except Exception:
                items_reportes = []

            settings.UNFOLD["SIDEBAR"]["navigation"] = [
                {
                    "title": "Tablas Dinámicas y Reportes",
                    "separator": True,
                    "items": items_reportes,
                }
            ]

        # 3. Dashboard Principal (Portal Empresarial)
        elif path in ['/admin/dashboard/', '/admin/dashboard']:
            titulo_modulo = "Portal Empresarial"
            settings.UNFOLD["SITE_HEADER"] = titulo_modulo
            settings.UNFOLD["SITE_TITLE"] = titulo_modulo
            admin_site.site_header = titulo_modulo
            admin_site.site_title = titulo_modulo

            settings.UNFOLD["SIDEBAR"]["navigation"] = []
        # 4. Módulo Recursos Humanos
        elif '/admin/rh/' in path or any(k in path for k in ['evaluacion', 'empleado', 'puesto', 'departamento', 'competencia', 'resumen', 'panel']):
            titulo_modulo = "Recursos Humanos"
            settings.UNFOLD["SITE_HEADER"] = titulo_modulo
            settings.UNFOLD["SITE_TITLE"] = titulo_modulo
            admin_site.site_header = titulo_modulo
            admin_site.site_title = titulo_modulo

            settings.UNFOLD["SIDEBAR"]["navigation"] = getattr(settings, 'NAV_RECURSOS_HUMANOS', [])

        else:
            settings.UNFOLD["SIDEBAR"]["navigation"] = []

        # 🌟 OBLIGATORIO: Generar y retornar la respuesta HTTP a Django
        response = self.get_response(request)
        return response
def obtener_nav_tablas_dinamicas():
    """
    Consulta la tabla rep_pivot_dinamico en la BD 
    y genera la estructura del menú para Django Unfold.
    """
    items = []
    try:
        # Consultamos únicamente los reportes activos ordenados
        reportes = ReportePivotDinamico.objects.filter(activo=True).order_by('orden', 'nombre')

        for rep in reportes:
            items.append({
                "title": rep.nombre,
                "icon": rep.icono or "bar_chart",  # Usa el icono de la tabla o uno por defecto
                "link": reverse("reportes:reporte_pivot_dinamico", kwargs={"slug": rep.slug}),
            })
    except (OperationalError, ProgrammingError):
        # Evita fallos durante migraciones tempranas si la tabla aún no existe
        items = []

    return [
        {
            "title": "Consultas y Tablas Dinámicas",
            "separator": True,
            "items": items,
        }
    ]        
class ForzarCambioPasswordMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            # 🌟 1. NUEVA CONDICIÓN: Si ingresó por enlace mágico (token), omitir el cambio obligatorio
            if request.session.get('acceso_por_token'):
                return self.get_response(request)

            # 2. Rutas exentas (no redirigir si ya está en ellas)
            path_actual = request.path.lower()
            
            # Si la petición es a cambio de contraseña, logout, login o estáticos, continuar
            if any(k in path_actual for k in ['/cambiar-password-obligatorio', '/cerrar-sesion', '/admin/login', '/static/', '/media/']):
                return self.get_response(request)

            # 3. Consultar el perfil de Empleado
            empleado = getattr(request.user, 'empleado', None)

            # Si el empleado existe y tiene activa la bandera 'debe_cambiar_password'
            if empleado and getattr(empleado, 'debe_cambiar_password', False):
                return redirect('cambiar_password_obligatorio')

        return self.get_response(request)