
from django.urls import path
from . import views  # 👈 ESTA LÍNEA ES LA QUE FALTABA

app_name = 'reportes'

urlpatterns = [
    path('pivot/<slug:slug>/', views.reporte_dinamico_view, name='reporte_dinamico'),
    path('pivot/guardar-plantilla/', views.guardar_plantilla_pivot, name='guardar_plantilla_pivot'),
    path('tablas/', views.lista_tablas_dinamicas_view, name='lista_tablas'),
]