from django.contrib import admin
from unfold.admin import ModelAdmin
from rh.admin import admin_site
from .models import Pivot_Dinamico

@admin.register(Pivot_Dinamico, site=admin_site)
class Pivot_DinamicoAdmin(ModelAdmin):
    list_display = ('nombre', 'slug', 'icono', 'orden', 'activo')
    list_editable = ('orden', 'activo')
    prepopulated_fields = {'slug': ('nombre',)}
    search_fields = ('nombre', 'query_sql')