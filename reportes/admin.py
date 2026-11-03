from django.contrib import admin
from unfold.admin import ModelAdmin
from rh.admin import admin_site
from .models import BitacoraConsultaExcel, BitacoraSincronizacion, ClaveExcel, Pivot_Dinamico

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


@admin.register(ClaveExcel, site=admin_site)
class ClaveExcelAdmin(ModelAdmin):
    """Las claves las genera cada usuario en Reportes en Excel; aquí se revisan, se les pone vencimiento o se desactivan."""
    list_display = ('usuario', 'nombre', 'prefijo', 'activa', 'vence', 'fecha_creacion', 'ultimo_uso')
    list_filter = ('activa',)
    search_fields = ('usuario__username', 'usuario__first_name', 'usuario__last_name', 'nombre', 'prefijo')
    fields = ('usuario', 'nombre', 'prefijo', 'activa', 'vence', 'fecha_creacion', 'ultimo_uso')
    readonly_fields = ('usuario', 'prefijo', 'fecha_creacion', 'ultimo_uso')
    actions = ['desactivar']

    def has_add_permission(self, request):
        return False

    @admin.action(description="Desactivar las claves seleccionadas")
    def desactivar(self, request, queryset):
        total = queryset.update(activa=False)
        self.message_user(request, f"{total} clave(s) desactivada(s).")


@admin.register(BitacoraConsultaExcel, site=admin_site)
class BitacoraConsultaExcelAdmin(ModelAdmin):
    """Solo consulta: cada actualización de datos desde Excel."""
    list_display = ('fecha', 'usuario', 'reporte', 'empresa', 'estatus', 'filas', 'duracion_ms', 'version_plantilla', 'ip')
    list_filter = ('estatus', 'reporte', 'empresa')
    search_fields = ('usuario__username', 'mensaje', 'ip')
    date_hierarchy = 'fecha'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
