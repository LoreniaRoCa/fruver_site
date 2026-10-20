from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline
from rh.admin import admin_site  # 🌟 Importamos tu sitio personalizado de Unfold
from .models import ModuloSistema, OpcionModulo

class OpcionModuloInline(TabularInline):
    model = OpcionModulo
    extra = 1
    fields = ('titulo', 'link', 'icono', 'orden', 'permiso_requerido', 'solo_superusuario')

@admin.register(ModuloSistema, site=admin_site)
class ModuloSistemaAdmin(ModelAdmin):
    list_display = ('nombre', 'slug', 'orden', 'activo')
    list_editable = ('orden', 'activo')
    inlines = [OpcionModuloInline]

@admin.register(OpcionModulo, site=admin_site)
class OpcionModuloAdmin(ModelAdmin):
    list_display = ('titulo', 'modulo', 'link', 'orden', 'permiso_requerido', 'solo_superusuario')
    list_filter = ('modulo', 'solo_superusuario')
    search_fields = ('titulo', 'link')