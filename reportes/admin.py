from django.contrib import admin
from unfold.admin import ModelAdmin
from rh.admin import admin_site
from .models import BitacoraSincronizacion, Pivot_Dinamico

@admin.register(Pivot_Dinamico, site=admin_site)
class Pivot_DinamicoAdmin(ModelAdmin):
    list_display = ('nombre', 'slug', 'icono', 'orden', 'activo')
    list_editable = ('orden', 'activo')
    prepopulated_fields = {'slug': ('nombre',)}
    search_fields = ('nombre', 'query_sql')

@admin.register(BitacoraSincronizacion, site=admin_site)
class BitacoraSincronizacionAdmin(ModelAdmin):
    """Solo consulta: las filas las escribe el comando subirsqlserver."""
    list_display = ('fecha_inicio', 'proceso', 'nombre_proceso', 'estatus', 'registros', 'duracion', 'equipo')
    list_filter = ('proceso', 'estatus', 'equipo')
    search_fields = ('nombre_proceso', 'mensaje')
    date_hierarchy = 'fecha_inicio'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
