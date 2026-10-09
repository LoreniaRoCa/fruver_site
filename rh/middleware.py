# rh/middleware.py

from django.conf import settings
from rh.admin import admin_site  # 🌟 Importamos tu instancia de AdminSite

from django.urls import reverse
from django.db.utils import OperationalError, ProgrammingError

# Importa el modelo que mapea a la tabla rep_pivot_dinamico
from reportes.models import Pivot_Dinamico


class RestringirAccesoAdminMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path.lower()

        # -------------------------------------------------------------
        # 1. Módulo Seguridad del Sitio (Usuarios, Grupos, Permisos)
        # -------------------------------------------------------------
        if any(k in path for k in ['/admin/auth/', '/auth/', '/user/', '/group/']):
            titulo_modulo = "Seguridad del Sitio"
            settings.UNFOLD["SITE_HEADER"] = titulo_modulo
            settings.UNFOLD["SITE_TITLE"] = titulo_modulo
            admin_site.site_header = titulo_modulo  # 🌟 Sobrescribe el objeto AdminSite
            admin_site.site_title = titulo_modulo

            if request.user.is_authenticated and request.user.is_superuser:
                settings.UNFOLD["SIDEBAR"]["navigation"] = getattr(settings, 'NAV_SEGURIDAD', [])
            else:
                settings.UNFOLD["SIDEBAR"]["navigation"] = getattr(settings, 'NAV_RECURSOS_HUMANOS', [])

        # -------------------------------------------------------------
        # 2. Módulo Tablas Dinámicas (CONSTRUCCIÓN DINÁMICA DESDE BD)
        # -------------------------------------------------------------
        elif any(k in path for k in ['/reportes/', 'pivot']):
            titulo_modulo = "Tablas Dinámicas"
            settings.UNFOLD["SITE_HEADER"] = titulo_modulo
            settings.UNFOLD["SITE_TITLE"] = titulo_modulo
            admin_site.site_header = titulo_modulo
            admin_site.site_title = titulo_modulo

            # Cargar dinámicamente las opciones desde la BD
            items_reportes = []
            try:
                reportes_db = Pivot_Dinamico.objects.filter(activo=True).order_by('orden', 'nombre')
                for rep in reportes_db:
                    items_reportes.append({
                        "title": rep.nombre,
                        "link": f"/reportes/pivot/{rep.slug}/",
                        "icon": rep.icono if rep.icono else "bar_chart",
                    })
            except Exception:
                items_reportes = []

            # Colocar las opciones en la barra lateral izquierda (SIDEBAR)
            settings.UNFOLD["SIDEBAR"]["navigation"] = [
                {
                    "title": "Tablas Dinámicas y Reportes",
                    "separator": True,
                    "items": items_reportes,
                }
            ]
        # -------------------------------------------------------------
        # 3. Dashboard Principal
        # -------------------------------------------------------------
        elif '/admin/dashboard/' in path or path in ['/admin/', '/admin']:
            titulo_modulo = "Portal Empresarial"
            settings.UNFOLD["SITE_HEADER"] = titulo_modulo
            settings.UNFOLD["SITE_TITLE"] = titulo_modulo
            admin_site.site_header = titulo_modulo
            admin_site.site_title = titulo_modulo

            settings.UNFOLD["SIDEBAR"]["navigation"] = []

        # -------------------------------------------------------------
        # 4. Módulo Recursos Humanos (Evaluaciones y Catálogos)
        # -------------------------------------------------------------
        else:
            titulo_modulo = "Recursos Humanos"
            settings.UNFOLD["SITE_HEADER"] = titulo_modulo
            settings.UNFOLD["SITE_TITLE"] = titulo_modulo
            admin_site.site_header = titulo_modulo
            admin_site.site_title = titulo_modulo

            settings.UNFOLD["SIDEBAR"]["navigation"] = getattr(settings, 'NAV_RECURSOS_HUMANOS', [])

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