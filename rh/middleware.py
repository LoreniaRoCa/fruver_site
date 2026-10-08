# rh/middleware.py

from django.conf import settings
from rh.admin import admin_site  # 🌟 Importamos tu instancia de AdminSite

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

        # 2. Módulo Tablas Dinámicas (CONSTRUCCIÓN DINÁMICA DESDE BD)
        elif any(k in path for k in ['/reportes/', 'pivot']):
            titulo_modulo = "Tablas Dinámicas"
            settings.UNFOLD["SITE_HEADER"] = titulo_modulo
            settings.UNFOLD["SITE_TITLE"] = titulo_modulo
            admin_site.site_header = titulo_modulo
            admin_site.site_title = titulo_modulo

            # Cargar dinámicamente cada renglón de la tabla Pivot_Dinamico
            items_reportes = []
            try:
                reportes_db = Pivot_Dinamico.objects.filter(activo=True).order_by('orden', 'nombre')
                for rep in reportes_db:
                    items_reportes.append({
                        "title": rep.nombre,
                        "link": f"/reportes/pivot/{rep.slug}/",
                        "icon": rep.icono or "bar_chart",
                    })
            except Exception:
                items_reportes = []

            settings.UNFOLD["SIDEBAR"]["navigation"] = [
                {
                    "items": items_reportes
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