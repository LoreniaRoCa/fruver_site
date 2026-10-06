from django.urls import path
from .views import inventario_pivot_view

app_name = 'reportes'

urlpatterns = [
    path('inventario/pivot/', inventario_pivot_view, name='inventario_pivot'),
]