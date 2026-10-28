from django.contrib import admin
from unfold.admin import ModelAdmin

from rh.admin import admin_site
from .models import DiaInhabil, PoliticaVacaciones, SaldoVacaciones


def empresa_de_sesion(request):
    return request.session.get('empresa_activa') or request.session.get('empresa_id')


class PorEmpresaAdmin(ModelAdmin):
    """Muestra y guarda los registros de la empresa activa en sesión."""
    exclude = ('empresa',)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        empresa = empresa_de_sesion(request)
        return qs.filter(empresa_id=empresa) if empresa else qs

    def save_model(self, request, obj, form, change):
        if not obj.empresa_id:
            obj.empresa_id = empresa_de_sesion(request)
        super().save_model(request, obj, form, change)


@admin.register(DiaInhabil, site=admin_site)
class DiaInhabilAdmin(PorEmpresaAdmin):
    list_display = ('fecha', 'nombre')
    list_filter = ('fecha',)
    search_fields = ('nombre',)
    date_hierarchy = 'fecha'


@admin.register(PoliticaVacaciones, site=admin_site)
class PoliticaVacacionesAdmin(PorEmpresaAdmin):
    list_display = ('empresa', 'sabado_habil', 'dias_aviso_minimo', 'serie_folio', 'responsable_rh')

    def has_add_permission(self, request):
        # Una política por empresa
        empresa = empresa_de_sesion(request)
        if empresa and PoliticaVacaciones.objects.filter(empresa_id=empresa).exists():
            return False
        return super().has_add_permission(request)


@admin.register(SaldoVacaciones, site=admin_site)
class SaldoVacacionesAdmin(ModelAdmin):
    list_display = ('empleado', 'dias_arrastrados', 'anios_acumulados', 'fecha_corte')
    search_fields = ('empleado__nombre_largo', 'empleado__id_empleado')
    autocomplete_fields = ('empleado',)

    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related('empleado')
        empresa = empresa_de_sesion(request)
        return qs.filter(empleado__empresa_id=empresa) if empresa else qs
